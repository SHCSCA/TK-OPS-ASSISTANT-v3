from __future__ import annotations

from collections.abc import Mapping

from sqlalchemy.orm import Session

from domain.models.ai_configuration_v1 import AccountAIRecipe
from errors import DomainError, ErrorCode
from repositories.ai_configuration_v1 import AIConfigurationV1Repository

from .json_codec import content_hash, load_object
from .route_validation import route_issues
from .unit_of_work import AIConfigurationTransaction
from .validation import require_capability_key, require_object


def normalize_recipe_payload(
    payload: Mapping[str, object],
) -> dict[str, object]:
    name = payload.get("name")
    if (
        not isinstance(name, str)
        or not name.strip()
        or len(name.strip()) > 128
    ):
        raise DomainError(
            ErrorCode.AI_RECIPE_INVALID,
            "账号 AI 配方名称格式无效",
            status_code=422,
        )
    route_overrides = require_object(
        payload.get("routeOverrides"),
        field="routeOverrides",
    )
    if len(route_overrides) > 64:
        raise DomainError(
            ErrorCode.AI_RECIPE_INVALID,
            "账号 AI 路由覆盖数量超过上限",
            status_code=422,
        )
    for key, value in route_overrides.items():
        require_capability_key(key)
        if not isinstance(value, Mapping):
            raise DomainError(
                ErrorCode.AI_RECIPE_INVALID,
                "账号 AI 路由覆盖格式无效",
                status_code=422,
            )
    voice_ref = payload.get("voiceProfileRef")
    template_ref = payload.get("compositionTemplateRef")
    for value, field in (
        (voice_ref, "voiceProfileRef"),
        (template_ref, "compositionTemplateRef"),
    ):
        if value is not None and (
            not isinstance(value, str)
            or not value.strip()
            or len(value) > 512
        ):
            raise DomainError(
                ErrorCode.AI_RECIPE_INVALID,
                f"账号 AI 配方字段 {field} 格式无效",
                status_code=422,
            )
    return {
        "name": name.strip(),
        "routeOverrides": route_overrides,
        "visualStyle": require_object(
            payload.get("visualStyle"),
            field="visualStyle",
        ),
        "voiceProfileRef": voice_ref,
        "compositionTemplateRef": template_ref,
        "costPolicy": require_object(
            payload.get("costPolicy"),
            field="costPolicy",
        ),
        "fallbackPolicy": require_object(
            payload.get("fallbackPolicy"),
            field="fallbackPolicy",
        ),
    }


def validate_recipe(
    transaction: AIConfigurationTransaction,
    row: AccountAIRecipe,
) -> dict[str, object]:
    overrides = load_object(
        row.route_overrides_json,
        label="账号 AI 路由覆盖",
    )
    required = {
        "script_generation",
        "storyboard_generation",
        "text_to_video",
        *overrides.keys(),
    }
    issues: list[dict[str, object]] = []
    resolved: dict[str, dict[str, object]] = {}
    for key in sorted(required):
        issue, summary = _resolve_route(
            transaction,
            capability_key=require_capability_key(key),
            override=overrides.get(key),
        )
        if issue is not None:
            issues.append(issue)
        if summary is not None:
            resolved[key] = summary
    if row.composition_template_ref is not None:
        template = transaction.ai.templates.get_by_id(
            transaction.session,
            row.composition_template_ref,
        )
        if template is None or template.status != "active":
            issues.append(
                {
                    "code": "COMPOSITION_TEMPLATE_INVALID",
                    "field": "compositionTemplateRef",
                    "message": "合成模板不存在或尚未激活",
                    "suggestedAction": "选择已激活的合成模板",
                }
            )
    current_ai_revision = transaction.ai.revisions.get(
        transaction.session
    )
    if int(row.source_ai_config_revision) != current_ai_revision:
        issues.append(
            {
                "code": "AI_CONFIG_REVISION_CHANGED",
                "field": None,
                "message": "系统 AI 配置已变化，请创建配方新版本",
                "suggestedAction": "基于当前配方创建并确认新版本",
            }
        )
    return {
        "accountId": row.account_id,
        "version": int(row.version),
        "validationStatus": "invalid" if issues else "valid",
        "validationIssues": issues,
        "resolvedRouteSummary": resolved,
        "sourceAiConfigRevision": int(row.source_ai_config_revision),
    }


