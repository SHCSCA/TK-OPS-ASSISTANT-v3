from __future__ import annotations

from collections.abc import Mapping

from errors import DomainError, ErrorCode

from .json_codec import dump_json
from .validation import (
    require_adapter_type,
    require_model_id,
    require_object,
    require_positive_int,
    require_provider_url,
)


def normalize_provider_create(
    payload: Mapping[str, object],
) -> dict[str, object]:
    name = payload.get("name")
    if (
        not isinstance(name, str)
        or not name.strip()
        or len(name.strip()) > 128
    ):
        raise DomainError(
            ErrorCode.REQUEST_VALIDATION_FAILED,
            "Provider 名称格式无效",
            status_code=422,
        )
    region = payload.get("region")
    if region is not None and (
        not isinstance(region, str) or len(region.strip()) > 64
    ):
        raise DomainError(
            ErrorCode.REQUEST_VALIDATION_FAILED,
            "Provider 区域格式无效",
            status_code=422,
        )
    adapter_type = require_adapter_type(payload.get("adapterType"))
    extra_params = require_object(
        payload.get("extraParams", {}),
        field="extraParams",
    )
    if adapter_type == "openai_compatible":
        extra_params = _openai_extra_params(extra_params)
    return {
        "name": name.strip(),
        "adapterType": adapter_type,
        "baseUrl": require_provider_url(payload.get("baseUrl")),
        "region": region.strip() if isinstance(region, str) else None,
        "proxyRef": _optional_reference(payload.get("proxyRef")),
        "timeoutMs": require_positive_int(
            payload.get("timeoutMs"),
            field="timeoutMs",
            minimum=1_000,
            maximum=600_000,
        ),
        "maxConcurrency": require_positive_int(
            payload.get("maxConcurrency"),
            field="maxConcurrency",
            minimum=1,
            maximum=32,
        ),
        "enabled": bool(payload.get("enabled", False)),
        "extraParams": extra_params,
        "costPolicy": require_object(
            payload.get("costPolicy", {"mode": "unavailable"}),
            field="costPolicy",
        ),
    }


def normalize_provider_patch(
    payload: Mapping[str, object],
) -> dict[str, object]:
    changes: dict[str, object] = {}
    if "name" in payload:
        name = payload["name"]
        if not isinstance(name, str) or not name.strip():
            raise DomainError(
                ErrorCode.REQUEST_VALIDATION_FAILED,
                "Provider 名称格式无效",
                status_code=422,
            )
        changes["name"] = name.strip()
    if "baseUrl" in payload:
        changes["base_url"] = require_provider_url(payload["baseUrl"])
        changes["health_status"] = "unknown"
    if "region" in payload:
        region = payload["region"]
        changes["region"] = (
            region.strip() if isinstance(region, str) and region.strip() else None
        )
    if "proxyRef" in payload:
        changes["proxy_ref"] = _optional_reference(payload["proxyRef"])
    if "timeoutMs" in payload:
        changes["timeout_ms"] = require_positive_int(
            payload["timeoutMs"],
            field="timeoutMs",
            minimum=1_000,
            maximum=600_000,
        )
    if "maxConcurrency" in payload:
        changes["max_concurrency"] = require_positive_int(
            payload["maxConcurrency"],
            field="maxConcurrency",
            minimum=1,
            maximum=32,
        )
    if "enabled" in payload:
        if not isinstance(payload["enabled"], bool):
            raise DomainError(
                ErrorCode.REQUEST_VALIDATION_FAILED,
                "Provider 启用状态必须为布尔值",
                status_code=422,
            )
        changes["enabled"] = payload["enabled"]
    if "extraParams" in payload:
        changes["extra_params_json"] = dump_json(
            require_object(payload["extraParams"], field="extraParams")
        )
    if "costPolicy" in payload:
        changes["cost_policy_json"] = dump_json(
            require_object(payload["costPolicy"], field="costPolicy")
        )
    return changes


