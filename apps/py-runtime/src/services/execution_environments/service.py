from __future__ import annotations

import json
import logging

from errors import DomainError, ErrorCode
from repositories.execution_environment_v1_repository import (
    ExecutionEnvironmentAggregate,
    ExecutionEnvironmentV1Repository,
)
from schemas.v1.execution_environments import (
    ExecutionEnvironmentAcceptedDto,
    ExecutionEnvironmentBrowserDto,
    ExecutionEnvironmentCreateInput,
    ExecutionEnvironmentDto,
    ExecutionEnvironmentListDto,
    ExecutionEnvironmentRetryAcceptedDto,
    ExecutionEnvironmentWorkspaceDto,
)
from schemas.v1.tasks import TaskAcceptedDto
from services.execution_environments.eligibility import evaluate_environment
from services.execution_environments.task_handlers import (
    CHECK_TASK_TYPE,
    DELETE_TASK_TYPE,
    PROVISION_TASK_TYPE,
    START_TASK_TYPE,
    STOP_TASK_TYPE,
)
from services.execution_environments.workspace_root_resolver import (
    WorkspaceRootResolutionError,
    WorkspaceRootResolver,
)
from services.tasks.coordinator import TaskCoordinator
from services.tasks.types import TaskStatus

log = logging.getLogger(__name__)


