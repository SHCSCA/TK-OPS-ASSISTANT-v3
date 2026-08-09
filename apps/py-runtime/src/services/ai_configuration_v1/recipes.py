from __future__ import annotations

from collections.abc import Mapping, Sequence
from uuid import uuid4

from sqlalchemy.orm import Session

from common.pagination import CursorPosition
from domain.models.ai_configuration_v1 import AccountAIRecipe
from repositories.ai_configuration_v1 import AIConfigurationV1Repository
from services.accounts.guards import require_account
from services.accounts.idempotency import MutationCommand
from services.accounts.json_codec import dump_json as dump_account_json
from services.accounts.types import (
    ReadinessItem,
    ReadinessStatus,
    RecipeCopyDecision,
)

from .dto import recipe_summary_to_dto, recipe_version_to_dto
from .json_codec import load_object
from .mutation import AIConfigurationMutationExecutor, AIResourceMutation
from .unit_of_work import AIConfigurationUnitOfWork
from .recipe_operations import (
    activate_recipe_version,
    create_recipe_version,
    utc_now,
    validate_recipe_version,
)
from .recipe_queries import (
    load_recipe_summary_replay,
    load_recipe_validation_replay,
    load_recipe_version_replay,
    missing_recipe,
    open_recipe_action,
    recipe_cursor_start,
)
from .recipe_validation import (
    normalize_recipe_payload,
    recipe_payload_hash,
    resolved_route_issue,
)
from .validation import require_capability_key


