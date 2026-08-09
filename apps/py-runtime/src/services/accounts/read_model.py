from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence

from common.pagination import CursorPosition
from domain.models.account import Account
from repositories.account_workspace_v1_repository import (
    AccountFilterStatus,
)
from schemas.v1.account_common import AccountDto, AccountListDto
from schemas.v1.accounts import (
    AccountNavigationDto,
    AccountTaskSummaryDto,
    AccountWorkspaceContextDto,
    AccountWorkspaceRouteId,
)
from services.accounts.guards import require_account
from services.accounts.presentation import account_to_dto
from services.accounts.readiness import AccountReadinessEvaluator
from services.accounts.runtime_policy import AccountRuntimePolicy
from services.accounts.types import AccountLifecycleDecision, AccountStatus
from services.accounts.unit_of_work import (
    AccountTransaction,
    AccountUnitOfWork,
)

_ACCOUNT_ROUTE_IDS: tuple[AccountWorkspaceRouteId, ...] = (
    "account_workspace_home",
    "account_strategy_knowledge",
    "account_script_topic",
    "account_storyboard_planning",
    "account_video_deconstruction",
    "account_batch_production",
    "account_content_library",
    "account_media_toolbox",
    "account_publishing",
    "account_review",
)
_ACCOUNT_ROUTE_PATHS = frozenset(
    {
        "/workspace",
        "/strategy-knowledge",
        "/scripts",
        "/storyboards",
        "/video-deconstruction",
        "/production/batches",
        "/content-library",
        "/media-tools",
        "/publishing",
        "/review",
    }
)


class _PositioningSummaryUnloaded:
    pass


_POSITIONING_UNLOADED = _PositioningSummaryUnloaded()


class AccountReadModel:
    def __init__(
        self,
        unit_of_work: AccountUnitOfWork,
        *,
        readiness_evaluator: AccountReadinessEvaluator,
        policy_provider: Callable[[], AccountRuntimePolicy],
        recent_pages_provider: Callable[[], Mapping[str, object]],
    ) -> None:
        self._unit_of_work = unit_of_work
        self._readiness = readiness_evaluator
        self._policy_provider = policy_provider
        self._recent_pages_provider = recent_pages_provider

    def list_accounts(
        self,
        *,
        limit: int,
        cursor: CursorPosition | None,
        query: str | None,
        status: AccountFilterStatus | None,
    ) -> tuple[AccountListDto, CursorPosition | None]:
        policy = self._policy_provider()
        with self._unit_of_work.read() as transaction:
            page = transaction.accounts.list_page(
                transaction.session,
                limit=limit,
                cursor=cursor,
                query=query,
                status=status,
            )
            summaries = transaction.accounts.active_positioning_summaries(
                transaction.session,
                account_ids=tuple(account.id for account in page.items),
            )
            items = [
                self.to_dto(
                    transaction,
                    account,
                    required_capabilities=policy.required_capabilities,
                    positioning_summary=summaries.get(account.id),
                )
                for account in page.items
            ]
            return (
                AccountListDto(
                    items=items,
                    totalKnown=page.total_known,
                ),
                page.next_position,
            )

    def get_account(
        self,
        account_id: str,
        *,
        allow_archived: bool,
    ) -> AccountDto:
        policy = self._policy_provider()
        with self._unit_of_work.read() as transaction:
            account = require_account(
                account_id,
                transaction.session,
                transaction.accounts,
                allow_archived=allow_archived,
            )
            return self.to_dto(
                transaction,
                account,
                required_capabilities=policy.required_capabilities,
            )

    def get_workspace_context(
        self,
        account_id: str,
    ) -> AccountWorkspaceContextDto:
        policy = self._policy_provider()
        recent_pages = self._recent_pages_provider()
        with self._unit_of_work.read() as transaction:
            account = require_account(
                account_id,
                transaction.session,
                transaction.accounts,
            )
            dto = self.to_dto(
                transaction,
                account,
                required_capabilities=policy.required_capabilities,
            )
            counts = transaction.accounts.task_counts(
                transaction.session,
                account_id=account_id,
            )
            return AccountWorkspaceContextDto(
                account=dto,
                readiness=dto.readiness,
                navigation=AccountNavigationDto(
                    lastRoute=_last_account_route(account_id, recent_pages),
                    availableRoutes=list(_ACCOUNT_ROUTE_IDS),
                ),
                taskSummary=AccountTaskSummaryDto(
                    running=counts.running,
                    failed=counts.failed,
                ),
                workspaceRevision=int(account.revision),
            )

    def to_dto(
        self,
        transaction: AccountTransaction,
        account: Account,
        *,
        required_capabilities: Sequence[str],
        positioning_summary: (
            str | None | _PositioningSummaryUnloaded
        ) = _POSITIONING_UNLOADED,
    ) -> AccountDto:
        decision = self.lifecycle_decision(
            transaction,
            account,
            required_capabilities=required_capabilities,
        )
        resolved_summary = positioning_summary
        if isinstance(resolved_summary, _PositioningSummaryUnloaded):
            active_positioning = (
                transaction.configuration.get_active_positioning(
                    account.id,
                    transaction.session,
                )
            )
            resolved_summary = (
                None
                if active_positioning is None
                else active_positioning.summary
            )
        return account_to_dto(
            account,
            decision,
            positioning_summary=resolved_summary,
        )

    def lifecycle_decision(
        self,
        transaction: AccountTransaction,
        account: Account,
        *,
        required_capabilities: Sequence[str],
        wizard_completed_override: bool | None = None,
        archived_override: bool | None = None,
        current_status_override: AccountStatus | None = None,
    ) -> AccountLifecycleDecision:
        resources = transaction.connections.get_connection(
            account.id,
            transaction.session,
        )
        knowledge_base = transaction.knowledge.get_base(
            account.id,
            transaction.session,
        )
        decision = self._readiness.evaluate(
            transaction.session,
            account=account,
            connection=(
                None if resources is None else resources.connection
            ),
            binding_is_valid=(
                resources is not None
                and resources.execution_binding is not None
                and resources.device_workspace is not None
                and resources.browser_instance is not None
            ),
            knowledge_base=knowledge_base,
            required_capability_keys=required_capabilities,
            wizard_completed_override=wizard_completed_override,
            archived_override=archived_override,
            current_status_override=current_status_override,
        )
        return decision


def _last_account_route(
    account_id: str,
    recent_pages: Mapping[str, object],
) -> str:
    candidate = recent_pages.get(account_id)
    if isinstance(candidate, str) and candidate in _ACCOUNT_ROUTE_PATHS:
        return candidate
    return "/workspace"
