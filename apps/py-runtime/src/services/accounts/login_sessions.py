from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Mapping
from typing import Protocol
from uuid import uuid4

from app.secret_store import SecretStore
from errors import DomainError, ErrorCode
from repositories.account_login_session_repository import (
    AccountLoginSessionRepository,
    LoginSessionAggregate,
    session_secret_payload,
)
from repositories.execution_environment_v1_repository import (
    ExecutionEnvironmentV1Repository,
)
from schemas.v1.account_login_sessions import (
    LoginSessionAcceptedDto,
    LoginSessionDto,
    LogoutAcceptedDto,
)
from services.browser_runtime import BrowserRuntimeError
from services.accounts.tiktok_session_probe import (
    TikTokSessionProbeError,
    TikTokSessionProbePort,
)
from services.tasks.coordinator import TaskCoordinator
from services.tasks.handler_registry import TaskHandlerRegistry
from services.tasks.types import (
    JsonValue,
    TaskExecutionContext,
    TaskExecutionResult,
    TaskHandlerDefinition,
    TaskResumePolicy,
)

log = logging.getLogger(__name__)
PREPARE_TASK_TYPE = "account.login.prepare"
PROBE_TASK_TYPE = "account.login.probe"
LOGOUT_TASK_TYPE = "account.logout"
_TIKTOK_LOGIN_URL = "https://www.tiktok.com/login"


class LoginBrowserNavigationPort(Protocol):
    def navigate(self, *, debug_port: int, url: str) -> None: ...


