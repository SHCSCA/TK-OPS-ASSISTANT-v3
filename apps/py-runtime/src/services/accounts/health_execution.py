from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from domain.models.account_connection import AccountConnection
from errors import DomainError, ErrorCode
from repositories.account_connection_v1_repository import (
    AccountConnectionResources,
)
from services.accounts.events import append_account_event
from services.accounts.guards import (
    require_account,
    require_revision,
    revision_conflict,
)
from services.accounts.lifecycle import ensure_account_transition
from services.accounts.read_model import AccountReadModel
from services.accounts.runtime_policy import AccountRuntimePolicy
from services.accounts.types import AccountStatus
from services.accounts.unit_of_work import (
    AccountTransaction,
    AccountUnitOfWork,
)
from services.browser_runtime import BrowserRuntime
from services.tasks.types import TaskCommitCoordinator

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ConnectionProbeEvidence:
    connection_id: str | None = None
    connection_revision: int | None = None
    connection_auth_status: str | None = None
    binding_id: str | None = None
    binding_status: str | None = None
    workspace_id: str | None = None
    workspace_status: str | None = None
    browser_id: str | None = None
    browser_status: str | None = None
    process_id: int | None = None
    debug_port: int | None = None


@dataclass(frozen=True, slots=True)
class ConnectionProbeResult:
    evidence: ConnectionProbeEvidence
    auth_status: str | None
    health_status: str | None
    error_code: str | None


