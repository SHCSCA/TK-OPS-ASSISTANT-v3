from __future__ import annotations

import ipaddress
import re
from collections.abc import Mapping, Sequence
from urllib.parse import urlparse

from errors import DomainError, ErrorCode, FieldError

from .constants import (
    CAPABILITY_KEYS,
    COMPOSITION_TEMPLATE_TYPES,
    PROVIDER_ADAPTER_TYPES,
)

_PROFILE_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9._-]{0,127}$")
_MODEL_ID_PATTERN = re.compile(r"^[^\s]{1,256}$")


def require_adapter_type(value: object) -> str:
    if isinstance(value, str) and value in PROVIDER_ADAPTER_TYPES:
        return value
    raise DomainError(
        ErrorCode.PROVIDER_ADAPTER_UNSUPPORTED,
        "Provider 适配器不受支持",
        status_code=422,
        field_errors=[
            FieldError(
                field="adapterType",
                code="unsupported_adapter",
                message="请选择已接入的 Provider 适配器",
            )
        ],
    )


def require_provider_url(value: object) -> str:
    if not isinstance(value, str):
        raise _provider_url_error()
    normalized = value.strip().rstrip("/")
    try:
        parsed = urlparse(normalized)
        port = parsed.port
    except ValueError as exc:
        raise _provider_url_error() from exc
    del port
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        raise _provider_url_error()
    if parsed.scheme == "http" and not _is_loopback(parsed.hostname):
        raise DomainError(
            ErrorCode.PROVIDER_BASE_URL_INVALID,
            "远程 Provider 必须使用 HTTPS",
            status_code=422,
            field_errors=[
                FieldError(
                    field="baseUrl",
                    code="https_required",
                    message="仅本机 Provider 可以使用 HTTP",
                )
            ],
        )
    return normalized


def require_positive_int(
    value: object,
    *,
    field: str,
    minimum: int,
    maximum: int,
) -> int:
    if (
        isinstance(value, int)
        and not isinstance(value, bool)
        and minimum <= value <= maximum
    ):
        return value
    raise DomainError(
        ErrorCode.REQUEST_VALIDATION_FAILED,
        "AI 配置参数超出允许范围",
        status_code=422,
        field_errors=[
            FieldError(
                field=field,
                code="out_of_range",
                message=f"必须为 {minimum} 至 {maximum} 的整数",
            )
        ],
    )


def require_capability_key(value: object) -> str:
    if isinstance(value, str) and value in CAPABILITY_KEYS:
        return value
    raise DomainError(
        ErrorCode.CAPABILITY_ROUTE_INVALID,
        "AI 能力标识不受支持",
        status_code=422,
        field_errors=[
            FieldError(
                field="capabilityKey",
                code="unsupported_capability",
                message="请选择当前版本支持的能力",
            )
        ],
    )


def require_capability_keys(
    values: object,
    *,
    allow_empty: bool = True,
) -> tuple[str, ...]:
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        raise DomainError(
            ErrorCode.REQUEST_VALIDATION_FAILED,
            "能力清单格式无效",
            status_code=422,
        )
    normalized = tuple(require_capability_key(value) for value in values)
    if (not allow_empty and not normalized) or len(set(normalized)) != len(
        normalized
    ):
        raise DomainError(
            ErrorCode.REQUEST_VALIDATION_FAILED,
            "能力清单不能为空或包含重复项",
            status_code=422,
        )
    return normalized


def require_profile_key(value: object, *, field: str) -> str:
    if (
        isinstance(value, str)
        and _PROFILE_KEY_PATTERN.fullmatch(value)
    ):
        return value
    raise DomainError(
        ErrorCode.REQUEST_VALIDATION_FAILED,
        "稳定配置标识格式无效",
        status_code=422,
        field_errors=[
            FieldError(
                field=field,
                code="invalid_profile_key",
                message="必须以小写字母开头，仅包含小写字母、数字和 ._-",
            )
        ],
    )


def require_model_id(value: object) -> str:
    if isinstance(value, str) and _MODEL_ID_PATTERN.fullmatch(value):
        return value
    raise DomainError(
        ErrorCode.REQUEST_VALIDATION_FAILED,
        "模型标识格式无效",
        status_code=422,
    )


def require_template_type(value: object) -> str:
    if isinstance(value, str) and value in COMPOSITION_TEMPLATE_TYPES:
        return value
    raise DomainError(
        ErrorCode.COMPOSITION_TEMPLATE_INVALID,
        "合成模板类型不受支持",
        status_code=422,
    )


def require_object(value: object, *, field: str) -> dict[str, object]:
    if isinstance(value, Mapping):
        return {str(key): item for key, item in value.items()}
    raise DomainError(
        ErrorCode.REQUEST_VALIDATION_FAILED,
        "AI 配置对象格式无效",
        status_code=422,
        field_errors=[
            FieldError(
                field=field,
                code="object_required",
                message="必须为对象",
            )
        ],
    )


def _provider_url_error() -> DomainError:
    return DomainError(
        ErrorCode.PROVIDER_BASE_URL_INVALID,
        "Provider 地址无效或不安全",
        status_code=422,
        field_errors=[
            FieldError(
                field="baseUrl",
                code="invalid_provider_url",
                message="请输入不含凭据和片段的 HTTP(S) 地址",
            )
        ],
    )


def _is_loopback(hostname: str) -> bool:
    normalized = hostname.casefold()
    if normalized == "localhost":
        return True
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False

