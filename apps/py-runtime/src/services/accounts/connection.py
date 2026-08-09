from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import uuid4

from domain.models.account import Account
from domain.models.account_connection import AccountConnection
from errors import DomainError, ErrorCode
from repositories.account_connection_v1_repository import (
    ExecutionBindingResources,
)
from repositories.execution_environment_v1_repository import (
    ExecutionEnvironmentAggregate,
)
from schemas.v1.accounts import (
    ConnectionBindingInput,
    ConnectionCandidatesDto,
    ConnectionDto,
)
from services.accounts.connection_presentation import (
    connection_candidate_to_dto,
    connection_to_dto,
)
from services.accounts.events import append_account_event
from services.accounts.guards import (
    require_account,
    require_revision,
    revision_conflict,
)
from services.accounts.idempotency import MutationCommand
from services.accounts.results import AccountServiceResponse
from services.accounts.types import AccountStatus
from services.accounts.unit_of_work import (
    AccountMutationExecutor,
    AccountTransaction,
    AccountUnitOfWork,
    MutationWorkResult,
)
from services.execution_environments.eligibility import evaluate_environment

log = logging.getLogger(__name__)


class AccountConnectionService:
    def __init__(
        self,
        unit_of_work: AccountUnitOfWork,
        mutation_executor: AccountMutationExecutor,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._mutations = mutation_executor

    def get(self, account_id: str) -> ConnectionDto:
        with self._unit_of_work.read() as transaction:
            account = require_account(
                account_id,
                transaction.session,
                transaction.accounts,
            )
            resources = transaction.connections.get_connection(
                account_id,
                transaction.session,
            )
            return connection_to_dto(
                account_id,
                resources,
                account_revision=int(account.revision),
            )

    def list_candidates(self, account_id: str) -> ConnectionCandidatesDto:
        with self._unit_of_work.read() as transaction:
            require_account(
                account_id,
                transaction.session,
                transaction.accounts,
            )
            resources = transaction.connections.list_connection_candidates(
                account_id,
                transaction.session,
            )
            return ConnectionCandidatesDto(
                items=[
                    connection_candidate_to_dto(item)
                    for item in resources
                    if _binding_eligibility(item).eligible
                ]
            )

    def bind(
        self,
        account_id: str,
        payload: ConnectionBindingInput,
        *,
        expected_revision: int,
        idempotency_key: str,
    ) -> AccountServiceResponse:
        execution = self._mutations.execute(
            MutationCommand(
                account_id=account_id,
                operation_name="account.connection.bind",
                idempotency_key=idempotency_key,
                request_payload={
                    **payload.model_dump(mode="json"),
                    "expectedRevision": expected_revision,
                },
            ),
            lambda transaction: self._bind(
                transaction,
                account_id=account_id,
                payload=payload,
                expected_revision=expected_revision,
            ),
        )
        return AccountServiceResponse.from_mutation(execution)

    def unbind(
        self,
        account_id: str,
        *,
        expected_revision: int,
        idempotency_key: str,
    ) -> AccountServiceResponse:
        execution = self._mutations.execute(
            MutationCommand(
                account_id=account_id,
                operation_name="account.connection.unbind",
                idempotency_key=idempotency_key,
                request_payload={"expectedRevision": expected_revision},
            ),
            lambda transaction: self._unbind(
                transaction,
                account_id=account_id,
                expected_revision=expected_revision,
            ),
        )
        return AccountServiceResponse.from_mutation(execution)

    @staticmethod
    def _bind(
        transaction: AccountTransaction,
        *,
        account_id: str,
        payload: ConnectionBindingInput,
        expected_revision: int,
    ) -> MutationWorkResult:
        transaction.accounts.acquire_write_lock(
            transaction.session,
            account_id=account_id,
        )
        account = require_account(
            account_id,
            transaction.session,
            transaction.accounts,
        )
        require_revision(account, expected_revision)
        evidence = transaction.connections.resolve_active_binding(
            account_id,
            transaction.session,
            binding_id=payload.environmentId,
        )
        if evidence is None:
            raise DomainError(
                ErrorCode.EXECUTION_ENVIRONMENT_NOT_FOUND,
                "未找到属于当前账号的执行环境",
                status_code=409,
            )
        eligibility = _binding_eligibility(evidence)
        if (
            not eligibility.eligible
            or eligibility.evidenceRevision != payload.eligibilityRevision
        ):
            raise DomainError(
                ErrorCode.EXECUTION_ENVIRONMENT_NOT_ELIGIBLE,
                "执行环境资格已变化，请刷新候选后重试",
                status_code=409,
                log_context={
                    "environmentId": payload.environmentId,
                    "requestedRevision": payload.eligibilityRevision,
                    "actualRevision": eligibility.evidenceRevision,
                    "blockingIssueCodes": [
                        item.code for item in eligibility.blockingIssues
                    ],
                },
            )
        workspace = evidence.device_workspace
        browser = evidence.browser_instance
        binding = transaction.connections.activate_execution_binding(
            account_id,
            transaction.session,
            binding_id=evidence.execution_binding.id,
        )
        if binding is None:
            log.warning(
                "账号绑定未找到现有执行环境证据",
                extra={
                    "account_id": account_id,
                    "workspace_id": workspace.id,
                    "browser_instance_id": browser.id,
                },
            )
            raise DomainError(
                ErrorCode.WORKSPACE_UNAVAILABLE,
                "所选工作区与浏览器尚无可复用的真实执行绑定",
                status_code=409,
            )
        now = _utc_now_text()
        resources = transaction.connections.get_connection(
            account_id,
            transaction.session,
        )
        if resources is None:
            connection = transaction.connections.add_connection(
                account_id,
                transaction.session,
                AccountConnection(
                    id=f"conn_{uuid4().hex}",
                    account_id=account_id,
                    credential_ref=None,
                    session_ref=None,
                    auth_status="required",
                    health_status="unknown",
                    active_execution_binding_id=binding.id,
                    last_checked_at=None,
                    error_code=None,
                    error_log_id=None,
                    revision=1,
                    created_at=now,
                    updated_at=now,
                ),
            )
        else:
            preserve_verified_state = (
                resources.connection.active_execution_binding_id
                == binding.id
            )
            connection = transaction.connections.set_active_binding(
                account_id,
                transaction.session,
                connection_id=resources.connection.id,
                binding_id=binding.id,
                expected_revision=int(resources.connection.revision),
                updated_at=now,
            )
            if connection is None:
                raise DomainError(
                    ErrorCode.EXECUTION_BINDING_INVALID,
                    "账号连接已变化或执行绑定证据不完整",
                    status_code=409,
                )
            connection = transaction.connections.update_connection_state(
                account_id,
                transaction.session,
                connection_id=connection.id,
                expected_revision=int(connection.revision),
                auth_status=(
                    resources.connection.auth_status
                    if preserve_verified_state
                    else "required"
                ),
                health_status=(
                    resources.connection.health_status
                    if preserve_verified_state
                    else "unknown"
                ),
                last_checked_at=(
                    resources.connection.last_checked_at
                    if preserve_verified_state
                    else None
                ),
                error_code=(
                    resources.connection.error_code
                    if preserve_verified_state
                    else None
                ),
                error_log_id=(
                    resources.connection.error_log_id
                    if preserve_verified_state
                    else None
                ),
                updated_at=now,
            )
            if connection is None:
                raise DomainError(
                    ErrorCode.EXECUTION_BINDING_INVALID,
                    "账号连接检查状态重置冲突，请重新加载后再试",
                    status_code=409,
                )
        updated_account = _update_account_after_binding_change(
            transaction,
            account=account,
            expected_revision=expected_revision,
            updated_at=now,
            binding_verified=(
                connection.auth_status == "valid"
                and connection.health_status == "ready"
            ),
        )
        resolved = transaction.connections.get_connection(
            account_id,
            transaction.session,
        )
        dto = connection_to_dto(
            account_id,
            resolved,
            account_revision=int(updated_account.revision),
        )
        invalidations = _connection_invalidations(account_id)
        append_account_event(
            transaction,
            account_id=account_id,
            event_type="account.connection.updated",
            aggregate_type="account_connection",
            aggregate_id=connection.id,
            revision=int(updated_account.revision),
            invalidations=invalidations,
            values={
                "bindingId": binding.id,
                "healthStatus": connection.health_status,
            },
        )
        return MutationWorkResult(
            response={
                "data": dto.model_dump(mode="json"),
                "meta": {
                    "revision": int(updated_account.revision),
                    "invalidations": invalidations,
                },
            },
            resource_type="account_connection",
            resource_id=connection.id,
        )

    @staticmethod
    def _unbind(
        transaction: AccountTransaction,
        *,
        account_id: str,
        expected_revision: int,
    ) -> MutationWorkResult:
        transaction.accounts.acquire_write_lock(
            transaction.session,
            account_id=account_id,
        )
        account = require_account(
            account_id,
            transaction.session,
            transaction.accounts,
        )
        require_revision(account, expected_revision)
        resources = transaction.connections.get_connection(
            account_id,
            transaction.session,
        )
        if (
            resources is None
            or resources.connection.active_execution_binding_id is None
        ):
            raise DomainError(
                ErrorCode.ACCOUNT_CONNECTION_REQUIRED,
                "账号尚未建立可解除的真实连接",
                status_code=409,
            )
        now = _utc_now_text()
        connection = transaction.connections.clear_active_binding(
            account_id,
            transaction.session,
            connection_id=resources.connection.id,
            expected_revision=int(resources.connection.revision),
            updated_at=now,
        )
        if connection is None:
            raise DomainError(
                ErrorCode.EXECUTION_BINDING_INVALID,
                "账号连接已变化，请重新加载后再试",
                status_code=409,
            )
        connection = transaction.connections.update_connection_state(
            account_id,
            transaction.session,
            connection_id=connection.id,
            expected_revision=int(connection.revision),
            auth_status=connection.auth_status,
            health_status="attention",
            last_checked_at=connection.last_checked_at,
            error_code=ErrorCode.ACCOUNT_CONNECTION_REQUIRED.value,
            error_log_id=None,
            updated_at=now,
        )
        if connection is None:
            raise DomainError(
                ErrorCode.EXECUTION_BINDING_INVALID,
                "账号连接状态更新冲突，请重新加载后再试",
                status_code=409,
            )
        updated_account = _update_account_after_binding_change(
            transaction,
            account=account,
            expected_revision=expected_revision,
            updated_at=now,
            binding_verified=False,
        )
        dto = connection_to_dto(
            account_id,
            transaction.connections.get_connection(
                account_id,
                transaction.session,
            ),
            account_revision=int(updated_account.revision),
        )
        invalidations = _connection_invalidations(account_id)
        append_account_event(
            transaction,
            account_id=account_id,
            event_type="account.connection.updated",
            aggregate_type="account_connection",
            aggregate_id=connection.id,
            revision=int(updated_account.revision),
            invalidations=invalidations,
            values={
                "bindingId": None,
                "healthStatus": connection.health_status,
            },
        )
        return MutationWorkResult(
            response={
                "data": dto.model_dump(mode="json"),
                "meta": {
                    "revision": int(updated_account.revision),
                    "invalidations": invalidations,
                },
            },
            resource_type="account_connection",
            resource_id=connection.id,
        )


def _update_account_after_binding_change(
    transaction: AccountTransaction,
    *,
    account: Account,
    expected_revision: int,
    updated_at: str,
    binding_verified: bool,
) -> Account:
    current_status = AccountStatus(account.status)
    target_status = (
        AccountStatus.ATTENTION
        if current_status is AccountStatus.READY and not binding_verified
        else current_status
    )
    updated = transaction.accounts.set_lifecycle(
        transaction.session,
        account_id=account.id,
        expected_revision=expected_revision,
        status=target_status.value,
        status_reason_code=(
            "ACCOUNT_CONNECTION_REQUIRED"
            if (
                target_status is AccountStatus.ATTENTION
                and not binding_verified
            )
            else account.status_reason_code
        ),
        wizard_completed_at=account.wizard_completed_at,
        archived_at=account.archived_at,
        health_checked_at=account.last_health_checked_at,
        updated_at=updated_at,
    )
    if updated is None:
        latest = require_account(
            account.id,
            transaction.session,
            transaction.accounts,
        )
        raise revision_conflict(latest)
    return updated


def _connection_invalidations(account_id: str) -> list[str]:
    return [
        "accounts:list",
        f"account:{account_id}:connection",
        f"account:{account_id}:readiness",
        f"account:{account_id}:workspace",
    ]


def _utc_now_text() -> str:
    return _to_utc_text(datetime.now(UTC))


def _to_utc_text(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _binding_eligibility(
    resources: ExecutionBindingResources,
):
    return evaluate_environment(
        ExecutionEnvironmentAggregate(
            resources.execution_binding,
            resources.browser_instance,
            resources.device_workspace,
        )
    )