class AccountHealthExecutor:
    """执行真实环境探测，并在单个事务中更新账号健康聚合。"""

    def __init__(
        self,
        unit_of_work: AccountUnitOfWork,
        *,
        read_model: AccountReadModel,
        browser_runtime: BrowserRuntime,
        policy_provider: Callable[[], AccountRuntimePolicy],
    ) -> None:
        self._unit_of_work = unit_of_work
        self._read_model = read_model
        self._browser_runtime = browser_runtime
        self._policy_provider = policy_provider

    def run(
        self,
        account_id: str,
        *,
        checks: tuple[str, ...],
        restore: bool,
        expected_revision: int | None,
        require_connection: bool,
        commit_coordinator: TaskCommitCoordinator,
    ) -> int:
        probe = (
            self._probe_connection(
                account_id,
                allow_archived=restore,
                require_connection=require_connection,
            )
            if "connection" in checks
            else None
        )
        commit_coordinator.raise_if_termination_won()
        return self._apply_result(
            account_id,
            checks=checks,
            restore=restore,
            expected_revision=expected_revision,
            probe=probe,
            commit_coordinator=commit_coordinator,
        )

    def _probe_connection(
        self,
        account_id: str,
        *,
        allow_archived: bool,
        require_connection: bool,
    ) -> ConnectionProbeResult | None:
        with self._unit_of_work.read() as transaction:
            require_account(
                account_id,
                transaction.session,
                transaction.accounts,
                allow_archived=allow_archived,
            )
            resources = transaction.connections.get_connection(
                account_id,
                transaction.session,
            )
            evidence = _freeze_connection_evidence(resources)
            if (
                resources is None
                or resources.execution_binding is None
                or resources.device_workspace is None
                or resources.browser_instance is None
            ):
                if require_connection:
                    raise DomainError(
                        ErrorCode.WORKSPACE_UNAVAILABLE,
                        "账号没有可验证的真实执行绑定",
                        status_code=409,
                    )
                return ConnectionProbeResult(
                    evidence=evidence,
                    auth_status=None,
                    health_status=None,
                    error_code=None,
                )
            auth_status = resources.connection.auth_status

        health = self._browser_runtime.health(
            process_id=evidence.process_id,
            debug_port=evidence.debug_port,
        )
        if not health.alive:
            return ConnectionProbeResult(
                evidence=evidence,
                auth_status=auth_status,
                health_status="failed",
                error_code=(
                    health.error_code or ErrorCode.WORKSPACE_UNAVAILABLE.value
                ),
            )
        if auth_status != "valid":
            return ConnectionProbeResult(
                evidence=evidence,
                auth_status=auth_status,
                health_status="attention",
                error_code=ErrorCode.ACCOUNT_CONNECTION_REQUIRED.value,
            )
        return ConnectionProbeResult(
            evidence=evidence,
            auth_status="valid",
            health_status="ready",
            error_code=None,
        )

    def _apply_result(
        self,
        account_id: str,
        *,
        checks: tuple[str, ...],
        restore: bool,
        expected_revision: int | None,
        probe: ConnectionProbeResult | None,
        commit_coordinator: TaskCommitCoordinator,
    ) -> int:
        commit_coordinator.raise_if_termination_won()
        policy = self._policy_provider()
        now = _utc_now_text()
        with self._unit_of_work.write(
            commit_coordinator=commit_coordinator
        ) as transaction:
            transaction.accounts.acquire_write_lock(
                transaction.session,
                account_id=account_id,
            )
            account = require_account(
                account_id,
                transaction.session,
                transaction.accounts,
                allow_archived=restore,
            )
            if restore:
                if expected_revision is None:
                    raise DomainError(
                        ErrorCode.REQUEST_VALIDATION_FAILED,
                        "恢复账号缺少预期修订号",
                        status_code=422,
                    )
                require_revision(account, expected_revision)
                if account.status != AccountStatus.ARCHIVED.value:
                    raise DomainError(
                        ErrorCode.ACCOUNT_STATE_TRANSITION_INVALID,
                        "只有归档账号可以执行恢复复检",
                        status_code=409,
                    )

            saved_probe: AccountConnection | None = None
            if probe is not None:
                saved_probe = self._save_connection_probe(
                    transaction,
                    account_id=account_id,
                    probe=probe,
                    checked_at=now,
                )

            decision = self._read_model.lifecycle_decision(
                transaction,
                account,
                required_capabilities=policy.required_capabilities,
                archived_override=False if restore else None,
                current_status_override=(
                    AccountStatus.UNBOUND if restore else None
                ),
            )
            ensure_account_transition(
                AccountStatus(account.status),
                decision.status,
            )
            updated = transaction.accounts.set_lifecycle(
                transaction.session,
                account_id=account_id,
                expected_revision=int(account.revision),
                status=decision.status.value,
                status_reason_code=_status_reason(decision.status),
                wizard_completed_at=account.wizard_completed_at,
                archived_at=None if restore else account.archived_at,
                health_checked_at=now,
                updated_at=now,
            )
            if updated is None:
                latest = require_account(
                    account_id,
                    transaction.session,
                    transaction.accounts,
                    allow_archived=True,
                )
                raise revision_conflict(latest)
            invalidations = [
                "accounts:list",
                f"account:{account_id}:detail",
                f"account:{account_id}:workspace",
                f"account:{account_id}:readiness",
            ]
            if saved_probe is not None:
                append_account_event(
                    transaction,
                    account_id=account_id,
                    event_type="account.connection.updated",
                    aggregate_type="account_connection",
                    aggregate_id=saved_probe.id,
                    revision=int(updated.revision),
                    invalidations=[
                        f"account:{account_id}:connection",
                        f"account:{account_id}:readiness",
                    ],
                    values={
                        "healthStatus": saved_probe.health_status,
                        "authStatus": saved_probe.auth_status,
                        "errorCode": saved_probe.error_code,
                    },
                    topic_resource="connection",
                )
            append_account_event(
                transaction,
                account_id=account_id,
                event_type="account.health.updated",
                aggregate_type="account",
                aggregate_id=account_id,
                revision=int(updated.revision),
                invalidations=invalidations,
                values={
                    "checks": list(checks),
                    "restored": restore,
                    "status": updated.status,
                },
            )
            commit_coordinator.raise_if_termination_won()
            return int(updated.revision)

    @staticmethod
    def _save_connection_probe(
        transaction: AccountTransaction,
        *,
        account_id: str,
        probe: ConnectionProbeResult,
        checked_at: str,
    ) -> AccountConnection | None:
        resources = transaction.connections.get_connection(
            account_id,
            transaction.session,
        )
        current_evidence = _freeze_connection_evidence(resources)
        if current_evidence != probe.evidence:
            _raise_probe_revision_conflict(
                account_id,
                expected=probe.evidence,
                current=current_evidence,
            )
        if probe.auth_status is None or probe.health_status is None:
            return None
        connection_id = probe.evidence.connection_id
        connection_revision = probe.evidence.connection_revision
        if (
            resources is None
            or connection_id is None
            or connection_revision is None
        ):
            log.error(
                "账号连接探测结果缺少可提交的冻结证据",
                extra={"account_id": account_id},
            )
            raise DomainError(
                ErrorCode.INTERNAL_ERROR,
                "账号连接探测证据不完整，请重新运行健康检查",
                status_code=500,
                loggable=True,
            )
        updated = transaction.connections.update_connection_state(
            account_id,
            transaction.session,
            connection_id=connection_id,
            expected_revision=connection_revision,
            auth_status=probe.auth_status,
            health_status=probe.health_status,
            last_checked_at=checked_at,
            error_code=probe.error_code,
            error_log_id=None,
            updated_at=checked_at,
        )
        if updated is None:
            raise DomainError(
                ErrorCode.REVISION_CONFLICT,
                "账号连接状态已被其他操作更新",
                status_code=412,
            )
        return updated


