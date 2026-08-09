from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from sqlalchemy.orm import Session

from services.accounts.types import (
    ReadinessItem,
    ReadinessStatus,
    RecipeCopyDecision,
    SuggestedAction,
    SuggestedActionKey,
)


class AccountAIReadinessPort(Protocol):
    def evaluate(
        self,
        session: Session,
        *,
        account_id: str,
        required_capability_keys: Sequence[str],
    ) -> ReadinessItem: ...


class AIRecipeCopyPort(Protocol):
    def copy_active_recipe(
        self,
        session: Session,
        *,
        source_account_id: str,
        target_account_id: str,
    ) -> RecipeCopyDecision: ...


class UnavailableAccountAIReadinessPort:
    def evaluate(
        self,
        session: Session,
        *,
        account_id: str,
        required_capability_keys: Sequence[str],
    ) -> ReadinessItem:
        del session, account_id, required_capability_keys
        return ReadinessItem(
            status=ReadinessStatus.MISSING,
            label="AI 配方待配置",
            error_code="AI_RECIPE_REQUIRED",
            suggested_action=SuggestedAction(
                action_key=SuggestedActionKey.OPEN_AI_RECIPE,
                label="配置 AI 创作档案",
                route_id="ai_system_settings",
                section="account-recipe",
            ),
        )


class UnavailableAIRecipeCopyPort:
    def copy_active_recipe(
        self,
        session: Session,
        *,
        source_account_id: str,
        target_account_id: str,
    ) -> RecipeCopyDecision:
        del session, source_account_id, target_account_id
        return RecipeCopyDecision(
            copied=False,
            reason_code="P0E_AI_RECIPE_NOT_AVAILABLE",
        )
