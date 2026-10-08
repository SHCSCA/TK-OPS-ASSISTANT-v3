from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from app.secret_store import SecretStore
from domain.models.account import Account
from domain.models.account_configuration import PositioningProfile
from domain.models.ai_configuration_v1 import (
    AccountAIRecipe,
    CapabilityRouteRevision,
)
from domain.models.ai_prompt import PromptProfile
from domain.models.knowledge import KnowledgeSnapshot
from errors import DomainError, ErrorCode
from services.accounts.guards import require_account, require_revision
from services.ai_configuration_v1.dependency_snapshots import (
    require_unchanged_dependency_snapshot,
)
from services.ai_configuration_v1.json_codec import (
    content_hash,
    load_object,
)
from services.ai_configuration_v1.recipe_dependencies import (
    resolve_recipe_dependencies,
)
from services.ai_configuration_v1.recipe_validation import recipe_payload_hash
from services.ai_configuration_v1.route_revision_support import (
    route_revision_content_hash,
)
from services.ai_execution_v1.dependency_graph import (
    resolve_route_dependencies,
)
from services.config import ConfigBusService

from .candidate_resolution import ResolvedCandidate, resolve_candidates
from .knowledge_context import FrozenKnowledgeContext, KnowledgeContextResolver
from .policies import (
    CostEstimate,
    ExecutionPolicy,
    estimate_cost,
    require_cost_within_budget,
    resolve_execution_policy,
)
from .prompt_renderer import RenderedPrompt, render_prompt
from .provider_registry import AIProviderPortRegistry
from .unit_of_work import AIExecutionTransaction, AIExecutionUnitOfWork


@dataclass(frozen=True, slots=True)
class ExecutionPlan:
    account: Account
    ai_config_revision: int
    recipe: AccountAIRecipe
    route: CapabilityRouteRevision
    prompt: PromptProfile
    positioning: PositioningProfile | None
    knowledge_snapshot: KnowledgeSnapshot
    knowledge: FrozenKnowledgeContext
    rendered_prompt: RenderedPrompt | None
    candidates: tuple[ResolvedCandidate, ...]
    policy: ExecutionPolicy
    input_hash: str | None
    dependency_graph: dict[str, object]
    dependency_hash: str
    snapshot_hash: str
    cost_minimum_micros: int | None
    cost_maximum_micros: int | None


