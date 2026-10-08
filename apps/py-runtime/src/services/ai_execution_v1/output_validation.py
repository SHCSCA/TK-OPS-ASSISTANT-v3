from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from errors import DomainError, ErrorCode


@dataclass(frozen=True, slots=True)
class ValidatedAIOutput:
    text: str
    kind: str
    mime_type: str
    schema_status: str
    safe_summary: dict[str, object]


def validate_provider_output(
    text: str,
    output_schema: dict[str, Any],
) -> ValidatedAIOutput:
    if not text.strip():
        raise _invalid_output()
    expected_type = output_schema.get("type")
    if expected_type in ("object", "array"):
        try:
            value = json.loads(text)
        except json.JSONDecodeError as exc:
            raise _invalid_output() from exc
        if expected_type == "object" and not isinstance(value, dict):
            raise _invalid_output()
        if expected_type == "array" and not isinstance(value, list):
            raise _invalid_output()
        _validate_required(value, output_schema)
        return ValidatedAIOutput(
            text=text,
            kind="json",
            mime_type="application/json; charset=utf-8",
            schema_status="valid",
            safe_summary={
                "format": "json",
                "topLevelType": expected_type,
                "characterCount": len(text),
            },
        )
    return ValidatedAIOutput(
        text=text,
        kind="text",
        mime_type="text/plain; charset=utf-8",
        schema_status="valid",
        safe_summary={
            "format": "text",
            "characterCount": len(text),
            "lineCount": text.count("\n") + 1,
        },
    )


def _validate_required(value: object, schema: dict[str, Any]) -> None:
    required = schema.get("required", [])
    if not required:
        return
    if (
        not isinstance(required, list)
        or any(not isinstance(item, str) for item in required)
        or not isinstance(value, dict)
        or any(item not in value for item in required)
    ):
        raise _invalid_output()


def _invalid_output() -> DomainError:
    return DomainError(
        ErrorCode.AI_PROVIDER_RESPONSE_INVALID,
        "Provider 输出不符合冻结的输出 Schema",
        status_code=502,
        loggable=True,
    )


__all__ = ["ValidatedAIOutput", "validate_provider_output"]
