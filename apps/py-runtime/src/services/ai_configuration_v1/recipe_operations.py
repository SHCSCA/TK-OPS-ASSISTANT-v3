from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from uuid import uuid4

from domain.models.ai_configuration_v1 import AccountAIRecipe
from errors import DomainError, ErrorCode
from services.accounts.guards import require_account

from .dto import recipe_summary_to_dto, recipe_version_to_dto
from .dependency_snapshots import (
    dependency_snapshot_to_dto,
    persist_dependency_snapshot,
    require_unchanged_dependency_snapshot,
)
from .events import append_account_ai_event
from .json_codec import dump_json
from .mutation import AIResourceMutation
from .recipe_queries import (
    account_revision_conflict,
    require_recipe_version,
)
from .recipe_dependencies import resolve_recipe_dependencies
from .recipe_validation import recipe_payload_hash, validate_recipe
from .unit_of_work import AIConfigurationTransaction


def create_recipe_version(
    transaction: AIConfigurationTransaction,
    *,
    account_id: str,
    payload: Mapping[str, object],
    expected_revision: int,
) -> AIResourceMutation:
    transaction.accounts.acquire_write_lock(
        transaction.session,
        account_id=account_id,
    )
    account = require_account(
        account_id,
        transaction.session,
        transaction.accounts,
    )
    if int(account.revision) != expected_revision:
        raise account_revision_conflict(int(account.revision))
    template_ref = payload.get("compositionTemplateRef")
    if isinstance(template_ref, str):
        template = transaction.ai.templates.get_by_id(
            transaction.session,
            template_ref,
        )
        if template is None:
            raise DomainError(
                ErrorCode.COMPOSITION_TEMPLATE_NOT_FOUND,
                "账号配方引用的合成模板不存在",
                status_code=404,
            )
    ai_revision = transaction.ai.revisions.get(transaction.session)
    now = utc_now()
    prior = transaction.ai.recipes.get_active(
        transaction.session,
        account_id,
    )
    version = transaction.ai.recipes.next_version(
        transaction.session,
        account_id,
    )
    digest = recipe_payload_hash(payload)
    row = transaction.ai.recipes.add(
        transaction.session,
        account_id,
        AccountAIRecipe(
            id=f"recipe_{uuid4().hex}",
            account_id=account_id,
            name=str(payload["name"]),
            version=version,
            status="draft",
            route_overrides_json=dump_json(payload["routeOverrides"]),
            visual_style_json=dump_json(payload["visualStyle"]),
            voice_profile_ref=(
                str(payload["voiceProfileRef"])
                if payload.get("voiceProfileRef") is not None
                else None
            ),
            composition_template_ref=(
                str(template_ref) if template_ref is not None else None
            ),
            cost_policy_json=dump_json(payload["costPolicy"]),
            fallback_policy_json=dump_json(payload["fallbackPolicy"]),
            dependency_snapshot_id=None,
            source_ai_config_revision=ai_revision,
            validation_status="incomplete",
            validation_issues_json="[]",
            content_hash=digest,
            revision=1,
            created_from_id=prior.id if prior is not None else None,
            created_at=now,
            activated_at=None,
        ),
    )
    updated_account = transaction.accounts.bump_revision(
        transaction.session,
        account_id=account_id,
        expected_revision=expected_revision,
        updated_at=now,
    )
    if updated_account is None:
        raise account_revision_conflict(int(account.revision))
    invalidations = (
        f"account:{account_id}:ai-recipe",
        f"account:{account_id}:readiness",
    )
    append_account_ai_event(
        transaction,
        account_id=account_id,
        event_type="ai.recipe.updated",
        recipe_id=row.id,
        revision=int(updated_account.revision),
        invalidations=invalidations,
        values={
            "version": version,
            "contentHash": digest,
            "validationStatus": "unvalidated",
        },
    )
    return AIResourceMutation(
        data=recipe_version_to_dto(row),
        resource_type="account_ai_recipe_version",
        resource_id=row.id,
        revision=int(updated_account.revision),
        invalidations=invalidations,
    )


