from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

from domain.models.account_configuration import PositioningProfile
from domain.models.ai_prompt import PromptProfile
from errors import DomainError, ErrorCode, FieldError
from services.ai_configuration_v1.json_codec import content_hash, load_object

from .knowledge_context import FrozenKnowledgeContext

_VARIABLE_PATTERN = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_.-]*)\s*\}\}")


@dataclass(frozen=True, slots=True)
class RenderedPrompt:
    messages: tuple[dict[str, object], ...]
    rendered_hash: str
    input_schema_hash: str
    output_schema_hash: str
    output_schema: dict[str, Any]


def render_prompt(
    prompt: PromptProfile,
    *,
    input_value: dict[str, object],
    knowledge: FrozenKnowledgeContext,
    positioning: PositioningProfile | None,
) -> RenderedPrompt:
    variables_schema = load_object(
        prompt.variables_schema_json,
        label="Prompt 变量 Schema",
    )
    output_schema = load_object(
        prompt.output_schema_json,
        label="Prompt 输出 Schema",
    )
    safety = load_object(
        prompt.safety_constraints_json,
        label="Prompt 安全约束",
    )
    _verify_prompt_hash(prompt, variables_schema, output_schema, safety)
    _validate_input(input_value, variables_schema)
    system_text = _render_template(prompt.system_prompt, input_value)
    task_text = _render_template(prompt.task_template, input_value)
    positioning_summary = positioning.summary if positioning is not None else ""
    system_sections = [system_text]
    if positioning_summary:
        system_sections.append(f"账号定位：\n{positioning_summary}")
    if safety:
        system_sections.append(
            "安全约束：\n" + _canonical_json(safety)
        )
    user_sections = [
        task_text,
        "受控输入：\n" + _canonical_json(input_value),
        "账号知识上下文：\n" + knowledge.text,
    ]
    messages = (
        {"role": "system", "content": "\n\n".join(system_sections)},
        {"role": "user", "content": "\n\n".join(user_sections)},
    )
    return RenderedPrompt(
        messages=messages,
        rendered_hash=_sha256_json(list(messages)),
        input_schema_hash=_sha256_json(variables_schema),
        output_schema_hash=_sha256_json(output_schema),
        output_schema=output_schema,
    )


def _verify_prompt_hash(
    prompt: PromptProfile,
    variables_schema: dict[str, Any],
    output_schema: dict[str, Any],
    safety: dict[str, Any],
) -> None:
    digest = content_hash(
        {
            "name": prompt.name,
            "systemPrompt": prompt.system_prompt,
            "taskTemplate": prompt.task_template,
            "variablesSchema": variables_schema,
            "outputSchema": output_schema,
            "visualStylePrefix": prompt.visual_style_prefix or "",
            "safetyConstraints": safety,
        }
    )
    if digest != prompt.content_hash:
        raise DomainError(
            ErrorCode.AI_PROMPT_SCHEMA_INVALID,
            "Prompt 不可变正文完整性校验失败",
            status_code=409,
            loggable=True,
        )


def _validate_input(
    value: dict[str, object],
    schema: dict[str, Any],
) -> None:
    if schema.get("type") not in (None, "object"):
        raise _prompt_input_invalid("Prompt 输入 Schema 顶层必须为 object")
    properties = schema.get("properties", {})
    if not isinstance(properties, dict):
        raise _prompt_input_invalid("Prompt 输入 Schema properties 无效")
    required = schema.get("required", [])
    if not isinstance(required, list) or any(
        not isinstance(item, str) for item in required
    ):
        raise _prompt_input_invalid("Prompt 输入 Schema required 无效")
    missing = [item for item in required if item not in value]
    if missing:
        raise DomainError(
            ErrorCode.AI_EXECUTION_INVALID,
            "AI 执行输入缺少 Prompt 必填字段",
            status_code=422,
            field_errors=[
                FieldError(
                    field=f"input.{item}",
                    code="required",
                    message="必须提供该字段",
                )
                for item in missing
            ],
        )
    for key, item in value.items():
        rule = properties.get(key)
        if isinstance(rule, dict):
            _validate_simple_type(key, item, rule.get("type"))


def _validate_simple_type(key: str, value: object, expected: object) -> None:
    checks = {
        "string": lambda item: isinstance(item, str),
        "integer": lambda item: isinstance(item, int) and not isinstance(item, bool),
        "number": lambda item: isinstance(item, (int, float)) and not isinstance(item, bool),
        "boolean": lambda item: isinstance(item, bool),
        "object": lambda item: isinstance(item, dict),
        "array": lambda item: isinstance(item, list),
        "null": lambda item: item is None,
    }
    if isinstance(expected, str) and expected in checks and not checks[expected](value):
        raise DomainError(
            ErrorCode.AI_EXECUTION_INVALID,
            "AI 执行输入与 Prompt Schema 不匹配",
            status_code=422,
            field_errors=[
                FieldError(
                    field=f"input.{key}",
                    code="invalid_type",
                    message=f"字段类型必须为 {expected}",
                )
            ],
        )


def _render_template(template: str, values: dict[str, object]) -> str:
    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        resolved = _resolve_value(values, key)
        if resolved is None:
            raise _prompt_input_invalid(f"Prompt 变量 {key} 缺少值")
        if isinstance(resolved, (dict, list)):
            return _canonical_json(resolved)
        return str(resolved)

    return _VARIABLE_PATTERN.sub(replace, template)


def _resolve_value(values: dict[str, object], path: str) -> object | None:
    current: object = values
    for segment in path.split("."):
        if not isinstance(current, dict) or segment not in current:
            return None
        current = current[segment]
    return current


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _sha256_json(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _prompt_input_invalid(message: str) -> DomainError:
    return DomainError(
        ErrorCode.AI_PROMPT_SCHEMA_INVALID,
        message,
        status_code=409,
        loggable=True,
    )


__all__ = ["RenderedPrompt", "render_prompt"]