def normalize_model_create(
    payload: Mapping[str, object],
) -> dict[str, object]:
    provider_id = payload.get("providerProfileId")
    display_name = payload.get("displayName")
    if not isinstance(provider_id, str) or not provider_id:
        raise DomainError(
            ErrorCode.REQUEST_VALIDATION_FAILED,
            "Provider 标识格式无效",
            status_code=422,
        )
    if (
        not isinstance(display_name, str)
        or not display_name.strip()
        or len(display_name.strip()) > 128
    ):
        raise DomainError(
            ErrorCode.REQUEST_VALIDATION_FAILED,
            "模型显示名称格式无效",
            status_code=422,
        )
    enabled = payload.get("enabled")
    if not isinstance(enabled, bool):
        raise DomainError(
            ErrorCode.REQUEST_VALIDATION_FAILED,
            "模型启用状态必须为布尔值",
            status_code=422,
        )
    return {
        "providerProfileId": provider_id,
        "modelId": require_model_id(payload.get("modelId")),
        "displayName": display_name.strip(),
        "enabled": enabled,
        "baseLimits": require_object(
            payload.get("baseLimits", {}),
            field="baseLimits",
        ),
    }


def normalize_model_patch(
    payload: Mapping[str, object],
) -> dict[str, object]:
    changes: dict[str, object] = {}
    if "displayName" in payload:
        value = payload["displayName"]
        if not isinstance(value, str) or not value.strip():
            raise DomainError(
                ErrorCode.REQUEST_VALIDATION_FAILED,
                "模型显示名称格式无效",
                status_code=422,
            )
        changes["display_name"] = value.strip()
    if "enabled" in payload:
        if not isinstance(payload["enabled"], bool):
            raise DomainError(
                ErrorCode.REQUEST_VALIDATION_FAILED,
                "模型启用状态必须为布尔值",
                status_code=422,
            )
        changes["enabled"] = payload["enabled"]
    if "contextWindow" in payload:
        changes["context_window"] = require_positive_int(
            payload["contextWindow"],
            field="contextWindow",
            minimum=1,
            maximum=10_000_000,
        )
    if "baseLimits" in payload:
        changes["base_limits_json"] = dump_json(
            require_object(payload["baseLimits"], field="baseLimits")
        )
    return changes


def require_openai_protocol_params(raw_json: str) -> str:
    from .json_codec import load_object

    return dump_json(
        _openai_extra_params(
            load_object(raw_json, label="Provider 扩展参数")
        )
    )


def _openai_extra_params(value: Mapping[str, object]) -> dict[str, object]:
    normalized = dict(value)
    protocol = normalized.get("protocolVariant", "chat_completions")
    if protocol not in {"chat_completions", "responses"}:
        raise DomainError(
            ErrorCode.REQUEST_VALIDATION_FAILED,
            "OpenAI-compatible 协议类型无效",
            status_code=422,
        )
    normalized["protocolVariant"] = protocol
    return normalized


def _optional_reference(value: object) -> str | None:
    if value is None:
        return None
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value.strip()) > 512
    ):
        raise DomainError(
            ErrorCode.REQUEST_VALIDATION_FAILED,
            "Provider 安全引用格式无效",
            status_code=422,
        )
    return value.strip()


def normalize_route_payload(
    payload: Mapping[str, object],
) -> dict[str, object]:
    enabled = payload.get("enabled")
    if not isinstance(enabled, bool):
        raise DomainError(
            ErrorCode.CAPABILITY_ROUTE_INVALID,
            "能力路由启用状态必须为布尔值",
            status_code=422,
        )
    normalized: dict[str, object] = {"enabled": enabled}
    for key in (
        "primaryModelProfileId",
        "fallbackModelProfileId",
        "promptProfileId",
    ):
        value = payload.get(key)
        if value is not None and (
            not isinstance(value, str) or not value.strip()
        ):
            raise DomainError(
                ErrorCode.CAPABILITY_ROUTE_INVALID,
                "能力路由引用格式无效",
                status_code=422,
            )
        normalized[key] = value.strip() if isinstance(value, str) else None
    return normalized
