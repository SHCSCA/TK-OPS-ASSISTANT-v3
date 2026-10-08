from __future__ import annotations

from collections.abc import Iterable

from domain.models import (
    AccountAIRecipe,
    CapabilityRoute,
    CompositionTemplateProfile,
    ModelCapability,
    ModelProfile,
    PromptProfile,
    ProviderProfile,
)

from .json_codec import load_list, load_object


def provider_to_dto(
    row: ProviderProfile,
    *,
    credential_configured: bool,
    masked_value: str | None = None,
) -> dict[str, object]:
    return {
        "id": row.id,
        "name": row.name,
        "adapterType": row.adapter_type,
        "baseUrl": row.base_url,
        "credentialSummary": {
            "configured": credential_configured,
            "maskedValue": masked_value,
        },
        "region": row.region,
        "proxyRef": row.proxy_ref,
        "timeoutMs": int(row.timeout_ms),
        "maxConcurrency": int(row.max_concurrency),
        "enabled": bool(row.enabled),
        "extraParams": load_object(
            row.extra_params_json,
            label="Provider 扩展参数",
        ),
        "costPolicy": load_object(
            row.cost_policy_json,
            label="Provider 成本策略",
        ),
        "activeRevisionId": row.active_revision_id,
        "healthStatus": row.health_status,
        "lastCheckedAt": row.last_checked_at,
        "lastErrorCode": row.last_error_code,
        "logId": row.last_error_log_id,
        "revision": int(row.revision),
    }


def capability_to_dto(row: ModelCapability) -> dict[str, object]:
    availability = "unavailable"
    if (
        row.declared_supported
        and row.adapter_supported
        and row.contract_verified
    ):
        availability = "available"
    elif row.declared_supported and row.adapter_supported:
        availability = "unverified"
    return {
        "capabilityKey": row.capability_key,
        "declaredSupported": bool(row.declared_supported),
        "adapterSupported": bool(row.adapter_supported),
        "contractVerified": bool(row.contract_verified),
        "availability": availability,
        "inputModalities": load_list(
            row.input_modalities_json,
            label="模型输入模态",
        ),
        "outputModalities": load_list(
            row.output_modalities_json,
            label="模型输出模态",
        ),
        "parameterSchema": load_object(
            row.parameter_schema_json,
            label="模型参数 Schema",
        ),
        "knownLimits": load_object(
            row.known_limits_json,
            label="模型限制",
        ),
        "verifiedAt": row.verified_at,
        "contractRevision": int(row.contract_revision),
    }


def model_to_dto(
    row: ModelProfile,
    capabilities: Iterable[ModelCapability],
) -> dict[str, object]:
    return {
        "id": row.id,
        "providerProfileId": row.provider_profile_id,
        "modelId": row.model_id,
        "displayName": row.display_name,
        "enabled": bool(row.enabled),
        "discoverySource": row.discovery_source,
        "contextWindow": row.context_window,
        "baseLimits": load_object(
            row.base_limits_json,
            label="模型基础限制",
        ),
        "capabilities": [
            capability_to_dto(capability)
            for capability in capabilities
        ],
        "activeRevisionId": row.active_revision_id,
        "revision": int(row.revision),
    }


def route_to_dto(row: CapabilityRoute) -> dict[str, object]:
    return {
        "id": row.id,
        "capabilityKey": row.capability_key,
        "primaryModelProfileId": row.primary_model_profile_id,
        "fallbackModelProfileId": row.fallback_model_profile_id,
        "promptProfileId": row.prompt_profile_id,
        "enabled": bool(row.enabled),
        "validationStatus": row.validation_status,
        "validationIssues": load_list(
            row.validation_issues_json,
            label="能力路由校验问题",
        ),
        "activeRevisionId": row.active_revision_id,
        "revision": int(row.revision),
    }


def prompt_summary_to_dto(
    rows: Iterable[PromptProfile],
    *,
    reference_count: int,
) -> dict[str, object]:
    versions = tuple(rows)
    if not versions:
        raise ValueError("Prompt Profile 汇总至少需要一个版本")
    latest = max(versions, key=lambda item: item.version)
    active = next(
        (item for item in versions if item.status == "active"),
        None,
    )
    return {
        "profileKey": latest.profile_key,
        "name": latest.name,
        "capabilityKey": latest.capability_key,
        "activeVersion": active.version if active is not None else None,
        "activeVersionId": active.id if active is not None else None,
        "versions": [
            {
                "version": int(item.version),
                "status": item.status,
                "contentHash": item.content_hash,
            }
            for item in sorted(versions, key=lambda item: item.version)
        ],
        "referenceCount": reference_count,
        "revision": max(int(item.revision) for item in versions),
    }