class AccountLoginSessionService:
    def __init__(
        self,
        *,
        repository: AccountLoginSessionRepository,
        environment_repository: ExecutionEnvironmentV1Repository,
        task_coordinator: TaskCoordinator,
        login_timeout_seconds: Callable[[], int],
        probe_timeout_seconds: Callable[[], int],
        cancel_timeout_seconds: Callable[[], int] = lambda: 30,
    ) -> None:
        self._repository = repository
        self._environments = environment_repository
        self._tasks = task_coordinator
        self._login_timeout_seconds = login_timeout_seconds
        self._probe_timeout_seconds = probe_timeout_seconds
        self._cancel_timeout_seconds = cancel_timeout_seconds
        self._cancel_locks: dict[str, asyncio.Lock] = {}

    async def create(
        self,
        account_id: str,
        *,
        environment_id: str,
        idempotency_key: str,
        request_id: str,
        operation_id: str,
    ) -> LoginSessionAcceptedDto:
        environment = self._environments.get_owned(account_id, environment_id)
        if environment is None or environment.binding.status != "active":
            raise DomainError(
                ErrorCode.ACCOUNT_CONNECTION_REQUIRED,
                "请先绑定并激活执行环境，再打开浏览器登录",
                status_code=409,
            )
        aggregate = self._repository.ensure(
            account_id=account_id,
            idempotency_key=idempotency_key,
            timeout_seconds=self._login_timeout_seconds(),
        )
        if aggregate.binding.id != environment_id:
            raise DomainError(
                ErrorCode.LOGIN_SESSION_STATE_CONFLICT,
                "已有登录尝试属于其他执行环境，请先取消",
                status_code=409,
            )
        if aggregate.login_session.prepare_task_id:
            return LoginSessionAcceptedDto(
                sessionId=aggregate.login_session.id,
                taskId=aggregate.login_session.prepare_task_id,
                state=aggregate.login_session.state,
            )
        try:
            task = await self._tasks.submit_account_task(
                account_id,
                task_type=PREPARE_TASK_TYPE,
                payload={"loginSessionId": aggregate.login_session.id},
                idempotency_key=idempotency_key,
                request_id=request_id,
                operation_id=operation_id,
                timeout_seconds=30,
            )
        except Exception:
            log.exception(
                "提交登录准备任务失败",
                extra={"account_id": account_id, "session_id": aggregate.login_session.id},
            )
            self._repository.mark_probe_failed(
                account_id=account_id,
                session_id=aggregate.login_session.id,
                error_code=ErrorCode.INTERNAL_ERROR.value,
                error_log_id=f"log_login_submit_{aggregate.login_session.id}",
                retryable=False,
            )
            raise
        self._repository.set_task(
            account_id=account_id,
            session_id=aggregate.login_session.id,
            task_kind="prepare",
            task_id=task.id,
        )
        return LoginSessionAcceptedDto(
            sessionId=aggregate.login_session.id,
            taskId=task.id,
            state="preparing",
        )

    def get(self, account_id: str, session_id: str) -> LoginSessionDto:
        aggregate = self._repository.get_owned(account_id, session_id)
        if aggregate is None:
            raise DomainError(
                ErrorCode.LOGIN_SESSION_NOT_FOUND,
                "登录尝试不存在或不属于当前账号",
                status_code=404,
            )
        return _to_dto(aggregate)

    async def probe(
        self,
        account_id: str,
        session_id: str,
        *,
        expected_revision: int,
        idempotency_key: str,
        request_id: str,
        operation_id: str,
    ) -> LoginSessionAcceptedDto:
        current = self.get(account_id, session_id)
        if current.revision != expected_revision:
            raise DomainError(
                ErrorCode.REVISION_CONFLICT,
                "登录状态已变化，请刷新后重试",
                status_code=409,
            )
        aggregate = self._repository.begin_probe(
            account_id=account_id,
            session_id=session_id,
        )
        try:
            task = await self._tasks.submit_account_task(
                account_id,
                task_type=PROBE_TASK_TYPE,
                payload={"loginSessionId": session_id},
                idempotency_key=idempotency_key,
                request_id=request_id,
                operation_id=operation_id,
                timeout_seconds=self._probe_timeout_seconds(),
            )
        except Exception:
            log.exception(
                "提交登录探测任务失败",
                extra={"account_id": account_id, "session_id": session_id},
            )
            self._repository.mark_probe_failed(
                account_id=account_id,
                session_id=session_id,
                error_code=ErrorCode.INTERNAL_ERROR.value,
                error_log_id=f"log_login_probe_submit_{session_id}",
                retryable=True,
            )
            raise
        self._repository.set_task(
            account_id=account_id,
            session_id=session_id,
            task_kind="probe",
            task_id=task.id,
        )
        return LoginSessionAcceptedDto(
            sessionId=session_id,
            taskId=task.id,
            state=aggregate.login_session.state,
        )

    async def cancel(
        self,
        account_id: str,
        session_id: str,
        *,
        idempotency_key: str,
    ) -> LoginSessionDto:
        lock = self._cancel_locks.setdefault(session_id, asyncio.Lock())
        async with lock:
            aggregate = self._repository.get_owned(account_id, session_id)
            if aggregate is None:
                raise DomainError(
                    ErrorCode.LOGIN_SESSION_NOT_FOUND,
                    "登录尝试不存在或不属于当前账号",
                    status_code=404,
                )
            if aggregate.login_session.state in {"completed", "cancelled"}:
                return _to_dto(aggregate)
            task_ids = tuple(
                task_id
                for task_id in (
                    aggregate.login_session.prepare_task_id,
                    aggregate.login_session.probe_task_id,
                )
                if task_id
            )
            try:
                for task_id in task_ids:
                    await self._cancel_task(
                        account_id,
                        task_id,
                        idempotency_key=f"{idempotency_key}:{task_id}",
                    )
                latest = self._repository.get_owned(account_id, session_id)
                if latest is not None and latest.login_session.state == "completed":
                    return _to_dto(latest)
                return _to_dto(
                    self._repository.cancel(
                        account_id=account_id,
                        session_id=session_id,
                    )
                )
            except Exception as exc:
                log.exception(
                    "监督登录取消补偿未完成",
                    extra={
                        "account_id": account_id,
                        "session_id": session_id,
                        "error_code": ErrorCode.LOGIN_SESSION_CANCEL_INCOMPLETE.value,
                    },
                )
                self._repository.mark_cancel_incomplete(
                    account_id=account_id,
                    session_id=session_id,
                    error_log_id=f"log_login_cancel_{uuid4().hex}",
                )
                raise DomainError(
                    ErrorCode.LOGIN_SESSION_CANCEL_INCOMPLETE,
                    "登录取消未完成，请保留当前页面并重试",
                    status_code=409,
                    loggable=True,
                ) from exc
            finally:
                self._cancel_locks.pop(session_id, None)

    async def _cancel_task(
        self,
        account_id: str,
        task_id: str,
        *,
        idempotency_key: str,
    ) -> None:
        record = await self._tasks.cancel_account_task(
            account_id,
            task_id,
            idempotency_key=idempotency_key,
        )
        if record.status.value in {"completed", "failed"}:
            return
        deadline = asyncio.get_running_loop().time() + self._cancel_timeout_seconds()
        while asyncio.get_running_loop().time() < deadline:
            await asyncio.sleep(0.1)
            record = await self._tasks.get_account_task(account_id, task_id)
            if record.status.value in {"completed", "failed"}:
                return
        raise TimeoutError("等待登录关联任务取消超时")

    async def logout(
        self,
        account_id: str,
        *,
        idempotency_key: str,
        request_id: str,
        operation_id: str,
    ) -> LogoutAcceptedDto:
        task = await self._tasks.submit_account_task(
            account_id,
            task_type=LOGOUT_TASK_TYPE,
            payload={},
            idempotency_key=idempotency_key,
            request_id=request_id,
            operation_id=operation_id,
            timeout_seconds=30,
        )
        return LogoutAcceptedDto(taskId=task.id)


