from __future__ import annotations

from dataclasses import dataclass

from domain.models.ai_configuration_v1 import CapabilityRouteRevision
from services.ai_configuration_v1.json_codec import content_hash, load_object
from services.ai_configuration_v1.unit_of_work import AIConfigurationTransaction

from .dependency_issue_support import (
    dependency_issue as _issue,
    repair_actions as _repair_actions,
    validate_route_policies as _validate_policies,
)

_TEXT_PROMPT_CAPABILITIES = frozenset(
    {
        "topic_generation",
        "script_generation",
        "script_rewrite",
        "storyboard_generation",
        "video_deconstruction",
        "subtitle_alignment",
        "asset_analysis",
    }
)


@dataclass(frozen=True, slots=True)
class DependencyResolution:
    graph: dict[str, object]
    issues: tuple[dict[str, object], ...]
    repair_actions: tuple[dict[str, object], ...]
    status: str
    content_hash: str


def resolve_route_dependencies(
    transaction: AIConfigurationTransaction,
    route_revision: CapabilityRouteRevision,
) -> DependencyResolution:
    candidate_policy = load_object(
        route_revision.candidate_policy_json,
        label="能力路由候选策略",
    )
    retry_policy = load_object(
        route_revision.retry_policy_json,
        label="能力路由重试策略",
    )
    raw_candidates = candidate_policy.get("candidates")
    issues: list[dict[str, object]] = []
    graph_candidates: list[dict[str, object]] = []
    if not route_revision.enabled:
        raw_candidates = []
    elif not isinstance(raw_candidates, list) or not raw_candidates:
        issues.append(
            _issue(
                "AI_ROUTE_INCOMPLETE",
                node_type="capability_route_revision",
                node_id=route_revision.id,
                path="candidates",
                message="能力路由至少需要一个候选模型",
            )
        )
    else:
        for ordinal, raw in enumerate(raw_candidates):
            _resolve_candidate(
                transaction,
                route_revision=route_revision,
                raw=raw,
                ordinal=ordinal,
                graph_candidates=graph_candidates,
                issues=issues,
            )
    prompt_node = (
        _resolve_prompt(
            transaction,
            route_revision=route_revision,
            issues=issues,
        )
        if route_revision.enabled
        else None
    )
    _validate_policies(route_revision, issues)
    graph = {
        "ownerType": "route",
        "ownerId": route_revision.capability_route_id,
        "ownerRevision": int(route_revision.revision),
        "capabilityKey": route_revision.capability_key,
        "enabled": bool(route_revision.enabled),
        "prompt": prompt_node,
        "candidates": graph_candidates,
        "policy": {
            "timeoutMs": int(route_revision.timeout_ms),
            "maxRetries": int(route_revision.max_retries),
            "retryPolicy": retry_policy,
            "maxConcurrency": int(route_revision.max_concurrency),
            "maxCostMicros": int(route_revision.max_cost_micros),
            "currency": route_revision.currency,
        },
    }
    actions = _repair_actions(issues)
    status = "invalid" if any(item["blocking"] for item in issues) else "valid"
    digest = content_hash(
        {
            "status": status,
            "graph": graph,
            "issues": issues,
            "repairActions": actions,
        }
    )
    return DependencyResolution(
        graph=graph,
        issues=tuple(issues),
        repair_actions=tuple(actions),
        status=status,
        content_hash=digest,
    )


def active_route_dependency_issue(
    transaction: AIConfigurationTransaction,
    capability_key: str,
) -> str | None:
    route = transaction.ai.routes.get(transaction.session, capability_key)
    if (
        route is None
        or not route.enabled
        or route.active_revision_id is None
    ):
        return "AI_ROUTE_INCOMPLETE"
    revision = transaction.ai.route_revisions.get_by_id(
        transaction.session,
        route.active_revision_id,
    )
    if revision is None or revision.status != "active":
        return "AI_ROUTE_INCOMPLETE"
    snapshot = (
        transaction.ai.dependency_snapshots.get(
            transaction.session,
            revision.dependency_snapshot_id,
        )
        if revision.dependency_snapshot_id is not None
        else None
    )
    current = resolve_route_dependencies(transaction, revision)
    if (
        snapshot is None
        or snapshot.status != "valid"
        or current.status != "valid"
        or snapshot.content_hash != current.content_hash
    ):
        return (
            str(current.issues[0]["code"])
            if current.issues
            else "AI_ROUTE_INCOMPLETE"
        )
    return None


