from __future__ import annotations

import logging

from domain.models.account import Account
from schemas.v1.account_common import (
    AccountDto,
    AccountReadinessDto,
    ReadinessItemDto,
    SuggestedActionDto,
)
from services.accounts.types import (
    AccountLifecycleDecision,
    AccountReadiness,
    ReadinessItem,
    SuggestedAction,
)

log = logging.getLogger(__name__)


def account_to_dto(
    account: Account,
    decision: AccountLifecycleDecision,
    *,
    positioning_summary: str | None,
) -> AccountDto:
    if account.status != decision.status.value:
        log.warning(
            "账号持久状态与实时就绪计算不一致",
            extra={
                "account_id": account.id,
                "resource_type": "account",
                "resource_id": account.id,
            },
        )
    return AccountDto(
        id=account.id,
        name=account.name,
        username=account.username,
        platform="tiktok",
        status=decision.status.value,
        positioningSummary=positioning_summary,
        lastUsedAt=account.last_used_at,
        readiness=readiness_to_dto(decision.readiness),
        wizardCompletedAt=account.wizard_completed_at,
        revision=int(account.revision),
    )


def readiness_to_dto(readiness: AccountReadiness) -> AccountReadinessDto:
    return AccountReadinessDto(
        connection=_readiness_item_to_dto(readiness.connection),
        knowledge=_readiness_item_to_dto(readiness.knowledge),
        ai=_readiness_item_to_dto(readiness.ai),
        overall=readiness.overall.value,
        checkedAt=readiness.checked_at,
        suggestedAction=_suggested_action_to_dto(
            readiness.suggested_action
        ),
    )


def _readiness_item_to_dto(item: ReadinessItem) -> ReadinessItemDto:
    return ReadinessItemDto(
        status=item.status.value,
        label=item.label,
        errorCode=item.error_code,
        logId=item.log_id,
        checkedAt=item.checked_at,
        suggestedAction=_suggested_action_to_dto(item.suggested_action),
    )


def _suggested_action_to_dto(
    action: SuggestedAction | None,
) -> SuggestedActionDto | None:
    if action is None:
        return None
    return SuggestedActionDto(
        actionKey=action.action_key.value,
        label=action.label,
        routeId=action.route_id,
        section=action.section,
        taskId=action.task_id,
    )
