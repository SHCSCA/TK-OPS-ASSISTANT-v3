from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from uuid import uuid4

from domain.models.ai_configuration_v1 import CompositionTemplateProfile
from errors import DomainError, ErrorCode
from services.ai_execution_v1.dependency_graph import (
    active_route_dependency_issue,
)

from .json_codec import content_hash, dump_json, load_object
from .unit_of_work import AIConfigurationTransaction
from .validation import (
    require_capability_keys,
    require_object,
    require_profile_key,
    require_template_type,
)

_ASPECT_RATIO_PATTERN = re.compile(r"^[1-9]\d{0,3}:[1-9]\d{0,3}$")
_ABSOLUTE_PATH_PATTERN = re.compile(
    r"^(?:[A-Za-z]:[\\/]|\\\\[^\\/]+[\\/]|/)"
)
_FORBIDDEN_TEMPLATE_KEYS = frozenset(
    {
        "command",
        "executable",
        "localPath",
        "python",
        "script",
        "shell",
    }
)

def _normalize_template_profile(
    payload: Mapping[str, object],
) -> dict[str, object]:
    return {
        **_normalize_template_body(payload),
        "templateKey": require_profile_key(
            payload.get("templateKey"),
            field="templateKey",
        ),
        "templateType": require_template_type(
            payload.get("templateType")
        ),
    }


def _normalize_template_version(
    payload: Mapping[str, object],
) -> dict[str, object]:
    source_version = payload.get("createdFromVersion")
    if (
        not isinstance(source_version, int)
        or isinstance(source_version, bool)
        or source_version < 1
    ):
        raise DomainError(
            ErrorCode.COMPOSITION_TEMPLATE_INVALID,
            "合成模板来源版本无效",
            status_code=422,
        )
    return {
        **_normalize_template_body(payload),
        "createdFromVersion": source_version,
    }


def _normalize_template_body(
    payload: Mapping[str, object],
) -> dict[str, object]:
    name = payload.get("name")
    if (
        not isinstance(name, str)
        or not name.strip()
        or len(name.strip()) > 128
    ):
        raise DomainError(
            ErrorCode.COMPOSITION_TEMPLATE_INVALID,
            "合成模板名称格式无效",
            status_code=422,
        )
    raw_ratios = payload.get("aspectRatios")
    if (
        not isinstance(raw_ratios, Sequence)
        or isinstance(raw_ratios, (str, bytes))
    ):
        raise DomainError(
            ErrorCode.COMPOSITION_TEMPLATE_INVALID,
            "合成模板画幅清单格式无效",
            status_code=422,
        )
    ratios = tuple(str(item) for item in raw_ratios)
    if (
        not ratios
        or len(ratios) > 16
        or len(set(ratios)) != len(ratios)
        or any(not _ASPECT_RATIO_PATTERN.fullmatch(item) for item in ratios)
    ):
        raise DomainError(
            ErrorCode.COMPOSITION_TEMPLATE_INVALID,
            "合成模板画幅清单无效",
            status_code=422,
        )
    parameter_schema = require_object(
        payload.get("parameterSchema"),
        field="parameterSchema",
    )
    composition_spec = require_object(
        payload.get("compositionSpecTemplate"),
        field="compositionSpecTemplate",
    )
    _validate_safe_template_value(composition_spec, path="$")
    compatible = require_object(
        payload.get("compatibleCapabilities"),
        field="compatibleCapabilities",
    )
    required = compatible.get("required", [])
    if required is not None:
        require_capability_keys(required)
    preview = payload.get("previewAssetRef")
    if preview is not None and (
        not isinstance(preview, str)
        or not preview.strip()
        or len(preview) > 512
    ):
        raise DomainError(
            ErrorCode.COMPOSITION_TEMPLATE_INVALID,
            "合成模板预览资产引用无效",
            status_code=422,
        )
    return {
        "name": name.strip(),
        "aspectRatios": list(ratios),
        "parameterSchema": parameter_schema,
        "compositionSpecTemplate": composition_spec,
        "compatibleCapabilities": compatible,
        "previewAssetRef": preview,
    }


def _build_template_row(
    payload: Mapping[str, object],
    *,
    template_key: str,
    template_type: str,
    version: int,
    created_from_id: str | None,
    revision: int,
) -> CompositionTemplateProfile:
    now = _utc_now()
    return CompositionTemplateProfile(
        id=f"tpl_{uuid4().hex}",
        template_key=template_key,
        name=str(payload["name"]),
        version=version,
        status="draft",
        template_type=template_type,
        aspect_ratios_json=dump_json(payload["aspectRatios"]),
        parameter_schema_json=dump_json(payload["parameterSchema"]),
        composition_spec_template_json=dump_json(
            payload["compositionSpecTemplate"]
        ),
        compatible_capabilities_json=dump_json(
            payload["compatibleCapabilities"]
        ),
        preview_asset_ref=(
            str(payload["previewAssetRef"])
            if payload.get("previewAssetRef") is not None
            else None
        ),
        dependency_snapshot_id=None,
        content_hash=_template_payload_hash(payload),
        revision=revision,
        created_from_id=created_from_id,
        created_at=now,
        activated_at=None,
    )


def _template_payload_hash(payload: Mapping[str, object]) -> str:
    return content_hash(
        {
            "name": payload["name"],
            "aspectRatios": payload["aspectRatios"],
            "parameterSchema": payload["parameterSchema"],
            "compositionSpecTemplate": payload[
                "compositionSpecTemplate"
            ],
            "compatibleCapabilities": payload[
                "compatibleCapabilities"
            ],
            "previewAssetRef": payload.get("previewAssetRef"),
        }
    )


def _template_validation(
    transaction: AIConfigurationTransaction,
    row: CompositionTemplateProfile,
) -> dict[str, object]:
    compatible = load_object(
        row.compatible_capabilities_json,
        label="合成模板兼容能力",
    )
    raw_required = compatible.get("required", [])
    required = (
        require_capability_keys(raw_required)
        if isinstance(raw_required, Sequence)
        else ()
    )
    issues: list[dict[str, object]] = []
    verified: list[str] = []
    for key in required:
        issue_code = active_route_dependency_issue(transaction, key)
        if issue_code is not None:
            issues.append(
                {
                    "code": issue_code,
                    "field": "compatibleCapabilities.required",
                    "message": f"能力 {key} 尚无可用系统路由",
                }
            )
        else:
            verified.append(key)
    return {
        "templateKey": row.template_key,
        "version": int(row.version),
        "validationStatus": "invalid" if issues else "valid",
        "validationIssues": issues,
        "verifiedCapabilities": verified,
        "checkedAt": _utc_now(),
    }


def _validate_safe_template_value(value: object, *, path: str) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise _unsafe_template(path)
            if key in _FORBIDDEN_TEMPLATE_KEYS:
                raise _unsafe_template(f"{path}.{key}")
            _validate_safe_template_value(item, path=f"{path}.{key}")
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for index, item in enumerate(value):
            _validate_safe_template_value(item, path=f"{path}[{index}]")
        return
    if isinstance(value, str) and _ABSOLUTE_PATH_PATTERN.match(value):
        raise _unsafe_template(path)
    if value is None or isinstance(value, (str, bool, int, float)):
        return
    raise _unsafe_template(path)


def _unsafe_template(path: str) -> DomainError:
    return DomainError(
        ErrorCode.COMPOSITION_TEMPLATE_INVALID,
        "合成模板包含不受控执行内容或本地路径",
        status_code=422,
        meta={"field": path},
    )


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
