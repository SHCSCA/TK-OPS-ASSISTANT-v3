from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.orm import Session, sessionmaker

from app.secret_store import SecretStore
from domain.models.account import Account
from domain.models.account_connection import AccountConnection
from domain.models.account_login_session import AccountLoginSession
from errors import DomainError, ErrorCode
from repositories.account_login_session_repository import (
    ACTIVE_STATES,
    AccountLoginSessionRepository,
)
from repositories.execution_environment_v1_repository import (
    ExecutionEnvironmentAggregate,
    ExecutionEnvironmentV1Repository,
)
from services.accounts.tiktok_session_probe import (
    TikTokSessionProbeError,
    TikTokSessionProbePort,
)
from services.browser_runtime import BrowserRuntime
from services.events import RuntimeEventDraft, RuntimeEventService
from services.execution_environments.browser_process import (
    BrowserProcessOwnershipError,
    BrowserProcessOwnershipService,
)

log = logging.getLogger(__name__)
_PENDING_REASON = "ARCHIVE_CLEANUP_PENDING"
_FAILED_REASON = "ARCHIVE_CLEANUP_FAILED"


class AccountArchiveCleanupService:
    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session],
        environments: ExecutionEnvironmentV1Repository,
        login_sessions: AccountLoginSessionRepository,
        browser_runtime: BrowserRuntime,
        ownership_service: BrowserProcessOwnershipService,
        session_probe: TikTokSessionProbePort,
        secret_store: SecretStore,
        event_service: RuntimeEventService,
    ) -> None:
        self._session_factory = session_factory
        self._environments = environments
        self._login_sessions = login_sessions
        self._browser_runtime = browser_runtime
        self._ownership = ownership_service
        self._session_probe = session_probe
        self._secret_store = secret_store
        self._events = event_service

    def cleanup(
        self,
        *,
        account_id: str,
        expected_revision: int,
        reason_provided: bool,
        task_id: str,
    ) -> int:
        self._mark_pending(account_id, expected_revision)
        log_id = f"log_{uuid4().hex}"
        try:
            environments = self._environments.list_owned(account_id)
            self._revoke_platform_session(account_id, environments)
            for environment in environments:
                self._stop_environment(account_id, environment, log_id)
            revision = self._finalize_archive(account_id)
            self._events.append_standalone_idempotent(
                RuntimeEventDraft(
                    event_id=f"account-archived-{task_id}",
                    event_type="account.archived",
                    topic=f"account:{account_id}:workspace",
                    account_id=account_id,
                    aggregate_type="account",
                    aggregate_id=account_id,
                    task_id=task_id,
                    revision=revision,
                    payload={
                        "reasonProvided": reason_provided,
                        "invalidations": [
                            "accounts:list",
                            "current-context",
                            f"account:{account_id}:workspace",
                            f"account:{account_id}:tasks",
                        ],
                    },
                )
            )
            return revision
        except DomainError:
            self._mark_attention(account_id)
            raise
        except Exception as exc:
            log.exception(
                "账号归档清理失败",
                extra={"account_id": account_id, "log_id": log_id},
            )
            self._mark_attention(account_id)
            raise DomainError(
                ErrorCode.INTERNAL_ERROR,
                "账号归档清理失败，请查看日志后重试",
                status_code=500,
                loggable=True,
            ) from exc

    def _mark_pending(self, account_id: str, expected_revision: int) -> None:
        with self._session_factory() as session:
            account = session.get(Account, account_id)
            if account is None:
                raise DomainError(
                    ErrorCode.ACCOUNT_NOT_FOUND,
                    "账号不存在，请刷新后重试",
                    status_code=404,
                )
            if account.status == "archived":
                return
            resuming = account.status_reason_code in {_PENDING_REASON, _FAILED_REASON}
            if not resuming and int(account.revision) != expected_revision:
                raise DomainError(
                    ErrorCode.REVISION_CONFLICT,
                    "账号状态已变化，请刷新后重试",
                    status_code=409,
                )
            if account.status != "attention" or account.status_reason_code != _PENDING_REASON:
                account.status = "attention"
                account.status_reason_code = _PENDING_REASON
                account.revision += 1
                account.updated_at = _now_text()
                session.commit()

    def _revoke_platform_session(
        self,
        account_id: str,
        environments: list[ExecutionEnvironmentAggregate],
    ) -> None:
        latest = self._login_sessions.get_latest_for_account(account_id)
        debug_port = latest.browser.debug_port if latest is not None else None
        if debug_port is None:
            debug_port = next(
                (
                    item.browser.debug_port
                    for item in environments
                    if item.browser.debug_port is not None
                ),
                None,
            )
        if debug_port is not None:
            try:
                self._session_probe.clear_session(
                    debug_port=debug_port,
                    timeout_seconds=20,
                )
            except TikTokSessionProbeError as exc:
                raise DomainError(
                    ErrorCode.ACCOUNT_PLATFORM_SESSION_INVALID,
                    str(exc),
                    status_code=409,
                    loggable=True,
                ) from exc

    def _stop_environment(
        self,
        account_id: str,
        environment: ExecutionEnvironmentAggregate,
        log_id: str,
    ) -> None:
        browser = environment.browser
        if browser.status == "running":
            if (
                browser.process_id is None
                or browser.debug_host is None
                or browser.debug_port is None
                or not browser.executable_path
                or not browser.runtime_evidence_json
            ):
                self._mark_environment_cleanup_failed(
                    account_id,
                    environment.binding.id,
                    log_id,
                    orphaned=True,
                )
                raise DomainError(
                    ErrorCode.BROWSER_PROCESS_OWNERSHIP_UNPROVEN,
                    "浏览器运行证据不完整，账号保持待处理状态",
                    status_code=409,
                    loggable=True,
                )
            try:
                self._ownership.verify_existing(
                    account_id=account_id,
                    browser_instance_id=browser.id,
                    profile_path=Path(browser.profile_path),
                    process_id=browser.process_id,
                    executable_path=browser.executable_path,
                    debug_host=browser.debug_host,
                    debug_port=browser.debug_port,
                    runtime_evidence_json=browser.runtime_evidence_json,
                )
            except BrowserProcessOwnershipError as exc:
                self._mark_environment_cleanup_failed(
                    account_id,
                    environment.binding.id,
                    log_id,
                    orphaned=True,
                )
                raise DomainError(
                    ErrorCode.BROWSER_PROCESS_OWNERSHIP_UNPROVEN,
                    str(exc),
                    status_code=409,
                    loggable=True,
                ) from exc
            stopped = self._browser_runtime.stop(process_id=browser.process_id)
            if stopped.alive:
                self._mark_environment_cleanup_failed(
                    account_id,
                    environment.binding.id,
                    log_id,
                    orphaned=False,
                )
                raise DomainError(
                    ErrorCode.EXECUTION_ENVIRONMENT_PROVISION_FAILED,
                    "浏览器进程未能停止，账号保持待处理状态",
                    status_code=409,
                    loggable=True,
                )
        self._environments.mark_stopped_for_archive(
            account_id=account_id,
            environment_id=environment.binding.id,
        )

    def _finalize_archive(self, account_id: str) -> int:
        with self._session_factory() as session:
            account = session.get(Account, account_id)
            if account is None:
                raise DomainError(
                    ErrorCode.ACCOUNT_NOT_FOUND,
                    "账号不存在，请刷新后重试",
                    status_code=404,
                )
            if account.status == "archived":
                return int(account.revision)
            connection = session.scalar(
                select(AccountConnection).where(
                    AccountConnection.account_id == account_id
                )
            )
            session_ref = connection.session_ref if connection is not None else None
            if session_ref:
                self._secret_store.delete(session_ref)
            if connection is not None:
                connection.session_ref = None
                connection.active_execution_binding_id = None
                connection.auth_status = "required"
                connection.health_status = "attention"
                connection.error_code = ErrorCode.ACCOUNT_PLATFORM_AUTH_REQUIRED.value
                connection.error_log_id = None
                connection.revision += 1
                connection.updated_at = _now_text()
            session.execute(
                update(AccountLoginSession)
                .where(
                    AccountLoginSession.account_id == account_id,
                    AccountLoginSession.state.in_(ACTIVE_STATES),
                )
                .values(state="cancelled", updated_at=_now_text())
            )
            account.status = "archived"
            account.status_reason_code = "USER_ARCHIVED"
            account.archived_at = _now_text()
            account.revision += 1
            account.updated_at = _now_text()
            session.commit()
            return int(account.revision)

    def _mark_environment_cleanup_failed(
        self,
        account_id: str,
        environment_id: str,
        log_id: str,
        *,
        orphaned: bool,
    ) -> None:
        self._environments.mark_cleanup_failed(
            account_id=account_id,
            environment_id=environment_id,
            error_code=(
                ErrorCode.BROWSER_PROCESS_OWNERSHIP_UNPROVEN.value
                if orphaned
                else ErrorCode.EXECUTION_ENVIRONMENT_PROVISION_FAILED.value
            ),
            error_log_id=log_id,
            browser_orphaned=orphaned,
        )

    def _mark_attention(self, account_id: str) -> None:
        try:
            with self._session_factory() as session:
                account = session.get(Account, account_id)
                if account is None or account.status == "archived":
                    return
                account.status = "attention"
                account.status_reason_code = _FAILED_REASON
                account.revision += 1
                account.updated_at = _now_text()
                session.commit()
        except Exception:
            log.exception(
                "记录账号归档清理失败状态时发生异常",
                extra={"account_id": account_id},
            )


def _now_text() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