class AIExecutionSnapshotBuilder:
    """只读解析全部不可变依赖，并在外部调用前完成失败封闭。"""

    def __init__(
        self,
        unit_of_work: AIExecutionUnitOfWork,
        *,
        config_bus: ConfigBusService,
        secret_store: SecretStore,
        port_registry: AIProviderPortRegistry,
        knowledge_context: KnowledgeContextResolver,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._config_bus = config_bus
        self._secret_store = secret_store
        self._ports = port_registry
        self._knowledge_context = knowledge_context

    def preflight(
        self,
        account_id: str,
        *,
        expected_revision: int,
        capability_key: str,
        recipe_version_id: str,
        knowledge_snapshot_id: str,
        input_summary: dict[str, object],
        requested_policy: dict[str, object],
    ) -> ExecutionPlan:
        estimated = input_summary.get("estimatedInputUnits", 1)
        if (
            isinstance(estimated, bool)
            or not isinstance(estimated, int)
            or estimated < 0
        ):
            raise DomainError(
                ErrorCode.AI_EXECUTION_INVALID,
                "输入摘要的 estimatedInputUnits 无效",
                status_code=422,
            )
        with self._unit_of_work.read() as transaction:
            return self._resolve(
                transaction,
                account_id=account_id,
                expected_revision=expected_revision,
                capability_key=capability_key,
                recipe_version_id=recipe_version_id,
                knowledge_snapshot_id=knowledge_snapshot_id,
                requested_policy=requested_policy,
                input_value=None,
                estimated_input_units=estimated,
            )

    def build(
        self,
        account_id: str,
        *,
        expected_revision: int,
        capability_key: str,
        recipe_version_id: str,
        knowledge_snapshot_id: str,
        input_value: dict[str, object],
        requested_policy: dict[str, object],
    ) -> ExecutionPlan:
        with self._unit_of_work.read() as transaction:
            return self._resolve(
                transaction,
                account_id=account_id,
                expected_revision=expected_revision,
                capability_key=capability_key,
                recipe_version_id=recipe_version_id,
                knowledge_snapshot_id=knowledge_snapshot_id,
                requested_policy=requested_policy,
                input_value=input_value,
                estimated_input_units=_estimate_units(input_value),
            )

    def _resolve(
        self,
        transaction: AIExecutionTransaction,
        *,
        account_id: str,
        expected_revision: int,
        capability_key: str,
        recipe_version_id: str,
        knowledge_snapshot_id: str,
        requested_policy: dict[str, object],
        input_value: dict[str, object] | None,
        estimated_input_units: int,
    ) -> ExecutionPlan:
        values = self._config_bus.get().values
        if values.get("ai.execution.enabled") is not True:
            raise DomainError(
                ErrorCode.AI_EXECUTION_DISABLED,
                "AI 执行能力尚未通过配置总线开启",
                status_code=503,
            )
        account = require_account(
            account_id,
            transaction.session,
            transaction.accounts,
        )
        require_revision(account, expected_revision)
        recipe = _require_recipe(
            transaction,
            account_id=account_id,
            recipe_version_id=recipe_version_id,
        )
        ai_revision = transaction.ai.revisions.get(transaction.session)
        if int(recipe.source_ai_config_revision) != ai_revision:
            raise DomainError(
                ErrorCode.AI_RECIPE_STALE,
                "账号 AI 配方引用的系统配置已变化",
                status_code=409,
            )
        require_unchanged_dependency_snapshot(
            transaction,
            snapshot_id=recipe.dependency_snapshot_id,
            current=resolve_recipe_dependencies(transaction, recipe),
        )
        route = _require_route(transaction, capability_key)
        route_resolution = resolve_route_dependencies(transaction, route)
        route_dependency = require_unchanged_dependency_snapshot(
            transaction,
            snapshot_id=route.dependency_snapshot_id,
            current=route_resolution,
        )
        _verify_route_hash(route)
        overrides = load_object(
            recipe.route_overrides_json,
            label="账号 AI 路由覆盖",
        )
        model_ids, prompt_id = _resolve_recipe_override(
            capability_key=capability_key,
            override=overrides.get(capability_key),
            route=route,
        )
        prompt = _require_prompt(transaction, prompt_id, capability_key)
        policy = resolve_execution_policy(
            route,
            requested_policy,
            default_timeout_seconds=_config_int(
                values,
                "ai.execution.defaultTimeoutSeconds",
            ),
            config_max_retries=_config_int(
                values,
                "ai.execution.maxRetries",
            ),
            default_max_cost_micros=_config_int(
                values,
                "ai.execution.defaultMaxCostMicros",
            ),
        )
        retry_policy = load_object(
            route.retry_policy_json,
            label="能力路由重试策略",
        )
        candidates = resolve_candidates(
            transaction,
            capability_key=capability_key,
            model_ids=model_ids,
            route_timeout_ms=policy.timeout_ms,
            route_max_retries=policy.max_retries,
            route_max_concurrency=int(route.max_concurrency),
            route_max_cost_micros=policy.max_cost_micros,
            retry_policy=retry_policy,
            global_max_concurrency=_config_int(
                values,
                "ai.execution.globalMaxConcurrency",
            ),
            allow_fallback=policy.allow_fallback,
            secret_store=self._secret_store,
            port_registry=self._ports,
        )
        knowledge_snapshot = _require_knowledge_snapshot(
            transaction,
            account_id=account_id,
            snapshot_id=knowledge_snapshot_id,
        )
        positioning = _snapshot_positioning(
            transaction,
            account_id=account_id,
            snapshot=knowledge_snapshot,
        )
        knowledge = self._knowledge_context.resolve(
            transaction,
            account_id=account_id,
            snapshot=knowledge_snapshot,
            max_input_units=policy.knowledge_max_input_units,
        )
        rendered = (
            render_prompt(
                prompt,
                input_value=input_value,
                knowledge=knowledge,
                positioning=positioning,
            )
            if input_value is not None
            else None
        )
        input_units = estimated_input_units + knowledge.input_units
        cost_minimum, cost_maximum = _cost_range(
            candidates,
            policy=policy,
            input_units=input_units,
        )
        dependency_graph = {
            "accountId": account_id,
            "accountRevision": int(account.revision),
            "aiConfigRevision": ai_revision,
            "recipeId": recipe.id,
            "recipeVersion": int(recipe.version),
            "recipeContentHash": recipe.content_hash,
            "recipeDependencySnapshotId": recipe.dependency_snapshot_id,
            "routeId": route.capability_route_id,
            "routeRevisionId": route.id,
            "routeContentHash": route.content_hash,
            "routeDependencySnapshotId": route_dependency.id,
            "promptProfileId": prompt.id,
            "promptVersion": int(prompt.version),
            "promptContentHash": prompt.content_hash,
            "knowledgeSnapshotId": knowledge_snapshot.id,
            "knowledgeContentHash": knowledge_snapshot.content_hash,
            "contextManifestHash": knowledge.manifest_hash,
            "policy": policy.to_dict(),
            "candidates": [item.safe_snapshot() for item in candidates],
        }
        dependency_hash = content_hash(dependency_graph)
        input_hash = _sha256_json(input_value) if input_value is not None else None
        snapshot_hash = content_hash(
            {
                "dependencyHash": dependency_hash,
                "inputHash": input_hash,
                "renderedPromptHash": (
                    rendered.rendered_hash if rendered is not None else None
                ),
            }
        )
        return ExecutionPlan(
            account=account,
            ai_config_revision=ai_revision,
            recipe=recipe,
            route=route,
            prompt=prompt,
            positioning=positioning,
            knowledge_snapshot=knowledge_snapshot,
            knowledge=knowledge,
            rendered_prompt=rendered,
            candidates=candidates,
            policy=policy,
            input_hash=input_hash,
            dependency_graph=dependency_graph,
            dependency_hash=dependency_hash,
            snapshot_hash=snapshot_hash,
            cost_minimum_micros=cost_minimum,
            cost_maximum_micros=cost_maximum,
        )


def _require_recipe(
    transaction: AIExecutionTransaction,
    *,
    account_id: str,
    recipe_version_id: str,
) -> AccountAIRecipe:
    row = transaction.ai.recipes.get_by_id(
        transaction.session,
        account_id,
        recipe_version_id,
    )
    if row is None or row.status != "active" or row.validation_status != "valid":
        raise DomainError(
            ErrorCode.AI_RECIPE_INVALID,
            "账号 AI 配方不存在、未激活或未通过校验",
            status_code=409,
        )
    payload = {
        "name": row.name,
        "routeOverrides": load_object(row.route_overrides_json, label="账号 AI 路由覆盖"),
        "visualStyle": load_object(row.visual_style_json, label="账号 AI 视觉风格"),
        "voiceProfileRef": row.voice_profile_ref,
        "compositionTemplateRef": row.composition_template_ref,
        "costPolicy": load_object(row.cost_policy_json, label="账号 AI 成本策略"),
        "fallbackPolicy": load_object(row.fallback_policy_json, label="账号 AI 回退策略"),
    }
    if recipe_payload_hash(payload) != row.content_hash:
        raise DomainError(
            ErrorCode.AI_RECIPE_STALE,
            "账号 AI 配方完整性校验失败",
            status_code=409,
            loggable=True,
        )
    return row


def _require_route(
    transaction: AIExecutionTransaction,
    capability_key: str,
) -> CapabilityRouteRevision:
    aggregate = transaction.ai.routes.get(transaction.session, capability_key)
    row = (
        transaction.ai.route_revisions.get_by_id(
            transaction.session,
            aggregate.active_revision_id,
        )
        if aggregate is not None and aggregate.active_revision_id is not None
        else None
    )
    if (
        aggregate is None
        or not aggregate.enabled
        or aggregate.validation_status != "valid"
        or row is None
        or row.status != "active"
        or not row.enabled
    ):
        raise DomainError(
            ErrorCode.AI_ROUTE_INCOMPLETE,
            "当前能力没有已激活且有效的路由修订",
            status_code=409,
        )
    return row


def _verify_route_hash(route: CapabilityRouteRevision) -> None:
    policy = load_object(route.candidate_policy_json, label="能力路由候选策略")
    digest = route_revision_content_hash(
        capability_key=route.capability_key,
        payload={
            "promptProfileId": route.prompt_profile_id,
            "candidates": policy.get("candidates", []),
            "timeoutMs": int(route.timeout_ms),
            "maxRetries": int(route.max_retries),
            "retryPolicy": load_object(route.retry_policy_json, label="能力路由重试策略"),
            "maxConcurrency": int(route.max_concurrency),
            "maxCostMicros": int(route.max_cost_micros),
            "currency": route.currency,
            "enabled": bool(route.enabled),
        },
    )
    if digest != route.content_hash:
        raise DomainError(
            ErrorCode.AI_DEPENDENCY_INVALID,
            "能力路由不可变修订完整性校验失败",
            status_code=409,
            loggable=True,
        )


def _resolve_recipe_override(
    *,
    capability_key: str,
    override: object,
    route: CapabilityRouteRevision,
) -> tuple[tuple[str, ...], str | None]:
    route_policy = load_object(route.candidate_policy_json, label="能力路由候选策略")
    raw_route = route_policy.get("candidates", [])
    route_models = tuple(
        str(item["modelProfileId"])
        for item in raw_route
        if isinstance(item, dict) and isinstance(item.get("modelProfileId"), str)
    )
    if override is None:
        return route_models, route.prompt_profile_id
    if not isinstance(override, dict):
        raise DomainError(
            ErrorCode.AI_RECIPE_ROUTE_CONFLICT,
            f"账号配方中的 {capability_key} 路由覆盖无效",
            status_code=409,
        )
    model_ids = tuple(
        value
        for value in (
            override.get("primaryModelProfileId"),
            override.get("fallbackModelProfileId"),
        )
        if isinstance(value, str) and value
    )
    if not model_ids:
        raise DomainError(
            ErrorCode.AI_RECIPE_ROUTE_CONFLICT,
            "账号路由覆盖缺少候选模型",
            status_code=409,
        )
    prompt = override.get("promptProfileId")
    return model_ids, str(prompt) if isinstance(prompt, str) else route.prompt_profile_id


def _require_prompt(
    transaction: AIExecutionTransaction,
    prompt_id: str | None,
    capability_key: str,
) -> PromptProfile:
    row = (
        transaction.ai.prompts.get_by_id(transaction.session, prompt_id)
        if prompt_id is not None
        else None
    )
    if row is None or row.status != "active" or row.capability_key != capability_key:
        raise DomainError(
            ErrorCode.AI_PROMPT_VERSION_MISSING,
            "当前能力缺少匹配的活动 Prompt 版本",
            status_code=409,
        )
    return row


def _require_knowledge_snapshot(
    transaction: AIExecutionTransaction,
    *,
    account_id: str,
    snapshot_id: str,
) -> KnowledgeSnapshot:
    row = transaction.knowledge.get_snapshot(
        account_id,
        transaction.session,
        snapshot_id=snapshot_id,
    )
    if row is None:
        raise DomainError(
            ErrorCode.AI_KNOWLEDGE_SNAPSHOT_NOT_READY,
            "当前账号的知识快照不存在",
            status_code=409,
        )
    return row


def _snapshot_positioning(
    transaction: AIExecutionTransaction,
    *,
    account_id: str,
    snapshot: KnowledgeSnapshot,
) -> PositioningProfile | None:
    if snapshot.positioning_profile_id is None:
        return None
    row = transaction.session.get(PositioningProfile, snapshot.positioning_profile_id)
    if row is None or row.account_id != account_id:
        raise DomainError(
            ErrorCode.AI_KNOWLEDGE_SNAPSHOT_NOT_READY,
            "知识快照引用的账号定位版本不可用",
            status_code=409,
        )
    return row


def _cost_range(
    candidates: tuple[ResolvedCandidate, ...],
    *,
    policy: ExecutionPolicy,
    input_units: int,
) -> tuple[int | None, int | None]:
    estimates: list[CostEstimate] = []
    for candidate in candidates:
        estimate = estimate_cost(
            candidate.cost_policy,
            input_units=input_units,
            output_units=policy.max_output_units,
        )
        estimates.append(estimate)
    if any(item.maximum_micros is None for item in estimates):
        if policy.max_cost_micros > 0:
            raise DomainError(
                ErrorCode.AI_COST_UNAVAILABLE,
                "候选 Provider 缺少硬预算所需的定价证据",
                status_code=409,
            )
        return None, None
    attempts = policy.max_retries + 1
    minimum = min(int(item.minimum_micros or 0) for item in estimates)
    maximum = sum(int(item.maximum_micros or 0) * attempts for item in estimates)
    require_cost_within_budget(
        CostEstimate(minimum, maximum, None),
        budget_micros=policy.max_cost_micros,
    )
    return minimum, maximum


def _config_int(values: dict[str, object], key: str) -> int:
    value = values.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise DomainError(
            ErrorCode.INTERNAL_ERROR,
            f"配置总线键 {key} 无效",
            status_code=500,
            loggable=True,
        )
    return value


def _estimate_units(value: dict[str, object]) -> int:
    return max(1, len(_canonical_json(value).encode("utf-8")) // 4)


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _sha256_json(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


__all__ = ["AIExecutionSnapshotBuilder", "ExecutionPlan"]
