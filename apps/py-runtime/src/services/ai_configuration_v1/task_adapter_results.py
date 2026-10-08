from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from errors import DomainError, ErrorCode

from .json_codec import dump_json
from .provider_adapters import CapabilityProbe, DiscoveredModel

log = logging.getLogger(__name__)

_MAX_DISCOVERED_MODELS = 5_000
_SAFE_PROVIDER_ERROR_CODES = frozenset(
    {
        ErrorCode.PROVIDER_ADAPTER_UNSUPPORTED.value,
        ErrorCode.PROVIDER_CONNECTION_FAILED.value,
        ErrorCode.PROVIDER_SECRET_UNAVAILABLE.value,
        ErrorCode.REQUEST_VALIDATION_FAILED.value,
        ErrorCode.AI_PROVIDER_AUTH_FAILED.value,
        ErrorCode.AI_PROVIDER_RATE_LIMITED.value,
        ErrorCode.AI_PROVIDER_TIMEOUT.value,
        ErrorCode.AI_PROVIDER_RESULT_UNKNOWN.value,
        ErrorCode.AI_PROVIDER_RESPONSE_INVALID.value,
        ErrorCode.AI_CONTENT_REJECTED.value,
    }
)


@dataclass(frozen=True, slots=True)
class NormalizedCapability:
    capability_key: str
    declared_supported: bool
    adapter_supported: bool
    contract_verified: bool
    input_modalities_json: str
    output_modalities_json: str
    parameter_schema_json: str
    known_limits_json: str


def normalize_discovered_models(
    values: Sequence[DiscoveredModel],
) -> tuple[DiscoveredModel, ...]:
    if isinstance(values, (str, bytes)) or len(values) > _MAX_DISCOVERED_MODELS:
        raise _provider_response_invalid()
    normalized: list[DiscoveredModel] = []
    seen: set[str] = set()
    for item in values:
        if not isinstance(item, DiscoveredModel):
            raise _provider_response_invalid()
        model_id = item.model_id.strip()
        display_name = item.display_name.strip()
        context_window = item.context_window
        if (
            not model_id
            or len(model_id) > 256
            or not display_name
            or len(display_name) > 128
            or model_id in seen
            or isinstance(context_window, bool)
            or (
                context_window is not None
                and (
                    not isinstance(context_window, int)
                    or context_window <= 0
                )
            )
        ):
            raise _provider_response_invalid()
        seen.add(model_id)
        normalized.append(
            DiscoveredModel(
                model_id=model_id,
                display_name=display_name,
                context_window=context_window,
            )
        )
    return tuple(normalized)


def normalize_capability_probes(
    values: Sequence[CapabilityProbe],
    *,
    requested_keys: Sequence[str],
) -> tuple[NormalizedCapability, ...]:
    if isinstance(values, (str, bytes)) or len(values) > len(requested_keys):
        raise _provider_response_invalid()
    requested = tuple(requested_keys)
    requested_set = set(requested)
    by_key: dict[str, NormalizedCapability] = {}
    for item in values:
        if (
            not isinstance(item, CapabilityProbe)
            or item.capability_key not in requested_set
            or item.capability_key in by_key
        ):
            raise _provider_response_invalid()
        declared = _require_bool(item.declared_supported)
        adapter_supported = _require_bool(item.adapter_supported)
        probe_verified = _require_bool(item.contract_verified)
        by_key[item.capability_key] = NormalizedCapability(
            capability_key=item.capability_key,
            declared_supported=declared,
            adapter_supported=adapter_supported,
            contract_verified=(
                declared and adapter_supported and probe_verified
            ),
            input_modalities_json=dump_json(
                _normalize_modalities(item.input_modalities)
            ),
            output_modalities_json=dump_json(
                _normalize_modalities(item.output_modalities)
            ),
            parameter_schema_json=dump_json(
                _normalize_mapping(item.parameter_schema)
            ),
            known_limits_json=dump_json(
                _normalize_mapping(item.known_limits)
            ),
        )
    unavailable = NormalizedCapability(
        capability_key="",
        declared_supported=False,
        adapter_supported=False,
        contract_verified=False,
        input_modalities_json=dump_json([]),
        output_modalities_json=dump_json([]),
        parameter_schema_json=dump_json({}),
        known_limits_json=dump_json({}),
    )
    return tuple(
        by_key.get(key, _unavailable_capability(key, unavailable))
        for key in requested
    )