def validate_recipe_version(
    transaction: AIConfigurationTransaction,
    *,
    account_id: str,
    version: int,
) -> AIResourceMutation:
    transaction.accounts.acquire_write_lock(
        transaction.session,
        account_id=account_id,
    )
    account = require_account(
        account_id,
        transaction.session,
        transaction.accounts,
    )
    row = require_recipe_version(transaction, account_id, version)
    validation = validate_recipe(transaction, row)
    resolution = resolve_recipe_dependencies(
        transaction,
        row,
        validation=validation,
    )
    snapshot = persist_dependency_snapshot(
        transaction,
        owner_type="recipe",
        owner_id=row.id,
        owner_revision=int(row.version),
        resolution=resolution,
    )
    validation["dependencySnapshot"] = dependency_snapshot_to_dto(snapshot)
    updated = transaction.ai.recipes.update_validation(
        transaction.session,
        account_id,
        version=version,
        validation_status=(
            "valid"
            if validation["validationStatus"] == "valid"
            else "invalid"
        ),
        validation_issues_json=dump_json(validation["validationIssues"]),
        dependency_snapshot_id=snapshot.id,
        expected_revision=int(row.revision),
    )
    if updated is None:
        raise DomainError(
            ErrorCode.REQUEST_CONFLICT,
            "账号 AI 配方校验状态已变化，请重试",
            status_code=409,
        )
    now = utc_now()
    updated_account = transaction.accounts.bump_revision(
        transaction.session,
        account_id=account_id,
        expected_revision=int(account.revision),
        updated_at=now,
    )
    if updated_account is None:
        raise account_revision_conflict(int(account.revision))
    invalidations = (
        f"account:{account_id}:ai-recipe",
        f"account:{account_id}:readiness",
    )
    append_account_ai_event(
        transaction,
        account_id=account_id,
        event_type="ai.recipe.updated",
        recipe_id=row.id,
        revision=int(updated_account.revision),
        invalidations=invalidations,
        values={
            "version": version,
            "validationStatus": validation["validationStatus"],
        },
    )
    return AIResourceMutation(
        data=validation,
        resource_type="account_ai_recipe_validation",
        resource_id=row.id,
        revision=int(updated_account.revision),
        invalidations=invalidations,
        replay_snapshot_safe=True,
    )


def activate_recipe_version(
    transaction: AIConfigurationTransaction,
    *,
    account_id: str,
    version: int,
    expected_revision: int,
) -> AIResourceMutation:
    transaction.accounts.acquire_write_lock(
        transaction.session,
        account_id=account_id,
    )
    account = require_account(
        account_id,
        transaction.session,
        transaction.accounts,
    )
    if int(account.revision) != expected_revision:
        raise account_revision_conflict(int(account.revision))
    target = require_recipe_version(transaction, account_id, version)
    current_resolution = resolve_recipe_dependencies(transaction, target)
    require_unchanged_dependency_snapshot(
        transaction,
        snapshot_id=target.dependency_snapshot_id,
        current=current_resolution,
    )
    current_ai_revision = transaction.ai.revisions.get(
        transaction.session
    )
    if (
        target.validation_status != "valid"
        or int(target.source_ai_config_revision) != current_ai_revision
    ):
        raise DomainError(
            ErrorCode.AI_RECIPE_INVALID,
            "账号 AI 配方未通过当前系统配置校验",
            status_code=422,
            meta={
                "sourceAiConfigRevision": int(
                    target.source_ai_config_revision
                ),
                "currentAiConfigRevision": current_ai_revision,
            },
        )
    activated = transaction.ai.recipes.activate(
        transaction.session,
        account_id,
        version=version,
        expected_revision=int(target.revision),
        activated_at=utc_now(),
    )
    if activated is None:
        raise DomainError(
            ErrorCode.AI_RECIPE_INVALID,
            "账号 AI 配方无法激活，请重新校验",
            status_code=422,
        )
    updated_account = transaction.accounts.bump_revision(
        transaction.session,
        account_id=account_id,
        expected_revision=expected_revision,
        updated_at=utc_now(),
    )
    if updated_account is None:
        raise account_revision_conflict(int(account.revision))
    invalidations = (
        f"account:{account_id}:ai-recipe",
        f"account:{account_id}:readiness",
        f"account:{account_id}:workspace",
    )
    append_account_ai_event(
        transaction,
        account_id=account_id,
        event_type="ai.recipe.updated",
        recipe_id=activated.id,
        revision=int(updated_account.revision),
        invalidations=invalidations,
        values={
            "version": version,
            "status": "active",
            "contentHash": activated.content_hash,
        },
    )
    rows = transaction.ai.recipes.list_versions(
        transaction.session,
        account_id,
    )
    return AIResourceMutation(
        data=recipe_summary_to_dto(
            account_id,
            rows,
            account_revision=int(updated_account.revision),
        ),
        resource_type="account_ai_recipe",
        resource_id=activated.id,
        revision=int(updated_account.revision),
        invalidations=invalidations,
    )


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
