from __future__ import annotations

from collections.abc import Mapping

from errors import DomainError, ErrorCode

from .unit_of_work import AIConfigurationTransaction


def route_issues(
    transaction: AIConfigurationTransaction,
    *,
    capability_key: str,
    payload: Mapping[str, object],
) -> list[dict[str, object]]:
    issues: list[dict[str, object]] = []
    primary_id = payload.get("primaryModelProfileId")
    fallback_id = payload.get("fallbackModelProfileId")
    prompt_id = payload.get("promptProfileId")
    if payload.get("enabled") and not isinstance(primary_id, str):
        issues.append(
            {
                "code": "PRIMARY_MODEL_REQUIRED",
                "field": "primaryModelProfileId",
                "message": "启用能力路由前必须选择主模型",
            }
        )
    for field, model_id in (
        ("primaryModelProfileId", primary_id),
        ("fallbackModelProfileId", fallback_id),
    ):
        if model_id is None:
            continue
        if not isinstance(model_id, str):
            issues.append(
                {
                    "code": "MODEL_NOT_FOUND",
                    "field": field,
                    "message": "模型标识格式无效",
                }
            )
            continue
        model = transaction.ai.models.get(
            transaction.session,
            model_id,
        )
        capability = transaction.ai.capabilities.get(
            transaction.session,
            model_profile_id=model_id,
            capability_key=capability_key,
        )
        if model is None or not model.enabled:
            issues.append(
                {
                    "code": "MODEL_NOT_FOUND",
                    "field": field,
                    "message": "所选模型不存在或未启用",
                }
            )
            continue
        if (
            (
                provider := transaction.ai.providers.get(
                    transaction.session,
                    model.provider_profile_id,
                )
            )
            is None
            or not provider.enabled
            or provider.health_status != "ready"
        ):
            issues.append(
                {
                    "code": "PROVIDER_UNAVAILABLE",
                    "field": field,
                    "message": "所选模型的 Provider 未启用或尚未健康就绪",
                }
            )
        if (
            capability is None
            or not capability.declared_supported
            or not capability.adapter_supported
            or not capability.contract_verified
        ):
            issues.append(
                {
                    "code": "MODEL_CAPABILITY_UNVERIFIED",
                    "field": field,
                    "message": "所选模型尚未通过该能力契约验证",
                }
            )
    if (
        isinstance(primary_id, str)
        and isinstance(fallback_id, str)
        and primary_id == fallback_id
    ):
        issues.append(
            {
                "code": "FALLBACK_EQUALS_PRIMARY",
                "field": "fallbackModelProfileId",
                "message": "回退模型不能与主模型相同",
            }
        )
    if prompt_id is not None:
        prompt = (
            transaction.ai.prompts.get_by_id(
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
            issues.append(
                {
                    "code": "PROMPT_PROFILE_INVALID",
                    "field": "promptProfileId",
                    "message": "Prompt 版本不存在、未激活或能力不匹配",
                }
            )
    return issues


def validation_status(
    payload: Mapping[str, object],
    issues: list[dict[str, object]],
) -> str:
    if issues:
        return "invalid" if payload.get("enabled") else "incomplete"
    return "valid" if payload.get("enabled") else "incomplete"


def route_invalid(issues: list[dict[str, object]]) -> DomainError:
    error_code = (
        ErrorCode.MODEL_CAPABILITY_UNVERIFIED
        if any(
            issue["code"] == "MODEL_CAPABILITY_UNVERIFIED"
            for issue in issues
        )
        else ErrorCode.CAPABILITY_ROUTE_INVALID
    )
    return DomainError(
        error_code,
        "能力路由校验失败",
        status_code=(
            409
            if error_code is ErrorCode.MODEL_CAPABILITY_UNVERIFIED
            else 422
        ),
        meta={"validationIssues": issues},
    )
