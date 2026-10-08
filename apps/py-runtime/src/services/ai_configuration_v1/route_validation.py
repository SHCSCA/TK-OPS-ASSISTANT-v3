from __future__ import annotations

from collections.abc import Mapping

from errors import DomainError, ErrorCode
from services.ai_execution_v1.config_readiness import model_dependency_issue

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
        dependency_issue = model_dependency_issue(
            transaction,
            model_id=model_id,
            capability_key=capability_key,
        )
        if dependency_issue is not None:
            issues.append(
                {
                    "code": dependency_issue,
                    "field": field,
                    "message": _dependency_message(dependency_issue),
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
            issue["code"]
            in {
                "AI_MODEL_CAPABILITY_UNVERIFIED",
                "AI_PROVIDER_REAL_VALIDATION_REQUIRED",
            }
            for issue in issues
        )
        else ErrorCode.CAPABILITY_ROUTE_INVALID
    )


def _dependency_message(code: str) -> str:
    messages = {
        "AI_MODEL_DISABLED": "所选模型不存在、未启用或没有活动修订",
        "AI_PROVIDER_DISABLED": "所选模型的 Provider 尚未启用",
        "AI_MODEL_CAPABILITY_UNVERIFIED": "所选模型尚未通过能力契约验证",
        "AI_PROVIDER_REAL_VALIDATION_REQUIRED": (
            "所选模型的当前修订尚未通过真实小调用验证"
        ),
    }
    return messages.get(code, "所选模型依赖尚未就绪")
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