class ExecutionEnvironmentService:
    def __init__(
        self,
        *,
        repository: ExecutionEnvironmentV1Repository,
        root_resolver: WorkspaceRootResolver,
        task_coordinator: TaskCoordinator,
        task_timeout_seconds: int = 120,
    ) -> None:
        self._repository = repository
        self._root_resolver = root_resolver
        self._tasks = task_coordinator
        self._task_timeout_seconds = task_timeout_seconds

    def list(self, account_id: str) -> ExecutionEnvironmentListDto:
        return ExecutionEnvironmentListDto(
            items=[self._to_dto(item) for item in self._repository.list_owned(account_id)]
        )

    def get(self, account_id: str, environment_id: str) -> ExecutionEnvironmentDto:
        aggregate = self._repository.get_owned(account_id, environment_id)
        if aggregate is None:
            raise DomainError(
                ErrorCode.EXECUTION_ENVIRONMENT_NOT_FOUND,
                "执行环境不存在或不属于当前账号",
                status_code=404,
            )
        return self._to_dto(aggregate)

    async def create(
        self,
        account_id: str,
        payload: ExecutionEnvironmentCreateInput,
        *,
        idempotency_key: str,
        request_id: str,
        operation_id: str,
    ) -> ExecutionEnvironmentAcceptedDto:
        try:
            resolution = self._root_resolver.resolve(
                account_id=account_id,
                root_ref=payload.rootRef,
            )
        except WorkspaceRootResolutionError as exc:
            raise DomainError(
                ErrorCode(exc.error_code),
                str(exc),
                status_code=409,
                loggable=True,
            ) from exc
        aggregate = self._repository.ensure_draft(
            account_id=account_id,
            idempotency_key=idempotency_key,
            name=payload.name.strip(),
            workspace_display_name=resolution.display_name,
            root_ref=payload.rootRef,
            root_path=str(resolution.path),
            browser_kind=payload.browser.kind,
        )
        try:
            task = await self._tasks.submit_account_task(
                account_id,
                task_type=PROVISION_TASK_TYPE,
                payload={
                    "environmentId": aggregate.binding.id,
                    "rootRef": payload.rootRef,
                    "activateWhenReady": payload.activateWhenReady,
                },
                idempotency_key=idempotency_key,
                request_id=request_id,
                operation_id=operation_id,
                timeout_seconds=self._task_timeout_seconds,
            )
            self._repository.record_task(
                account_id=account_id,
                environment_id=aggregate.binding.id,
                task_id=task.id,
                retry_of_task_id=None,
            )
        except Exception:
            log.exception(
                "提交执行环境创建任务失败",
                extra={
                    "account_id": account_id,
                    "environment_id": aggregate.binding.id,
                },
            )
            self._repository.mark_failed(
                account_id=account_id,
                environment_id=aggregate.binding.id,
                error_code=ErrorCode.INTERNAL_ERROR.value,
                error_log_id=f"log_task_submit_{aggregate.binding.id}",
                browser_orphaned=False,
            )
            raise
        return ExecutionEnvironmentAcceptedDto(
            environmentId=aggregate.binding.id,
            taskId=task.id,
        )

    async def retry(
        self,
        account_id: str,
        environment_id: str,
        *,
        expected_revision: int,
        idempotency_key: str,
        request_id: str,
        operation_id: str,
    ) -> ExecutionEnvironmentRetryAcceptedDto:
        aggregate = self._repository.get_owned(account_id, environment_id)
        if aggregate is None:
            raise DomainError(
                ErrorCode.EXECUTION_ENVIRONMENT_NOT_FOUND,
                "执行环境不存在或不属于当前账号",
                status_code=404,
            )
        if int(aggregate.binding.revision) != expected_revision:
            raise DomainError(
                ErrorCode.REVISION_CONFLICT,
                "执行环境状态已变化，请刷新后重试",
                status_code=409,
            )
        if aggregate.binding.status != "failed":
            raise DomainError(
                ErrorCode.EXECUTION_ENVIRONMENT_NOT_RETRYABLE,
                "当前执行环境不能重试创建，请先执行检查",
                status_code=409,
            )
        original_task_id = aggregate.binding.last_task_id
        if not original_task_id:
            raise DomainError(
                ErrorCode.EXECUTION_ENVIRONMENT_RETRY_CONTEXT_MISSING,
                "执行环境缺少原任务上下文，请先执行检查",
                status_code=409,
            )
        original = await self._tasks.get_account_task(account_id, original_task_id)
        if (
            original.task_type != PROVISION_TASK_TYPE
            or original.status is not TaskStatus.FAILED
        ):
            raise DomainError(
                ErrorCode.EXECUTION_ENVIRONMENT_NOT_RETRYABLE,
                "原创建任务尚未失败，不能发起重试",
                status_code=409,
            )
        task = await self._tasks.retry_account_task(
            account_id,
            original_task_id,
            idempotency_key=idempotency_key,
            request_id=request_id,
            operation_id=operation_id,
        )
        self._repository.record_task(
            account_id=account_id,
            environment_id=environment_id,
            task_id=task.id,
            retry_of_task_id=original_task_id,
            expected_revision=expected_revision,
        )
        return ExecutionEnvironmentRetryAcceptedDto(
            environmentId=environment_id,
            taskId=task.id,
            retryOfTaskId=original_task_id,
        )

    async def start(
        self,
        account_id: str,
        environment_id: str,
        *,
        expected_revision: int,
        idempotency_key: str,
        request_id: str,
        operation_id: str,
    ) -> TaskAcceptedDto:
        return await self._submit_action(
            account_id,
            environment_id,
            task_type=START_TASK_TYPE,
            expected_revision=expected_revision,
            idempotency_key=idempotency_key,
            request_id=request_id,
            operation_id=operation_id,
        )

    async def stop(
        self,
        account_id: str,
        environment_id: str,
        *,
        expected_revision: int,
        idempotency_key: str,
        request_id: str,
        operation_id: str,
    ) -> TaskAcceptedDto:
        return await self._submit_action(
            account_id,
            environment_id,
            task_type=STOP_TASK_TYPE,
            expected_revision=expected_revision,
            idempotency_key=idempotency_key,
            request_id=request_id,
            operation_id=operation_id,
        )

    async def check(
        self,
        account_id: str,
        environment_id: str,
        *,
        expected_revision: int,
        idempotency_key: str,
        request_id: str,
        operation_id: str,
    ) -> TaskAcceptedDto:
        return await self._submit_action(
            account_id,
            environment_id,
            task_type=CHECK_TASK_TYPE,
            expected_revision=expected_revision,
            idempotency_key=idempotency_key,
            request_id=request_id,
            operation_id=operation_id,
        )

    async def delete(
        self,
        account_id: str,
        environment_id: str,
        *,
        expected_revision: int,
        idempotency_key: str,
        request_id: str,
        operation_id: str,
    ) -> TaskAcceptedDto:
        return await self._submit_action(
            account_id,
            environment_id,
            task_type=DELETE_TASK_TYPE,
            expected_revision=expected_revision,
            idempotency_key=idempotency_key,
            request_id=request_id,
            operation_id=operation_id,
        )

    async def _submit_action(
        self,
        account_id: str,
        environment_id: str,
        *,
        task_type: str,
        expected_revision: int,
        idempotency_key: str,
        request_id: str,
        operation_id: str,
    ) -> TaskAcceptedDto:
        aggregate = self._repository.get_owned(account_id, environment_id)
        if aggregate is None:
            raise DomainError(
                ErrorCode.EXECUTION_ENVIRONMENT_NOT_FOUND,
                "执行环境不存在或不属于当前账号",
                status_code=404,
            )
        if int(aggregate.binding.revision) != expected_revision:
            raise DomainError(
                ErrorCode.REVISION_CONFLICT,
                "执行环境状态已变化，请刷新后重试",
                status_code=409,
            )
        task = await self._tasks.submit_account_task(
            account_id,
            task_type=task_type,
            payload={
                "environmentId": environment_id,
                "expectedRevision": expected_revision,
            },
            idempotency_key=idempotency_key,
            request_id=request_id,
            operation_id=operation_id,
            timeout_seconds=self._task_timeout_seconds,
        )
        return TaskAcceptedDto.from_record(task)

    @staticmethod
    def _to_dto(
        aggregate: ExecutionEnvironmentAggregate,
    ) -> ExecutionEnvironmentDto:
        metadata = _metadata(aggregate.binding.metadata_json)
        browser_kind = metadata.get("browserKind")
        if browser_kind not in {"chrome", "edge"}:
            browser_kind = "chrome"
        display_name = metadata.get("workspaceDisplayName")
        return ExecutionEnvironmentDto(
            id=aggregate.binding.id,
            accountId=aggregate.binding.account_id,
            name=str(metadata.get("name") or aggregate.workspace.name),
            status=aggregate.binding.status,
            workspace=ExecutionEnvironmentWorkspaceDto(
                id=aggregate.workspace.id,
                rootRef=aggregate.workspace.root_ref or "",
                displayName=(
                    str(display_name)
                    if isinstance(display_name, str) and display_name
                    else aggregate.workspace.name
                ),
                status=aggregate.workspace.status,
                ownershipState=aggregate.workspace.ownership_state,
            ),
            browser=ExecutionEnvironmentBrowserDto(
                id=aggregate.browser.id,
                kind=browser_kind,
                displayName=aggregate.browser.name,
                status=aggregate.browser.status,
                ownershipVerified=(
                    aggregate.browser.status == "running"
                    and _has_ownership_evidence(
                        aggregate.browser.runtime_evidence_json
                    )
                ),
                lastCheckedAt=(
                    aggregate.browser.last_checked_at.isoformat()
                    if aggregate.browser.last_checked_at
                    else None
                ),
            ),
            eligibility=evaluate_environment(aggregate),
            revision=max(1, int(aggregate.binding.revision)),
            errorCode=aggregate.binding.error_code,
            errorLogId=aggregate.binding.error_log_id,
            errorMessage=aggregate.browser.error_message,
            lastTaskId=aggregate.binding.last_task_id,
            lastRetryOfTaskId=aggregate.binding.last_retry_of_task_id,
            recoveryActions=_recovery_actions(aggregate),
        )


def _metadata(raw: str | None) -> dict[str, object]:
    try:
        value = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _has_ownership_evidence(raw: str | None) -> bool:
    try:
        value = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return False
    return isinstance(value, dict) and value.get("ownerMarkerVersion") == 1


def _recovery_actions(
    aggregate: ExecutionEnvironmentAggregate,
) -> list[str]:
    actions: list[str] = []
    if aggregate.binding.status == "failed":
        if aggregate.binding.last_task_id:
            actions.append("retry_provision")
        actions.append("check")
    if aggregate.binding.error_code in {
        ErrorCode.WORKSPACE_ROOT_NOT_FOUND.value,
        ErrorCode.WORKSPACE_ROOT_REVOKED.value,
        ErrorCode.WORKSPACE_ROOT_EXPIRED.value,
        ErrorCode.WORKSPACE_ROOT_NOT_WRITABLE.value,
    }:
        actions.append("reauthorize_root")
    if aggregate.binding.error_log_id:
        actions.append("view_log")
    if aggregate.binding.status in {"failed", "cleanup_failed", "inactive"}:
        actions.append("delete_preserving_files")
    return actions
