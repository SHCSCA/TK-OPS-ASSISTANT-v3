from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import UTC, datetime
from uuid import uuid4

from domain.models.ai_configuration_v1 import PromptProfile
from errors import DomainError, ErrorCode

from .json_codec import content_hash, dump_json
from .validation import (
    require_capability_key,
    require_object,
    require_profile_key,
)

_VARIABLE_PATTERN = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_.-]*)\s*\}\}")
_MAX_PROMPT_CHARS = 200_000

def _normalize_prompt_profile(
    payload: Mapping[str, object],
) -> dict[str, object]:
    return {
        **_normalize_prompt_body(payload),
        "profileKey": require_profile_key(
            payload.get("profileKey"),
            field="profileKey",
        ),
        "capabilityKey": require_capability_key(
            payload.get("capabilityKey")
        ),
    }


def _normalize_prompt_version(
    payload: Mapping[str, object],
) -> dict[str, object]:
    created_from = payload.get("createdFromVersion")
    if (
        not isinstance(created_from, int)
        or isinstance(created_from, bool)
        or created_from < 1
    ):
        raise DomainError(
            ErrorCode.PROMPT_PROFILE_INVALID,
            "Prompt 来源版本无效",
            status_code=422,
        )
    return {
        **_normalize_prompt_body(payload),
        "createdFromVersion": created_from,
    }


def _normalize_prompt_body(
    payload: Mapping[str, object],
) -> dict[str, object]:
    name = _required_text(payload.get("name"), field="name", maximum=128)
    system_prompt = _required_text(
        payload.get("systemPrompt"),
        field="systemPrompt",
        maximum=_MAX_PROMPT_CHARS,
    )
    task_template = _required_text(
        payload.get("taskTemplate"),
        field="taskTemplate",
        maximum=_MAX_PROMPT_CHARS,
    )
    variables_schema = require_object(
        payload.get("variablesSchema"),
        field="variablesSchema",
    )
    output_schema = require_object(
        payload.get("outputSchema"),
        field="outputSchema",
    )
    safety = require_object(
        payload.get("safetyConstraints"),
        field="safetyConstraints",
    )
    prefix = payload.get("visualStylePrefix")
    if prefix is not None and (
        not isinstance(prefix, str) or len(prefix) > 10_000
    ):
        raise DomainError(
            ErrorCode.PROMPT_PROFILE_INVALID,
            "视觉风格前缀格式无效",
            status_code=422,
        )
    _validate_template_variables(
        system_prompt,
        task_template,
        variables_schema,
    )
    return {
        "name": name,
        "systemPrompt": system_prompt,
        "taskTemplate": task_template,
        "variablesSchema": variables_schema,
        "outputSchema": output_schema,
        "visualStylePrefix": prefix or "",
        "safetyConstraints": safety,
    }


def _build_prompt_row(
    payload: Mapping[str, object],
    *,
    profile_key: str,
    capability_key: str,
    version: int,
    created_from_id: str | None,
    revision: int,
) -> PromptProfile:
    now = _utc_now()
    digest = _prompt_payload_hash(payload)
    return PromptProfile(
        id=f"prompt_{uuid4().hex}",
        profile_key=profile_key,
        name=str(payload["name"]),
        capability_key=capability_key,
        version=version,
        status="draft",
        system_prompt=str(payload["systemPrompt"]),
        task_template=str(payload["taskTemplate"]),
        variables_schema_json=dump_json(payload["variablesSchema"]),
        output_schema_json=dump_json(payload["outputSchema"]),
        visual_style_prefix=str(payload["visualStylePrefix"]) or None,
        safety_constraints_json=dump_json(
            payload["safetyConstraints"]
        ),
        content_hash=digest,
        revision=revision,
        created_from_id=created_from_id,
        created_at=now,
        activated_at=None,
    )


def _prompt_payload_hash(payload: Mapping[str, object]) -> str:
    return content_hash(
        {
            "name": payload["name"],
            "systemPrompt": payload["systemPrompt"],
            "taskTemplate": payload["taskTemplate"],
            "variablesSchema": payload["variablesSchema"],
            "outputSchema": payload["outputSchema"],
            "visualStylePrefix": payload["visualStylePrefix"],
            "safetyConstraints": payload["safetyConstraints"],
        }
    )


def _safe_prompt_request(
    payload: Mapping[str, object],
) -> dict[str, object]:
    return {
        "profileKey": payload["profileKey"],
        "capabilityKey": payload["capabilityKey"],
        "contentHash": _prompt_payload_hash(payload),
    }


def _validate_template_variables(
    system_prompt: str,
    task_template: str,
    variables_schema: Mapping[str, object],
) -> None:
    used = set(
        _VARIABLE_PATTERN.findall(f"{system_prompt}\n{task_template}")
    )
    raw_properties = variables_schema.get("properties", {})
    properties = (
        set(raw_properties)
        if isinstance(raw_properties, Mapping)
        else set()
    )
    missing = sorted(used - properties)
    if missing:
        raise DomainError(
            ErrorCode.PROMPT_PROFILE_INVALID,
            "Prompt 使用了未在变量 Schema 声明的变量",
            status_code=422,
            meta={"missingVariables": missing},
        )


def _required_text(
    value: object,
    *,
    field: str,
    maximum: int,
) -> str:
    if (
        isinstance(value, str)
        and value.strip()
        and len(value) <= maximum
    ):
        return value
    raise DomainError(
        ErrorCode.PROMPT_PROFILE_INVALID,
        f"Prompt 字段 {field} 格式无效",
        status_code=422,
    )


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