def _resolve_route(
    transaction: AIConfigurationTransaction,
    *,
    capability_key: str,
    override: object,
) -> tuple[
    dict[str, object] | None,
    dict[str, object] | None,
]:
    repository = transaction.ai
    if override is None:
        route = repository.routes.get(
            transaction.session,
            capability_key,
        )
        if (
            route is None
            or not route.enabled
            or route.validation_status != "valid"
            or route.primary_model_profile_id is None
            or route_issues(
                transaction,
                capability_key=capability_key,
                payload={
                    "primaryModelProfileId": (
                        route.primary_model_profile_id
                        if route is not None
                        else None
                    ),
                    "fallbackModelProfileId": (
                        route.fallback_model_profile_id
                        if route is not None
                        else None
                    ),
                    "promptProfileId": (
                        route.prompt_profile_id
                        if route is not None
                        else None
                    ),
                    "enabled": (
                        bool(route.enabled) if route is not None else False
                    ),
                },
            )
        ):
            return (
                {
                    "code": "CAPABILITY_ROUTE_UNAVAILABLE",
                    "field": f"routeOverrides.{capability_key}",
                    "message": f"能力 {capability_key} 没有可用系统路由",
                    "suggestedAction": "先在系统 AI 设置中修复能力路由",
                },
                None,
            )
        return (
            None,
            {
                "modelProfileId": route.primary_model_profile_id,
                "promptProfileId": route.prompt_profile_id,
                "source": "system",
            },
        )
    if not isinstance(override, Mapping):
        return (
            {
                "code": "AI_RECIPE_INVALID",
                "field": f"routeOverrides.{capability_key}",
                "message": "账号路由覆盖格式无效",
                "suggestedAction": "重新选择账号覆盖模型",
            },
            None,
        )
    model_id = override.get("primaryModelProfileId")
    prompt_id = override.get("promptProfileId")
    if not isinstance(model_id, str):
        return (
            {
                "code": "AI_RECIPE_INVALID",
                "field": f"routeOverrides.{capability_key}",
                "message": "账号路由覆盖缺少主模型",
                "suggestedAction": "选择已验证的主模型",
            },
            None,
        )
    dependency_issue = _model_dependency_issue(
        repository,
        transaction.session,
        model_id=model_id,
        capability_key=capability_key,
    )
    if dependency_issue is not None:
        return (
            {
                "code": dependency_issue,
                "field": f"routeOverrides.{capability_key}",
                "message": (
                    "账号覆盖模型的 Provider 尚未健康就绪"
                    if dependency_issue == "PROVIDER_UNAVAILABLE"
                    else "账号覆盖模型尚未通过能力验证"
                ),
                "suggestedAction": (
                    "启用 Provider 并完成健康检查"
                    if dependency_issue == "PROVIDER_UNAVAILABLE"
                    else "运行模型能力检查"
                ),
            },
            None,
        )
    if prompt_id is not None:
        prompt = (
            repository.prompts.get_by_id(
                transaction.session,
                str(prompt_id),
            )
            if isinstance(prompt_id, str)
            else None
        )
        if (
            prompt is None
            or prompt.status != "active"
            or prompt.capability_key != capability_key
        ):
            return (
                {
                    "code": "PROMPT_PROFILE_INVALID",
                    "field": f"routeOverrides.{capability_key}",
                    "message": "账号覆盖 Prompt 不可用",
                    "suggestedAction": "选择匹配能力的活动 Prompt",
                },
                None,
            )
    return (
        None,
        {
            "modelProfileId": model_id,
            "promptProfileId": prompt_id,
            "source": "account_override",
        },
    )


def resolved_route_issue(
    repository: AIConfigurationV1Repository,
    session: Session,
    *,
    capability_key: str,
    override: object,
) -> dict[str, object] | None:
    if override is None:
        route = repository.routes.get(session, capability_key)
        if (
            route is not None
            and route.enabled
            and route.validation_status == "valid"
            and route.primary_model_profile_id is not None
            and _model_dependency_issue(
                repository,
                session,
                model_id=route.primary_model_profile_id,
                capability_key=capability_key,
            )
            is None
            and _prompt_dependency_valid(
                repository,
                session,
                prompt_id=route.prompt_profile_id,
                capability_key=capability_key,
            )
        ):
            return None
        return {"code": "CAPABILITY_ROUTE_UNAVAILABLE"}
    if not isinstance(override, Mapping):
        return {"code": "AI_RECIPE_INVALID"}
    model_id = override.get("primaryModelProfileId")
    if not isinstance(model_id, str):
        return {"code": "AI_RECIPE_INVALID"}
    dependency_issue = _model_dependency_issue(
        repository,
        session,
        model_id=model_id,
        capability_key=capability_key,
    )
    prompt_id = override.get("promptProfileId")
    if dependency_issue is None and _prompt_dependency_valid(
        repository,
        session,
        prompt_id=prompt_id,
        capability_key=capability_key,
    ):
        return None
    return {
        "code": dependency_issue or "PROMPT_PROFILE_INVALID"
    }


def _model_dependency_issue(
    repository: AIConfigurationV1Repository,
    session: Session,
    *,
    model_id: str,
    capability_key: str,
) -> str | None:
    model = repository.models.get(session, model_id)
    if model is None or not model.enabled:
        return "MODEL_CAPABILITY_UNVERIFIED"
    provider = repository.providers.get(
        session,
        model.provider_profile_id,
    )
    if (
        provider is None
        or not provider.enabled
        or provider.health_status != "ready"
    ):
        return "PROVIDER_UNAVAILABLE"
    capability = repository.capabilities.get(
        session,
        model_profile_id=model_id,
        capability_key=capability_key,
    )
    if (
        capability is None
        or not capability.declared_supported
        or not capability.adapter_supported
        or not capability.contract_verified
    ):
        return "MODEL_CAPABILITY_UNVERIFIED"
    return None


def _prompt_dependency_valid(
    repository: AIConfigurationV1Repository,
    session: Session,
    *,
    prompt_id: object,
    capability_key: str,
) -> bool:
    if prompt_id is None:
        return True
    if not isinstance(prompt_id, str):
        return False
    prompt = repository.prompts.get_by_id(session, prompt_id)
    return (
        prompt is not None
        and prompt.status == "active"
        and prompt.capability_key == capability_key
    )


def recipe_payload_hash(payload: Mapping[str, object]) -> str:
    return content_hash(
        {
            "name": payload["name"],
            "routeOverrides": payload["routeOverrides"],
            "visualStyle": payload["visualStyle"],
            "voiceProfileRef": payload.get("voiceProfileRef"),
            "compositionTemplateRef": payload.get(
                "compositionTemplateRef"
            ),
            "costPolicy": payload["costPolicy"],
            "fallbackPolicy": payload["fallbackPolicy"],
        }
    )
