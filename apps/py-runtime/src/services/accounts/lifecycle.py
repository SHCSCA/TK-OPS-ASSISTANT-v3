from __future__ import annotations

from errors import DomainError, ErrorCode
from services.accounts.types import (
    AccountHealthFacts,
    AccountLifecycleDecision,
    AccountReadiness,
    AccountStatus,
    ReadinessItem,
    ReadinessOverall,
    ReadinessStatus,
    SuggestedAction,
)

_ALLOWED_TRANSITIONS: dict[AccountStatus, frozenset[AccountStatus]] = {
    AccountStatus.DRAFT: frozenset(
        {AccountStatus.UNBOUND, AccountStatus.ARCHIVED}
    ),
    AccountStatus.UNBOUND: frozenset(
        {
            AccountStatus.READY,
            AccountStatus.ATTENTION,
            AccountStatus.ARCHIVED,
        }
    ),
    AccountStatus.READY: frozenset(
        {AccountStatus.ATTENTION, AccountStatus.ARCHIVED}
    ),
    AccountStatus.ATTENTION: frozenset(
        {
            AccountStatus.UNBOUND,
            AccountStatus.READY,
            AccountStatus.ARCHIVED,
        }
    ),
    AccountStatus.ARCHIVED: frozenset(
        {
            AccountStatus.DRAFT,
            AccountStatus.UNBOUND,
            AccountStatus.READY,
            AccountStatus.ATTENTION,
        }
    ),
}

_BLOCKING_READINESS = frozenset(
    {
        ReadinessStatus.ATTENTION,
        ReadinessStatus.BLOCKED,
        ReadinessStatus.MISSING,
        ReadinessStatus.CHECKING,
    }
)


def compute_account_lifecycle(
    facts: AccountHealthFacts,
) -> AccountLifecycleDecision:
    if facts.archived:
        status = AccountStatus.ARCHIVED
    elif not facts.wizard_completed:
        status = AccountStatus.DRAFT
    elif not facts.has_real_binding or not facts.connection_ever_verified:
        status = _status_for_missing_binding(facts.current_status)
    elif _has_blocking_dependency(facts):
        status = AccountStatus.ATTENTION
    else:
        status = AccountStatus.READY

    readiness = AccountReadiness(
        connection=facts.connection,
        knowledge=facts.knowledge,
        ai=facts.ai,
        overall=_overall_for_status(status),
        checked_at=_latest_checked_at(
            facts.connection,
            facts.knowledge,
            facts.ai,
        ),
        suggested_action=_first_suggested_action(
            facts.connection,
            facts.knowledge,
            facts.ai,
        ),
    )
    return AccountLifecycleDecision(status=status, readiness=readiness)


def ensure_account_transition(
    current: AccountStatus,
    target: AccountStatus,
) -> None:
    if current == target:
        return
    if target in _ALLOWED_TRANSITIONS[current]:
        return
    raise DomainError(
        ErrorCode.ACCOUNT_STATE_TRANSITION_INVALID,
        "当前账号状态不允许执行该状态转换",
        status_code=409,
        meta={
            "currentStatus": current.value,
            "targetStatus": target.value,
        },
    )


def _status_for_missing_binding(current: AccountStatus) -> AccountStatus:
    if current in {AccountStatus.READY, AccountStatus.ATTENTION}:
        return AccountStatus.ATTENTION
    return AccountStatus.UNBOUND


def _has_blocking_dependency(facts: AccountHealthFacts) -> bool:
    if facts.connection.status is not ReadinessStatus.READY:
        return True
    if facts.knowledge.status in _BLOCKING_READINESS:
        return True
    return facts.ai.status is not ReadinessStatus.READY


def _overall_for_status(status: AccountStatus) -> ReadinessOverall:
    if status is AccountStatus.READY:
        return ReadinessOverall.READY
    if status is AccountStatus.ATTENTION:
        return ReadinessOverall.ATTENTION
    return ReadinessOverall.BLOCKED


def _latest_checked_at(*items: ReadinessItem) -> str | None:
    checked_values = tuple(
        item.checked_at for item in items if item.checked_at is not None
    )
    return max(checked_values, default=None)


def _first_suggested_action(
    *items: ReadinessItem,
) -> SuggestedAction | None:
    for item in items:
        if item.status is not ReadinessStatus.READY:
            if item.suggested_action is not None:
                return item.suggested_action
    return None
