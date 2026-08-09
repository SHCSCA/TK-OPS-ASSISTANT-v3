from __future__ import annotations

from collections.abc import Callable

from domain.models.account import Account
from errors import DomainError, ErrorCode
from services.accounts.guards import require_account, revision_conflict
from services.accounts.lifecycle import ensure_account_transition
from services.accounts.read_model import AccountReadModel
from services.accounts.runtime_policy import AccountRuntimePolicy
from services.accounts.types import (
    AccountLifecycleDecision,
    AccountStatus,
    ReadinessStatus,
)
from services.accounts.unit_of_work import AccountTransaction


class AccountLifecycleSynchronizer:
    """在依赖状态变化时同步账号持久生命周期与聚合修订。"""

    def __init__(
        self,
        *,
        read_model: AccountReadModel,
        policy_provider: Callable[[], AccountRuntimePolicy],
    ) -> None:
        self._read_model = read_model
        self._policy_provider = policy_provider

    def update(
        self,
        transaction: AccountTransaction,
        account: Account,
        *,
        updated_at: str,
    ) -> Account:
        policy = self._policy_provider()
        decision = self._read_model.lifecycle_decision(
            transaction,
            account,
            required_capabilities=policy.required_capabilities,
        )
        ensure_account_transition(
            AccountStatus(account.status),
            decision.status,
        )
        updated = transaction.accounts.set_lifecycle(
            transaction.session,
            account_id=account.id,
            expected_revision=int(account.revision),
            status=decision.status.value,
            status_reason_code=_status_reason(account, decision),
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
                allow_archived=True,
            )
            raise revision_conflict(latest)
        return updated


def _status_reason(
    account: Account,
    decision: AccountLifecycleDecision,
) -> str | None:
    status = decision.status
    if status in {AccountStatus.DRAFT, AccountStatus.ARCHIVED}:
        return account.status_reason_code
    if status is AccountStatus.READY:
        return None
    if status is AccountStatus.UNBOUND:
        return ErrorCode.ACCOUNT_CONNECTION_REQUIRED.value

    readiness = decision.readiness
    for item in (
        readiness.connection,
        readiness.knowledge,
        readiness.ai,
    ):
        if item.status is ReadinessStatus.READY:
            continue
        if item.error_code is not None:
            return item.error_code
    if readiness.connection.status is not ReadinessStatus.READY:
        return ErrorCode.ACCOUNT_CONNECTION_REQUIRED.value
    if readiness.knowledge.status is not ReadinessStatus.READY:
        return "KNOWLEDGE_ATTENTION_REQUIRED"
    if readiness.ai.status is not ReadinessStatus.READY:
        return "AI_RECIPE_REQUIRED"
    raise DomainError(
        ErrorCode.INTERNAL_ERROR,
        "账号生命周期与就绪摘要不一致",
        status_code=500,
        loggable=True,
    )