def register_login_session_task_handlers(
    registry: TaskHandlerRegistry,
    *,
    repository: AccountLoginSessionRepository,
    browser_runtime: LoginBrowserNavigationPort,
    probe: TikTokSessionProbePort,
    secret_store: SecretStore,
    probe_timeout_seconds: Callable[[], int],
) -> None:
    async def prepare_handler(
        context: TaskExecutionContext,
        payload: Mapping[str, JsonValue],
    ) -> TaskExecutionResult:
        account_id, session_id = _task_scope(context, payload)
        aggregate = _require_aggregate(repository, account_id, session_id)
        debug_port = aggregate.browser.debug_port
        if aggregate.browser.status != "running" or debug_port is None:
            raise DomainError(
                ErrorCode.EXECUTION_ENVIRONMENT_NOT_ELIGIBLE,
                "执行环境浏览器未运行，请先修复环境",
                status_code=409,
            )
        try:
            await asyncio.to_thread(
                browser_runtime.navigate,
                debug_port=debug_port,
                url=_TIKTOK_LOGIN_URL,
            )
        except BrowserRuntimeError as exc:
            raise DomainError(
                ErrorCode.ACCOUNT_PLATFORM_SESSION_INVALID,
                str(exc),
                status_code=409,
                loggable=True,
            ) from exc
        repository.mark_waiting(account_id=account_id, session_id=session_id)
        return TaskExecutionResult(result_ref=f"login-session://{session_id}")

    async def probe_handler(
        context: TaskExecutionContext,
        payload: Mapping[str, JsonValue],
    ) -> TaskExecutionResult:
        account_id, session_id = _task_scope(context, payload)
        aggregate = _require_aggregate(repository, account_id, session_id)
        debug_port = aggregate.browser.debug_port
        if debug_port is None:
            raise DomainError(
                ErrorCode.ACCOUNT_PLATFORM_SESSION_INVALID,
                "受控浏览器缺少调试连接，请重新启动环境",
                status_code=409,
            )
        log_id = f"log_{uuid4().hex}"
        try:
            result = probe.probe(
                debug_port=debug_port,
                timeout_seconds=probe_timeout_seconds(),
            )
            if not result.authenticated:
                raise TikTokSessionProbeError(
                    ErrorCode.ACCOUNT_PLATFORM_AUTH_REQUIRED.value,
                    "尚未检测到 TikTok 登录，请在浏览器完成登录后重试。",
                )
            if not result.identity:
                raise TikTokSessionProbeError(
                    ErrorCode.ACCOUNT_PLATFORM_IDENTITY_UNAVAILABLE.value,
                    "未能识别 TikTok 公开账号，请打开个人主页后重试。",
                )
            expected = aggregate.login_session.expected_identity
            if expected and expected != result.identity:
                repository.mark_probe_failed(
                    account_id=account_id,
                    session_id=session_id,
                    error_code=ErrorCode.ACCOUNT_PLATFORM_IDENTITY_MISMATCH.value,
                    error_log_id=log_id,
                    retryable=True,
                    detected_identity=result.identity,
                )
                raise DomainError(
                    ErrorCode.ACCOUNT_PLATFORM_IDENTITY_MISMATCH,
                    f"检测到 @{result.identity}，与目标账号 @{expected} 不一致",
                    status_code=409,
                    loggable=True,
                )
            session_ref = f"account-session:{account_id}"
            secret_store.set(
                session_ref,
                session_secret_payload(aggregate, result.identity),
            )
            try:
                repository.complete_probe(
                    account_id=account_id,
                    session_id=session_id,
                    detected_identity=result.identity,
                    session_ref=session_ref,
                )
            except Exception:
                secret_store.delete(session_ref)
                raise
            return TaskExecutionResult(result_ref=f"login-session://{session_id}")
        except TikTokSessionProbeError as exc:
            repository.mark_probe_failed(
                account_id=account_id,
                session_id=session_id,
                error_code=exc.error_code,
                error_log_id=log_id,
                retryable=True,
            )
            raise DomainError(
                ErrorCode(exc.error_code),
                str(exc),
                status_code=409,
                loggable=True,
            ) from exc

    async def logout_handler(
        context: TaskExecutionContext,
        payload: Mapping[str, JsonValue],
    ) -> TaskExecutionResult:
        if payload or context.account_id is None:
            raise DomainError(
                ErrorCode.TASK_SNAPSHOT_INVALID,
                "登出任务快照无效",
                status_code=409,
            )
        account_id = context.account_id
        aggregate = _active_login_aggregate(repository, account_id)
        try:
            if aggregate is not None and aggregate.browser.debug_port is not None:
                probe.clear_session(
                    debug_port=aggregate.browser.debug_port,
                    timeout_seconds=probe_timeout_seconds(),
                )
        except TikTokSessionProbeError as exc:
            raise DomainError(
                ErrorCode.ACCOUNT_PLATFORM_SESSION_INVALID,
                str(exc),
                status_code=409,
                loggable=True,
            ) from exc
        previous_ref = repository.logout(account_id=account_id)
        if previous_ref:
            secret_store.delete(previous_ref)
        return TaskExecutionResult(result_ref=f"account-session://{account_id}/revoked")

    for task_type, handler, timeout in (
        (PREPARE_TASK_TYPE, prepare_handler, 30),
        (PROBE_TASK_TYPE, probe_handler, None),
        (LOGOUT_TASK_TYPE, logout_handler, 30),
    ):
        registry.register(
            TaskHandlerDefinition(
                task_type=task_type,
                handler=handler,
                allowed_snapshot_fields=frozenset(
                    {"loginSessionId"} if task_type != LOGOUT_TASK_TYPE else set()
                ),
                resume_policy=TaskResumePolicy.INTERRUPT,
                cancellable=True,
                handler_version=1,
                timeout_seconds=timeout,
                single_active_per_scope=True,
                active_conflict_error_code="LOGIN_SESSION_STATE_CONFLICT",
            )
        )


