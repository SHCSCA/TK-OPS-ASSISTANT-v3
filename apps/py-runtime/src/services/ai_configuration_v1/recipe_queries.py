from __future__ import annotations

from collections.abc import Mapping

from common.pagination import CursorPosition
from domain.models.ai_configuration_v1 import AccountAIRecipe
from errors import DomainError, ErrorCode
from services.accounts.guards import require_account
from services.accounts.types import (
    ReadinessItem,
    ReadinessStatus,
    SuggestedAction,
    SuggestedActionKey,
)

from .dto import recipe_summary_to_dto, recipe_version_to_dto
from .dependency_snapshots import dependency_snapshot_to_dto
from .recipe_validation import validate_recipe
from .unit_of_work import AIConfigurationTransaction


def require_recipe_version(
    transaction: AIConfigurationTransaction,
    account_id: str,
    version: int,
) -> AccountAIRecipe:
    row = transaction.ai.recipes.get(
        transaction.session,
        account_id,
        version=version,
    )
    if row is None:
        raise DomainError(
            ErrorCode.AI_RECIPE_INVALID,
            "账号 AI 配方版本不存在",
            status_code=404,
        )
    return row


def load_recipe_version_replay(
    transaction: AIConfigurationTransaction,
    resource_type: str,
    resource_id: str,
    *,
    account_id: str,
) -> Mapping[str, object]:
    if resource_type != "account_ai_recipe_version":
        raise _bad_recipe_replay()
    row = transaction.ai.recipes.get_by_id(
        transaction.session,
        account_id,
        resource_id,
    )
    if row is None:
        raise _bad_recipe_replay()
    return recipe_version_to_dto(row)


def load_recipe_validation_replay(
    transaction: AIConfigurationTransaction,
    resource_type: str,
    resource_id: str,
    *,
    account_id: str,
) -> Mapping[str, object]:
    if resource_type != "account_ai_recipe_validation":
        raise _bad_recipe_replay()
    row = transaction.ai.recipes.get_by_id(
        transaction.session,
        account_id,
        resource_id,
    )
    if row is None:
        raise _bad_recipe_replay()
    if row.dependency_snapshot_id is None:
        raise _bad_recipe_replay()
    snapshot = transaction.ai.dependency_snapshots.get(
        transaction.session,
        row.dependency_snapshot_id,
    )
    if snapshot is None:
        raise _bad_recipe_replay()
    validation = validate_recipe(transaction, row)
    validation["dependencySnapshot"] = dependency_snapshot_to_dto(snapshot)
    return validation


def load_recipe_summary_replay(
    transaction: AIConfigurationTransaction,
    resource_type: str,
    resource_id: str,
    *,
    account_id: str,
) -> Mapping[str, object]:
    if resource_type != "account_ai_recipe":
        raise _bad_recipe_replay()
    if transaction.ai.recipes.get_by_id(
        transaction.session,
        account_id,
        resource_id,
    ) is None:
        raise _bad_recipe_replay()
    account = require_account(
        account_id,
        transaction.session,
        transaction.accounts,
    )
    return recipe_summary_to_dto(
        account_id,
        transaction.ai.recipes.list_versions(
            transaction.session,
            account_id,
        ),
        account_revision=int(account.revision),
    )


def _bad_recipe_replay() -> DomainError:
    return DomainError(
        ErrorCode.INTERNAL_ERROR,
        "账号 AI 配方幂等记录异常，请查看诊断日志",
        status_code=500,
        loggable=True,
    )


def recipe_cursor_start(
    rows: tuple[AccountAIRecipe, ...],
    cursor: CursorPosition | None,
) -> int:
    if cursor is None:
        return 0
    for index, row in enumerate(rows):
        if (
            row.id == cursor.resource_id
            and str(row.version) == cursor.sort_value
        ):
            return index + 1
    raise DomainError(
        ErrorCode.REQUEST_VALIDATION_FAILED,
        "账号 AI 配方分页游标已失效，请重新加载",
        status_code=422,
    )


def missing_recipe() -> ReadinessItem:
    return ReadinessItem(
        status=ReadinessStatus.MISSING,
        label="AI 配方待配置",
        error_code="AI_RECIPE_REQUIRED",
        suggested_action=open_recipe_action("配置 AI 创作档案"),
    )


def open_recipe_action(label: str) -> SuggestedAction:
    return SuggestedAction(
        action_key=SuggestedActionKey.OPEN_AI_RECIPE,
        label=label,
        route_id="account_management",
        section="ai-recipe",
    )


def account_revision_conflict(current_revision: int) -> DomainError:
    return DomainError(
        ErrorCode.REVISION_CONFLICT,
        "账号数据已被更新，请重新加载后再试",
        status_code=412,
        meta={
            "currentRevision": current_revision,
            "invalidations": ["account:detail", "account:ai-recipe"],
        },
    )