class AccountAIRecipeService:
    def __init__(
        self,
        unit_of_work: AIConfigurationUnitOfWork,
        mutations: AIConfigurationMutationExecutor,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._mutations = mutations

    def get_account_ai_recipe(
        self,
        account_id: str,
    ) -> dict[str, object]:
        with self._unit_of_work.read() as transaction:
            account = require_account(
                account_id,
                transaction.session,
                transaction.accounts,
            )
            rows = transaction.ai.recipes.list_versions(
                transaction.session,
                account_id,
            )
            return recipe_summary_to_dto(
                account_id,
                rows,
                account_revision=int(account.revision),
            )

    def list_account_ai_recipe_versions(
        self,
        account_id: str,
        *,
        cursor: CursorPosition | None = None,
        limit: int = 50,
    ) -> tuple[dict[str, object], CursorPosition | None]:
        with self._unit_of_work.read() as transaction:
            require_account(
                account_id,
                transaction.session,
                transaction.accounts,
            )
            rows = transaction.ai.recipes.list_versions(
                transaction.session,
                account_id,
            )
            start = recipe_cursor_start(rows, cursor)
            page = rows[start : start + limit]
            next_position = (
                CursorPosition(
                    sort_value=str(page[-1].version),
                    resource_id=page[-1].id,
                )
                if start + limit < len(rows) and page
                else None
            )
            return (
                {
                    "items": [
                        recipe_version_to_dto(row)
                        for row in page
                    ],
                    "totalKnown": len(rows),
                },
                next_position,
            )

    def create_account_ai_recipe_version(
        self,
        account_id: str,
        payload: Mapping[str, object],
        *,
        expected_revision: int,
        idempotency_key: str,
        request_id: str,
        operation_id: str,
    ) -> AIResourceMutation:
        del request_id, operation_id
        normalized = normalize_recipe_payload(payload)
        command = MutationCommand(
            account_id=account_id,
            operation_name="ai.account_recipe.create",
            idempotency_key=idempotency_key,
            request_payload={
                "contentHash": recipe_payload_hash(normalized),
                "expectedRevision": expected_revision,
            },
        )
        result = self._mutations.execute(
            command,
            work=lambda transaction: create_recipe_version(
                transaction,
                account_id=account_id,
                payload=normalized,
                expected_revision=expected_revision,
            ),
            replay_loader=lambda transaction, resource_type, resource_id: (
                load_recipe_version_replay(
                    transaction,
                    resource_type,
                    resource_id,
                    account_id=account_id,
                )
            ),
        )
        return result

    def validate_account_ai_recipe_version(
        self,
        account_id: str,
        version: int,
        *,
        idempotency_key: str,
        request_id: str,
        operation_id: str,
    ) -> AIResourceMutation:
        del request_id, operation_id
        command = MutationCommand(
            account_id=account_id,
            operation_name="ai.account_recipe.validate",
            idempotency_key=idempotency_key,
            request_payload={
                "accountId": account_id,
                "version": version,
            },
        )
        result = self._mutations.execute(
            command,
            work=lambda transaction: validate_recipe_version(
                transaction,
                account_id=account_id,
                version=version,
            ),
            replay_loader=lambda transaction, resource_type, resource_id: (
                load_recipe_validation_replay(
                    transaction,
                    resource_type,
                    resource_id,
                    account_id=account_id,
                )
            ),
        )
        return result

    def activate_account_ai_recipe_version(
        self,
        account_id: str,
        version: int,
        *,
        expected_revision: int,
        idempotency_key: str,
        request_id: str,
        operation_id: str,
    ) -> AIResourceMutation:
        del request_id, operation_id
        command = MutationCommand(
            account_id=account_id,
            operation_name="ai.account_recipe.activate",
            idempotency_key=idempotency_key,
            request_payload={
                "accountId": account_id,
                "version": version,
                "expectedRevision": expected_revision,
            },
        )
        result = self._mutations.execute(
            command,
            work=lambda transaction: activate_recipe_version(
                transaction,
                account_id=account_id,
                version=version,
                expected_revision=expected_revision,
            ),
            replay_loader=lambda transaction, resource_type, resource_id: (
                load_recipe_summary_replay(
                    transaction,
                    resource_type,
                    resource_id,
                    account_id=account_id,
                )
            ),
        )
        return result

class AccountAIReadinessAdapter:
    def __init__(self, repository: AIConfigurationV1Repository) -> None:
        self._repository = repository

    def evaluate(
        self,
        session: Session,
        *,
        account_id: str,
        required_capability_keys: Sequence[str],
    ) -> ReadinessItem:
        active = self._repository.recipes.get_active(session, account_id)
        if active is None:
            return missing_recipe()
        current_revision = self._repository.revisions.get(session)
        if (
            active.validation_status != "valid"
            or int(active.source_ai_config_revision) != current_revision
        ):
            return ReadinessItem(
                status=ReadinessStatus.ATTENTION,
                label="AI 配方需要重新校验",
                error_code="AI_RECIPE_INVALID",
                suggested_action=open_recipe_action("重新校验 AI 配方"),
            )
        overrides = load_object(
            active.route_overrides_json,
            label="账号 AI 路由覆盖",
        )
        for key in required_capability_keys:
            issue = resolved_route_issue(
                self._repository,
                session,
                capability_key=require_capability_key(key),
                override=overrides.get(key),
            )
            if issue is not None:
                return ReadinessItem(
                    status=ReadinessStatus.ATTENTION,
                    label="AI 必需能力不可用",
                    error_code=str(issue["code"]),
                    suggested_action=open_recipe_action(
                        "修复 AI 能力路由"
                    ),
                )
        return ReadinessItem(
            status=ReadinessStatus.READY,
            label="AI 配方可用",
        )


class AIRecipeCopyAdapter:
    def __init__(self, repository: AIConfigurationV1Repository) -> None:
        self._repository = repository

    def copy_active_recipe(
        self,
        session: Session,
        *,
        source_account_id: str,
        target_account_id: str,
    ) -> RecipeCopyDecision:
        source = self._repository.recipes.get_active(
            session,
            source_account_id,
        )
        if source is None:
            return RecipeCopyDecision(
                copied=False,
                reason_code="AI_RECIPE_NOT_CONFIGURED",
            )
        payload = {
            "name": source.name,
            "routeOverrides": load_object(
                source.route_overrides_json,
                label="账号 AI 路由覆盖",
            ),
            "visualStyle": load_object(
                source.visual_style_json,
                label="账号 AI 视觉风格",
            ),
            "voiceProfileRef": source.voice_profile_ref,
            "compositionTemplateRef": source.composition_template_ref,
            "costPolicy": load_object(
                source.cost_policy_json,
                label="账号 AI 成本策略",
            ),
            "fallbackPolicy": load_object(
                source.fallback_policy_json,
                label="账号 AI 回退策略",
            ),
        }
        now = utc_now()
        self._repository.recipes.add(
            session,
            target_account_id,
            AccountAIRecipe(
                id=f"recipe_{uuid4().hex}",
                account_id=target_account_id,
                name=source.name,
                version=self._repository.recipes.next_version(
                    session,
                    target_account_id,
                ),
                status="draft",
                route_overrides_json=source.route_overrides_json,
                visual_style_json=source.visual_style_json,
                voice_profile_ref=source.voice_profile_ref,
                composition_template_ref=source.composition_template_ref,
                cost_policy_json=source.cost_policy_json,
                fallback_policy_json=source.fallback_policy_json,
                source_ai_config_revision=self._repository.revisions.get(
                    session
                ),
                validation_status="incomplete",
                validation_issues_json=dump_account_json([]),
                content_hash=recipe_payload_hash(payload),
                revision=1,
                created_from_id=None,
                created_at=now,
                activated_at=None,
            ),
        )
        return RecipeCopyDecision(copied=True)
