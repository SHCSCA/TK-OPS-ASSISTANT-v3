from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

from errors import DomainError, ErrorCode


def dump_json(value: object) -> str:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError, RecursionError) as exc:
        raise DomainError(
            ErrorCode.REQUEST_VALIDATION_FAILED,
            "AI 配置包含无法保存的内容",
            status_code=422,
        ) from exc


def load_object(raw_value: str, *, label: str) -> dict[str, Any]:
    value = _load(raw_value, label=label)
    if not isinstance(value, dict):
        raise _damaged_json(label)
    return value


def load_list(raw_value: str, *, label: str) -> list[Any]:
    value = _load(raw_value, label=label)
    if not isinstance(value, list):
        raise _damaged_json(label)
    return value


def content_hash(value: Mapping[str, object] | Sequence[object]) -> str:
    serialized = dump_json(value)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _load(raw_value: str, *, label: str) -> object:
    try:
        return json.loads(raw_value)
    except (TypeError, json.JSONDecodeError) as exc:
        raise _damaged_json(label) from exc


def _damaged_json(label: str) -> DomainError:
    return DomainError(
        ErrorCode.INTERNAL_ERROR,
        f"{label}数据异常，请查看诊断日志",
        status_code=500,
        loggable=True,
    )