def _task_scope(
    context: TaskExecutionContext,
    payload: Mapping[str, JsonValue],
) -> tuple[str, str]:
    session_id = payload.get("loginSessionId")
    if context.account_id is None or not isinstance(session_id, str):
        raise DomainError(
            ErrorCode.TASK_SNAPSHOT_INVALID,
            "登录任务快照无效",
            status_code=409,
        )
    return context.account_id, session_id


def _require_aggregate(
    repository: AccountLoginSessionRepository,
    account_id: str,
    session_id: str,
) -> LoginSessionAggregate:
    aggregate = repository.get_owned(account_id, session_id)
    if aggregate is None:
        raise DomainError(
            ErrorCode.LOGIN_SESSION_NOT_FOUND,
            "登录尝试不存在或不属于当前账号",
            status_code=404,
        )
    return aggregate


def _active_login_aggregate(
    repository: AccountLoginSessionRepository,
    account_id: str,
) -> LoginSessionAggregate | None:
    # 登出无需依赖历史尝试，仓储仅用于获取当前受控浏览器。
    return repository.get_latest_for_account(account_id)


def _to_dto(aggregate: LoginSessionAggregate) -> LoginSessionDto:
    value = aggregate.login_session
    return LoginSessionDto(
        id=value.id,
        accountId=value.account_id,
        environmentId=value.execution_binding_id,
        state=value.state,
        expectedIdentity=value.expected_identity,
        detectedIdentity=value.detected_identity,
        expiresAt=value.expires_at,
        prepareTaskId=value.prepare_task_id,
        probeTaskId=value.probe_task_id,
        errorCode=value.error_code,
        errorLogId=value.error_log_id,
        revision=int(value.revision),
    )