def prompt_version_to_dto(row: PromptProfile) -> dict[str, object]:
    return {
        "id": row.id,
        "profileKey": row.profile_key,
        "name": row.name,
        "capabilityKey": row.capability_key,
        "version": int(row.version),
        "status": row.status,
        "systemPrompt": row.system_prompt,
        "taskTemplate": row.task_template,
        "variablesSchema": load_object(
            row.variables_schema_json,
            label="Prompt 变量 Schema",
        ),
        "outputSchema": load_object(
            row.output_schema_json,
            label="Prompt 输出 Schema",
        ),
        "visualStylePrefix": row.visual_style_prefix or "",
        "safetyConstraints": load_object(
            row.safety_constraints_json,
            label="Prompt 安全约束",
        ),
        "contentHash": row.content_hash,
        "createdFromId": row.created_from_id,
        "createdAt": row.created_at,
        "activatedAt": row.activated_at,
        "revision": int(row.revision),
    }


def template_summary_to_dto(
    rows: Iterable[CompositionTemplateProfile],
    *,
    reference_count: int,
) -> dict[str, object]:
    versions = tuple(rows)
    if not versions:
        raise ValueError("合成模板汇总至少需要一个版本")
    latest = max(versions, key=lambda item: item.version)
    active = next(
        (item for item in versions if item.status == "active"),
        None,
    )
    return {
        "templateKey": latest.template_key,
        "name": latest.name,
        "templateType": latest.template_type,
        "activeVersion": active.version if active is not None else None,
        "activeVersionId": active.id if active is not None else None,
        "versions": [
            {
                "version": int(item.version),
                "status": item.status,
                "contentHash": item.content_hash,
            }
            for item in sorted(versions, key=lambda item: item.version)
        ],
        "compatibleCapabilities": load_object(
            latest.compatible_capabilities_json,
            label="合成模板兼容能力",
        ),
        "referenceCount": reference_count,
        "revision": max(int(item.revision) for item in versions),
    }


def template_version_to_dto(
    row: CompositionTemplateProfile,
) -> dict[str, object]:
    return {
        "id": row.id,
        "templateKey": row.template_key,
        "name": row.name,
        "templateType": row.template_type,
        "version": int(row.version),
        "status": row.status,
        "aspectRatios": load_list(
            row.aspect_ratios_json,
            label="合成模板画幅",
        ),
        "parameterSchema": load_object(
            row.parameter_schema_json,
            label="合成模板参数 Schema",
        ),
        "compositionSpecTemplate": load_object(
            row.composition_spec_template_json,
            label="合成模板 CompositionSpec",
        ),
        "compatibleCapabilities": load_object(
            row.compatible_capabilities_json,
            label="合成模板兼容能力",
        ),
        "previewAssetRef": row.preview_asset_ref,
        "contentHash": row.content_hash,
        "createdFromId": row.created_from_id,
        "createdAt": row.created_at,
        "activatedAt": row.activated_at,
        "revision": int(row.revision),
    }


def recipe_version_to_dto(row: AccountAIRecipe) -> dict[str, object]:
    validation_status = (
        "unvalidated"
        if row.validation_status == "incomplete"
        else row.validation_status
    )
    return {
        "id": row.id,
        "accountId": row.account_id,
        "version": int(row.version),
        "status": row.status,
        "name": row.name,
        "routeOverrides": load_object(
            row.route_overrides_json,
            label="账号 AI 路由覆盖",
        ),
        "visualStyle": load_object(
            row.visual_style_json,
            label="账号 AI 视觉风格",
        ),
        "voiceProfileRef": row.voice_profile_ref,
        "compositionTemplateRef": row.composition_template_ref,
        "costPolicy": load_object(
            row.cost_policy_json,
            label="账号 AI 成本策略",
        ),
        "fallbackPolicy": load_object(
            row.fallback_policy_json,
            label="账号 AI 回退策略",
        ),
        "sourceAiConfigRevision": int(row.source_ai_config_revision),
        "validationStatus": validation_status,
        "validationIssues": load_list(
            row.validation_issues_json,
            label="账号 AI 配方校验问题",
        ),
        "contentHash": row.content_hash,
        "createdAt": row.created_at,
        "activatedAt": row.activated_at,
        "revision": int(row.revision),
    }


def recipe_summary_to_dto(
    account_id: str,
    rows: Iterable[AccountAIRecipe],
    *,
    account_revision: int,
) -> dict[str, object]:
    versions = tuple(rows)
    active = next(
        (item for item in versions if item.status == "active"),
        None,
    )
    resolved_summary = None
    if active is not None:
        overrides = load_object(
            active.route_overrides_json,
            label="账号 AI 路由覆盖",
        )
        resolved_summary = {
            "overriddenCapabilities": sorted(overrides),
            "compositionTemplateRef": active.composition_template_ref,
            "sourceAiConfigRevision": int(
                active.source_ai_config_revision
            ),
        }
    return {
        "accountId": account_id,
        "activeVersion": active.version if active is not None else None,
        "activeVersionId": active.id if active is not None else None,
        "versions": [
            {
                "version": int(item.version),
                "status": item.status,
                "validationStatus": (
                    "unvalidated"
                    if item.validation_status == "incomplete"
                    else item.validation_status
                ),
            }
            for item in sorted(versions, key=lambda item: item.version)
        ],
        "resolvedSummary": resolved_summary,
        "revision": account_revision,
    }