def safe_provider_error(error: Exception) -> DomainError:
    if isinstance(error, DomainError):
        error_code = error.error_code
    else:
        error_code = ErrorCode.PROVIDER_CONNECTION_FAILED.value
    if error_code not in _SAFE_PROVIDER_ERROR_CODES:
        error_code = ErrorCode.PROVIDER_CONNECTION_FAILED.value
    if error_code == ErrorCode.PROVIDER_SECRET_UNAVAILABLE.value:
        return DomainError(
            error_code,
            "Provider 凭据暂不可用，请重新设置后重试",
            status_code=503,
            loggable=True,
        )
    if error_code == ErrorCode.PROVIDER_ADAPTER_UNSUPPORTED.value:
        return DomainError(
            error_code,
            "Provider 适配器尚未接入",
            status_code=422,
            loggable=True,
        )
    details = {
        ErrorCode.REQUEST_VALIDATION_FAILED.value: (
            "Provider 配置或调用参数无效",
            422,
        ),
        ErrorCode.AI_PROVIDER_AUTH_FAILED.value: (
            "Provider 鉴权失败，请轮换凭据后重试",
            502,
        ),
        ErrorCode.AI_PROVIDER_RATE_LIMITED.value: (
            "Provider 暂时限流，请稍后重试",
            429,
        ),
        ErrorCode.AI_PROVIDER_TIMEOUT.value: (
            "Provider 调用超时",
            504,
        ),
        ErrorCode.AI_PROVIDER_RESULT_UNKNOWN.value: (
            "Provider 调用超时，远端结果可能未知",
            502,
        ),
        ErrorCode.AI_PROVIDER_RESPONSE_INVALID.value: (
            "Provider 返回了无法识别的响应",
            502,
        ),
        ErrorCode.AI_CONTENT_REJECTED.value: (
            "Provider 拒绝了本次内容",
            422,
        ),
    }
    detail = details.get(error_code)
    if detail is not None:
        return DomainError(
            error_code,
            detail[0],
            status_code=detail[1],
            loggable=True,
        )
    return DomainError(
        error_code,
        "Provider 连接检查失败，请检查配置和网络",
        status_code=502,
        loggable=True,
    )


def log_safe_external_failure(
    *,
    task_id: str,
    provider_id: str,
    model_id: str | None,
    error_code: str,
    log_id: str,
) -> None:
    try:
        raise RuntimeError("Provider 外部调用失败，原始响应已脱敏")
    except RuntimeError:
        log.exception(
            "AI 配置持久任务外部调用失败",
            extra={
                "task_id": task_id,
                "provider_profile_id": provider_id,
                "model_profile_id": model_id,
                "error_code": error_code,
                "log_id": log_id,
            },
        )


def _unavailable_capability(
    capability_key: str,
    template: NormalizedCapability,
) -> NormalizedCapability:
    return NormalizedCapability(
        capability_key=capability_key,
        declared_supported=template.declared_supported,
        adapter_supported=template.adapter_supported,
        contract_verified=template.contract_verified,
        input_modalities_json=template.input_modalities_json,
        output_modalities_json=template.output_modalities_json,
        parameter_schema_json=template.parameter_schema_json,
        known_limits_json=template.known_limits_json,
    )


def _normalize_modalities(values: Sequence[str]) -> list[str]:
    if isinstance(values, (str, bytes)):
        raise _provider_response_invalid()
    normalized = list(values)
    if (
        len(normalized) > 32
        or any(
            not isinstance(item, str)
            or not item.strip()
            or len(item) > 64
            for item in normalized
        )
        or len(set(normalized)) != len(normalized)
    ):
        raise _provider_response_invalid()
    return normalized


def _normalize_mapping(value: Mapping[str, object]) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise _provider_response_invalid()
    return dict(value)


def _require_bool(value: object) -> bool:
    if not isinstance(value, bool):
        raise _provider_response_invalid()
    return value


def _provider_response_invalid() -> DomainError:
    return DomainError(
        ErrorCode.PROVIDER_CONNECTION_FAILED,
        "Provider 返回了无法识别的结果",
        status_code=502,
        loggable=True,
    )
