from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Mapping, Sequence

from errors import DomainError, ErrorCode

log = logging.getLogger(__name__)


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
            "配置内容不是有效 JSON",
            status_code=422,
        ) from exc


def load_json_object(value: str, *, resource_label: str) -> dict[str, object]:
    loaded = _load_json(value, resource_label=resource_label)
    if not isinstance(loaded, dict):
        raise _stored_json_error(resource_label)
    return loaded


def load_json_list(value: str, *, resource_label: str) -> list[object]:
    loaded = _load_json(value, resource_label=resource_label)
    if not isinstance(loaded, list):
        raise _stored_json_error(resource_label)
    return loaded


def content_hash(value: object) -> str:
    return hashlib.sha256(dump_json(value).encode("utf-8")).hexdigest()


def combined_content_hash(
    values: Mapping[str, object] | Sequence[object],
) -> str:
    return content_hash(values)


def _load_json(value: str, *, resource_label: str) -> object:
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError, RecursionError) as exc:
        log.exception("%s 的持久化 JSON 结构损坏", resource_label)
        raise _stored_json_error(resource_label) from exc


def _stored_json_error(resource_label: str) -> DomainError:
    return DomainError(
        ErrorCode.INTERNAL_ERROR,
        f"{resource_label}数据结构异常，请查看诊断日志",
        status_code=500,
        loggable=True,
    )