def _freeze_connection_evidence(
    resources: AccountConnectionResources | None,
) -> ConnectionProbeEvidence:
    if resources is None:
        return ConnectionProbeEvidence()
    connection = resources.connection
    binding = resources.execution_binding
    workspace = resources.device_workspace
    browser = resources.browser_instance
    return ConnectionProbeEvidence(
        connection_id=connection.id,
        connection_revision=int(connection.revision),
        connection_auth_status=connection.auth_status,
        binding_id=connection.active_execution_binding_id,
        binding_status=None if binding is None else binding.status,
        workspace_id=(
            None if binding is None else binding.device_workspace_id
        ),
        workspace_status=None if workspace is None else workspace.status,
        browser_id=(
            None if binding is None else binding.browser_instance_id
        ),
        browser_status=None if browser is None else browser.status,
        process_id=None if browser is None else browser.process_id,
        debug_port=None if browser is None else browser.debug_port,
    )


def _raise_probe_revision_conflict(
    account_id: str,
    *,
    expected: ConnectionProbeEvidence,
    current: ConnectionProbeEvidence,
) -> None:
    log.warning(
        "账号连接探测证据已变化，拒绝写回过期结果",
        extra={
            "account_id": account_id,
            "expected_connection_id": expected.connection_id,
            "current_connection_id": current.connection_id,
            "expected_connection_revision": expected.connection_revision,
            "current_connection_revision": current.connection_revision,
            "expected_binding_id": expected.binding_id,
            "current_binding_id": current.binding_id,
            "expected_binding_status": expected.binding_status,
            "current_binding_status": current.binding_status,
            "expected_workspace_status": expected.workspace_status,
            "current_workspace_status": current.workspace_status,
            "expected_browser_id": expected.browser_id,
            "current_browser_id": current.browser_id,
            "expected_browser_status": expected.browser_status,
            "current_browser_status": current.browser_status,
            "expected_process_id": expected.process_id,
            "current_process_id": current.process_id,
            "expected_debug_port": expected.debug_port,
            "current_debug_port": current.debug_port,
        },
    )
    raise DomainError(
        ErrorCode.REVISION_CONFLICT,
        "账号连接证据已被更新，请重新运行健康检查",
        status_code=412,
        meta={
            "invalidations": [
                f"account:{account_id}:connection",
                f"account:{account_id}:readiness",
                f"account:{account_id}:workspace",
            ]
        },
    )


def _status_reason(status: AccountStatus) -> str | None:
    if status is AccountStatus.UNBOUND:
        return ErrorCode.ACCOUNT_CONNECTION_REQUIRED.value
    if status is AccountStatus.ATTENTION:
        return "ACCOUNT_DEPENDENCY_ATTENTION"
    return None


def _utc_now_text() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace(
        "+00:00",
        "Z",
    )
