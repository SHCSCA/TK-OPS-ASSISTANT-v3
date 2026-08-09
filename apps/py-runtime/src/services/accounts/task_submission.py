from __future__ import annotations

from errors import DomainError, ErrorCode
from schemas.v1.bootstrap import TaskAcceptedDto
from services.accounts.guards import require_account, require_revision
from services.accounts.task_handlers import (
    ACCOUNT_ARCHIVE_CLEANUP_TASK_TYPE,
    ACCOUNT_CONNECTION_CHECK_TASK_TYPE,
    ACCOUNT_HEALTH_TASK_TYPE,
    ACCOUNT_RESTORE_HEALTH_TASK_TYPE,
)
from services.accounts.types import AccountStatus
from services.accounts.unit_of_work import AccountUnitOfWork
from services.tasks.coordinator import TaskCoordinator
from services.tasks.types import JsonValue

_ALL_CHECKS = ("connection", "knowledge", "ai")


class AccountTaskSubmissionService:
    def __init__(
        self,
        unit_of_work: AccountUnitOfWork,
        *,
        coordinator: TaskCoordinator,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._coordinator = coordinator

    async def submit_health_checks(
        self,
        account_id: str,
        *,
        checks: list[str] | None,
        idempotency_key: str,
        request_id: str,
        operation_id: str,
    ) -> TaskAcceptedDto:
        self._validate_account(account_id, allow_archived=False)
        return await self._submit(
            account_id,
            task_type=ACCOUNT_HEALTH_TASK_TYPE,
            payload={"checks": _normalize_checks(checks)},
            idempotency_key=idempotency_key,
            request_id=request_id,
            operation_id=operation_id,
        )

    async def submit_archive_cleanup(
        self,
        account_id: str,
        *,
        expected_revision: int,
        reason_provided: bool,
        idempotency_key: str,
        request_id: str,
        operation_id: str,
    ) -> TaskAcceptedDto:
        self._validate_archive(account_id, expected_revision)
        return await self._submit(
            account_id,
            task_type=ACCOUNT_ARCHIVE_CLEANUP_TASK_TYPE,
            payload={
                "expectedRevision": expected_revision,
                "reasonProvided": reason_provided,
            },
            idempotency_key=idempotency_key,
            request_id=request_id,
            operation_id=operation_id,
        )

    async def submit_restore(
        self,
        account_id: str,
        *,
        checks: list[str] | None,
        expected_revision: int,
        idempotency_key: str,
        request_id: str,
        operation_id: str,
    ) -> TaskAcceptedDto:
        self._validate_restore(account_id, expected_revision)
        return await self._submit(
            account_id,
            task_type=ACCOUNT_RESTORE_HEALTH_TASK_TYPE,
            payload={
                "checks": _normalize_checks(checks),
                "expectedRevision": expected_revision,
            },
            idempotency_key=idempotency_key,
            request_id=request_id,
            operation_id=operation_id,
        )

    async def submit_connection_check(
        self,
        account_id: str,
        *,
        idempotency_key: str,
        request_id: str,
        operation_id: str,
    ) -> TaskAcceptedDto:
        self._validate_connection(account_id)
        return await self._submit(
            account_id,
            task_type=ACCOUNT_CONNECTION_CHECK_TASK_TYPE,
            payload={"checks": ["connection"]},
            idempotency_key=idempotency_key,
            request_id=request_id,
            operation_id=operation_id,
        )

    def _validate_account(
        self,
        account_id: str,
        *,
        allow_archived: bool,
    ) -> None:
        with self._unit_of_work.read() as transaction:
            require_account(
                account_id,
                transaction.session,
                transaction.accounts,
                allow_archived=allow_archived,
            )

    def _validate_restore(
        self,
        account_id: str,
        expected_revision: int,
    ) -> None:
        with self._unit_of_work.read() as transaction:
            account = require_account(
                account_id,
                transaction.session,
                transaction.accounts,
                allow_archived=True,
            )
            require_revision(account, expected_revision)
            if account.status != AccountStatus.ARCHIVED.value:
                raise DomainError(
                    ErrorCode.ACCOUNT_STATE_TRANSITION_INVALID,
                    "只有归档账号可以恢复",
                    status_code=409,
                )

    def _validate_connection(self, account_id: str) -> None:
        with self._unit_of_work.read() as transaction:
            require_account(
                account_id,
                transaction.session,
                transaction.accounts,
            )
            resources = transaction.connections.get_connection(
                account_id,
                transaction.session,
            )
            if (
                resources is None
                or resources.execution_binding is None
                or resources.device_workspace is None
                or resources.browser_instance is None
            ):
                raise DomainError(
                    ErrorCode.WORKSPACE_UNAVAILABLE,
                    "账号没有可检查的真实工作区与浏览器绑定",
                    status_code=409,
                )

    def _validate_archive(
        self,
        account_id: str,
        expected_revision: int,
    ) -> None:
        with self._unit_of_work.read() as transaction:
            account = require_account(
                account_id,
                transaction.session,
                transaction.accounts,
                allow_archived=True,
            )
            if (
                account.status == AccountStatus.ARCHIVED.value
                or account.status_reason_code
                in {"ARCHIVE_CLEANUP_PENDING", "ARCHIVE_CLEANUP_FAILED"}
            ):
                return
            require_revision(account, expected_revision)

    async def _submit(
        self,
        account_id: str,
        *,
        task_type: str,
        payload: dict[str, JsonValue],
        idempotency_key: str,
        request_id: str,
        operation_id: str,
    ) -> TaskAcceptedDto:
        record = await self._coordinator.submit_account_task(
            account_id,
            task_type=task_type,
            payload=payload,
            idempotency_key=idempotency_key,
            request_id=request_id,
            operation_id=operation_id,
        )
        return TaskAcceptedDto(
            taskId=record.id,
            scope="account",
            accountId=account_id,
            taskType=record.task_type,
            status="queued",
            cancellable=record.cancellable,
            createdAt=record.created_at,
        )


def _normalize_checks(checks: list[str] | None) -> list[str]:
    if checks is None:
        return list(_ALL_CHECKS)
    return list(dict.fromkeys(checks))
