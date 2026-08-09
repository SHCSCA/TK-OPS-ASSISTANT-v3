from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.orm import Session

from domain.models.account import Account
from domain.models.account_connection import AccountConnection
from domain.models.knowledge import AccountKnowledgeBase
from services.accounts.lifecycle import compute_account_lifecycle
from services.accounts.ports import AccountAIReadinessPort
from services.accounts.types import (
    AccountHealthFacts,
    AccountLifecycleDecision,
    AccountStatus,
    ReadinessItem,
    ReadinessStatus,
    SuggestedAction,
    SuggestedActionKey,
)


class AccountReadinessEvaluator:
    def __init__(self, ai_readiness_port: AccountAIReadinessPort) -> None:
        self._ai_readiness_port = ai_readiness_port

    def evaluate(
        self,
        session: Session,
        *,
        account: Account,
        connection: AccountConnection | None,
        binding_is_valid: bool,
        knowledge_base: AccountKnowledgeBase | None,
        required_capability_keys: Sequence[str],
        wizard_completed_override: bool | None = None,
        archived_override: bool | None = None,
        current_status_override: AccountStatus | None = None,
    ) -> AccountLifecycleDecision:
        connection_item = _connection_readiness(
            connection,
            binding_is_valid=binding_is_valid,
        )
        knowledge_item = knowledge_readiness(knowledge_base)
        ai_item = self._ai_readiness_port.evaluate(
            session,
            account_id=account.id,
            required_capability_keys=required_capability_keys,
        )
        return compute_account_lifecycle(
            AccountHealthFacts(
                current_status=(
                    AccountStatus(account.status)
                    if current_status_override is None
                    else current_status_override
                ),
                archived=(
                    account.status == AccountStatus.ARCHIVED.value
                    if archived_override is None
                    else archived_override
                ),
                wizard_completed=(
                    account.wizard_completed_at is not None
                    if wizard_completed_override is None
                    else wizard_completed_override
                ),
                has_real_binding=binding_is_valid,
                connection_ever_verified=(
                    connection is not None
                    and connection.last_checked_at is not None
                ),
                connection=connection_item,
                knowledge=knowledge_item,
                ai=ai_item,
            )
        )


def _connection_readiness(
    connection: AccountConnection | None,
    *,
    binding_is_valid: bool,
) -> ReadinessItem:
    if connection is None or not binding_is_valid:
        return ReadinessItem(
            status=ReadinessStatus.MISSING,
            label="未连接",
            suggested_action=SuggestedAction(
                action_key=SuggestedActionKey.OPEN_CONNECTION,
                label="配置真实连接",
                route_id="account_management",
                section="connection",
            ),
        )
    if connection.health_status == "checking":
        return ReadinessItem(
            status=ReadinessStatus.CHECKING,
            label="连接检查中",
            checked_at=connection.last_checked_at,
            suggested_action=SuggestedAction(
                action_key=SuggestedActionKey.RUN_HEALTH_CHECK,
                label="查看连接检查",
                route_id="account_management",
                section="connection",
            ),
        )
    if (
        connection.health_status == "ready"
        and connection.auth_status == "valid"
    ):
        return ReadinessItem(
            status=ReadinessStatus.READY,
            label="连接正常",
            checked_at=connection.last_checked_at,
        )
    if connection.health_status == "unknown":
        return ReadinessItem(
            status=ReadinessStatus.MISSING,
            label="连接待验证",
            checked_at=connection.last_checked_at,
            suggested_action=SuggestedAction(
                action_key=SuggestedActionKey.RUN_HEALTH_CHECK,
                label="运行连接检查",
                route_id="account_management",
                section="connection",
            ),
        )
    return ReadinessItem(
        status=ReadinessStatus.ATTENTION,
        label="连接需要处理",
        error_code=connection.error_code,
        log_id=connection.error_log_id,
        checked_at=connection.last_checked_at,
        suggested_action=_connection_repair_action(connection),
    )


def _connection_repair_action(
    connection: AccountConnection,
) -> SuggestedAction:
    if connection.error_log_id is not None:
        return SuggestedAction(
            action_key=SuggestedActionKey.VIEW_LOG,
            label="查看连接日志",
            route_id="account_management",
            section="connection",
        )
    return SuggestedAction(
        action_key=SuggestedActionKey.OPEN_CONNECTION,
        label="修复真实连接",
        route_id="account_management",
        section="connection",
    )


def knowledge_readiness(
    knowledge_base: AccountKnowledgeBase | None,
) -> ReadinessItem:
    if knowledge_base is None:
        return ReadinessItem(
            status=ReadinessStatus.MISSING,
            label="知识库待创建",
            suggested_action=SuggestedAction(
                action_key=SuggestedActionKey.OPEN_KNOWLEDGE,
                label="创建账号知识库",
                route_id="account_strategy_knowledge",
                section="knowledge",
            ),
        )
    if knowledge_base.status == "empty":
        return ReadinessItem(
            status=ReadinessStatus.EMPTY,
            label="待补充",
            checked_at=knowledge_base.last_indexed_at,
            suggested_action=SuggestedAction(
                action_key=SuggestedActionKey.OPEN_KNOWLEDGE,
                label="添加知识来源",
                route_id="account_strategy_knowledge",
                section="knowledge",
            ),
        )
    if knowledge_base.status == "indexing":
        return ReadinessItem(
            status=ReadinessStatus.CHECKING,
            label="知识索引中",
            checked_at=knowledge_base.last_indexed_at,
        )
    if knowledge_base.status == "ready":
        return ReadinessItem(
            status=ReadinessStatus.READY,
            label="知识可用",
            checked_at=knowledge_base.last_indexed_at,
        )
    return ReadinessItem(
        status=ReadinessStatus.ATTENTION,
        label="知识库需要处理",
        error_code=knowledge_base.error_code,
        log_id=knowledge_base.error_log_id,
        checked_at=knowledge_base.last_indexed_at,
        suggested_action=_knowledge_repair_action(knowledge_base),
    )


def _knowledge_repair_action(
    knowledge_base: AccountKnowledgeBase,
) -> SuggestedAction:
    if knowledge_base.error_log_id is not None:
        return SuggestedAction(
            action_key=SuggestedActionKey.VIEW_LOG,
            label="查看知识索引日志",
            route_id="account_strategy_knowledge",
            section="knowledge",
        )
    return SuggestedAction(
        action_key=SuggestedActionKey.OPEN_KNOWLEDGE,
        label="检查知识来源",
        route_id="account_strategy_knowledge",
        section="knowledge",
    )