def _resolve_candidate(
    transaction: AIConfigurationTransaction,
    *,
    route_revision: CapabilityRouteRevision,
    raw: object,
    ordinal: int,
    graph_candidates: list[dict[str, object]],
    issues: list[dict[str, object]],
) -> None:
    path = f"candidates[{ordinal}]"
    if not isinstance(raw, dict) or not isinstance(
        raw.get("modelProfileId"), str
    ):
        issues.append(
            _issue(
                "AI_ROUTE_INCOMPLETE",
                node_type="model_profile",
                node_id=None,
                path=path,
                message="候选模型配置无效",
            )
        )
        return
    model_id = str(raw["modelProfileId"])
    model = transaction.ai.models.get(transaction.session, model_id)
    if model is None or model.active_revision_id is None:
        issues.append(
            _issue(
                "AI_MODEL_DISABLED",
                node_type="model_profile",
                node_id=model_id,
                path=path,
                message="候选模型不存在或没有活动修订",
            )
        )
        return
    model_revision = transaction.ai.immutable_revisions.get_model(
        transaction.session,
        model.active_revision_id,
    )
    provider = transaction.ai.providers.get(
        transaction.session,
        model.provider_profile_id,
    )
    if not model.enabled or model_revision is None or not model_revision.enabled:
        issues.append(
            _issue(
                "AI_MODEL_DISABLED",
                node_type="model_profile",
                node_id=model_id,
                path=path,
                message="候选模型尚未启用",
            )
        )
        return
    if provider is None or provider.active_revision_id is None or not provider.enabled:
        issues.append(
            _issue(
                "AI_PROVIDER_DISABLED",
                node_type="provider_profile",
                node_id=None if provider is None else provider.id,
                path=path,
                message="候选模型的 Provider 尚未启用",
            )
        )
        return
    provider_revision = transaction.ai.immutable_revisions.get_provider(
        transaction.session,
        provider.active_revision_id,
    )
    if (
        provider_revision is None
        or model_revision.provider_profile_revision_id != provider_revision.id
    ):
        issues.append(
            _issue(
                "AI_PROVIDER_REAL_VALIDATION_REQUIRED",
                node_type="provider_profile_revision",
                node_id=provider.active_revision_id,
                path=path,
                message="模型尚未绑定当前 Provider 修订",
            )
        )
        return
    capability = transaction.ai.capabilities.get(
        transaction.session,
        model_profile_id=model.id,
        capability_key=route_revision.capability_key,
    )
    validation = transaction.ai.validation_runs.latest_verified_capability(
        transaction.session,
        provider_profile_id=provider.id,
        provider_revision=int(provider_revision.revision),
        model_profile_id=model.id,
        model_revision=int(model_revision.revision),
        capability_key=route_revision.capability_key,
    )
    if (
        capability is None
        or not capability.declared_supported
        or not capability.adapter_supported
        or not capability.contract_verified
        or validation is None
    ):
        issues.append(
            _issue(
                "AI_PROVIDER_REAL_VALIDATION_REQUIRED",
                node_type="model_profile_revision",
                node_id=model_revision.id,
                path=path,
                message="候选模型尚未通过当前修订的真实小调用",
            )
        )
        return
    graph_candidates.append(
        {
            "ordinal": ordinal,
            "providerProfileId": provider.id,
            "providerRevisionId": provider_revision.id,
            "providerRevision": int(provider_revision.revision),
            "modelProfileId": model.id,
            "modelRevisionId": model_revision.id,
            "modelRevision": int(model_revision.revision),
            "modelId": model_revision.model_id,
            "capabilityContractRevision": int(capability.contract_revision),
            "validationRunId": validation.id,
        }
    )


def _resolve_prompt(
    transaction: AIConfigurationTransaction,
    *,
    route_revision: CapabilityRouteRevision,
    issues: list[dict[str, object]],
) -> dict[str, object] | None:
    prompt_id = route_revision.prompt_profile_id
    required = route_revision.capability_key in _TEXT_PROMPT_CAPABILITIES
    prompt = (
        transaction.ai.prompts.get_by_id(transaction.session, prompt_id)
        if prompt_id is not None
        else None
    )
    if prompt is None and required:
        issues.append(
            _issue(
                "AI_PROMPT_VERSION_MISSING",
                node_type="prompt_profile",
                node_id=prompt_id,
                path="promptProfileId",
                message="文本能力路由缺少匹配的 Prompt 版本",
            )
        )
        return None
    if prompt is None:
        return None
    if prompt.status != "active" or prompt.capability_key != route_revision.capability_key:
        issues.append(
            _issue(
                "AI_PROMPT_SCHEMA_INVALID",
                node_type="prompt_profile",
                node_id=prompt.id,
                path="promptProfileId",
                message="Prompt 版本未激活或能力不匹配",
            )
        )
    return {
        "promptProfileId": prompt.id,
        "profileKey": prompt.profile_key,
        "version": int(prompt.version),
        "revision": int(prompt.revision),
        "contentHash": prompt.content_hash,
    }


__all__ = [
    "DependencyResolution",
    "active_route_dependency_issue",
    "resolve_route_dependencies",
]
