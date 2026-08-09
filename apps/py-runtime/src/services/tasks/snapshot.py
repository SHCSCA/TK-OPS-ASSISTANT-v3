from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping
from uuid import NAMESPACE_URL, uuid5

from services.tasks.errors import (
    idempotency_key_required,
    task_snapshot_invalid,
)
from services.tasks.types import FrozenTaskSnapshot, JsonValue

_KEY_NORMALIZER = re.compile(r"[^a-z0-9]")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_FORBIDDEN_KEYS = frozenset(
    {
        "apikey",
        "authorization",
        "password",
        "prompt",
        "promptbody",
        "prompttext",
        "rawprompt",
        "refreshtoken",
        "systemprompt",
        "tasktemplate",
    }
)
_MAX_NESTING_DEPTH = 12


class TaskSnapshotPolicy:
    """将处理器输入冻结为受控、可校验且不含敏感正文的快照。"""

    def __init__(self, *, max_bytes: int) -> None:
        if max_bytes <= 0:
            raise ValueError("任务快照上限必须大于零")
        self._max_bytes = max_bytes

    def freeze(
        self,
        payload: Mapping[str, JsonValue],
        *,
        allowed_fields: frozenset[str],
        handler_version: int,
        idempotency_key: str,
        request_id: str,
        operation_id: str,
        attempt: int,
        retry_of_task_id: str | None,
        requested_timeout_seconds: int | None,
    ) -> FrozenTaskSnapshot:
        normalized_key = idempotency_key.strip()
        if not normalized_key:
            raise idempotency_key_required()
        if (
            isinstance(handler_version, bool)
            or not isinstance(handler_version, int)
            or handler_version < 1
        ):
            raise task_snapshot_invalid("任务处理器版本必须大于零")
        if isinstance(attempt, bool) or attempt < 1:
            raise task_snapshot_invalid("任务尝试次数必须大于零")
        if retry_of_task_id is not None and not retry_of_task_id.strip():
            raise task_snapshot_invalid("重试来源任务 ID 不能为空")
        if (
            requested_timeout_seconds is not None
            and (
                isinstance(requested_timeout_seconds, bool)
                or requested_timeout_seconds <= 0
            )
        ):
            raise task_snapshot_invalid("请求超时必须大于零")

        unexpected = sorted(set(payload) - allowed_fields)
        if unexpected:
            raise task_snapshot_invalid(
                f"任务快照包含未允许字段：{', '.join(unexpected)}"
            )

        safe_payload = {
            key: self._sanitize(value, key_path=key, depth=0)
            for key, value in payload.items()
        }
        key_hash = _sha256_text(normalized_key)
        request_hash = _sha256_json(safe_payload)
        envelope: dict[str, JsonValue] = {
            "schemaVersion": 2,
            "handlerVersion": handler_version,
            "requestId": request_id,
            "operationId": operation_id,
            "payload": safe_payload,
            "idempotency": {
                "keyHash": key_hash,
                "requestHash": request_hash,
            },
            "command": {
                "creationAttempt": attempt,
                "retryOfTaskId": retry_of_task_id,
                "requestedTimeoutSeconds": requested_timeout_seconds,
            },
        }
        serialized = _canonical_json(envelope)
        if len(serialized.encode("utf-8")) > self._max_bytes:
            raise task_snapshot_invalid("任务快照超过配置总线允许的大小")
        return FrozenTaskSnapshot(
            serialized=serialized,
            key_hash=key_hash,
            request_hash=request_hash,
            handler_version=handler_version,
            payload=safe_payload,
            creation_attempt=attempt,
            retry_of_task_id=retry_of_task_id,
            requested_timeout_seconds=requested_timeout_seconds,
        )

    def load(
        self,
        serialized: str,
        *,
        expected_handler_version: int | None = None,
    ) -> FrozenTaskSnapshot:
        try:
            raw = json.loads(serialized)
        except (TypeError, ValueError) as exc:
            raise task_snapshot_invalid(
                "持久任务快照无法解析",
                stored_snapshot=True,
            ) from exc
        if not isinstance(raw, dict):
            raise task_snapshot_invalid(
                "持久任务快照结构无效",
                stored_snapshot=True,
            )

        schema_version = raw.get("schemaVersion")
        handler_version = raw.get("handlerVersion")
        payload = raw.get("payload")
        idempotency = raw.get("idempotency")
        if (
            isinstance(schema_version, bool)
            or not isinstance(schema_version, int)
            or schema_version != 2
            or isinstance(handler_version, bool)
            or not isinstance(handler_version, int)
            or handler_version < 1
            or not isinstance(payload, dict)
            or not isinstance(idempotency, dict)
        ):
            raise task_snapshot_invalid(
                "持久任务快照缺少必要版本或幂等信息",
                stored_snapshot=True,
            )
        if (
            expected_handler_version is not None
            and handler_version != expected_handler_version
        ):
            raise task_snapshot_invalid(
                "任务处理器版本与持久快照不兼容",
                stored_snapshot=True,
            )

        command = raw.get("command")
        if not isinstance(command, dict):
            raise task_snapshot_invalid(
                "持久任务快照缺少创建命令信息",
                stored_snapshot=True,
            )
        creation_attempt = command.get("creationAttempt")
        retry_of_task_id = command.get("retryOfTaskId")
        requested_timeout_seconds = command.get("requestedTimeoutSeconds")
        if (
            isinstance(creation_attempt, bool)
            or not isinstance(creation_attempt, int)
            or creation_attempt < 1
            or (
                retry_of_task_id is not None
                and (
                    not isinstance(retry_of_task_id, str)
                    or not retry_of_task_id.strip()
                )
            )
            or (
                requested_timeout_seconds is not None
                and (
                    isinstance(requested_timeout_seconds, bool)
                    or not isinstance(requested_timeout_seconds, int)
                    or requested_timeout_seconds <= 0
                )
            )
        ):
            raise task_snapshot_invalid(
                "持久任务快照创建命令无效",
                stored_snapshot=True,
            )

        key_hash = idempotency.get("keyHash")
        request_hash = idempotency.get("requestHash")
        if (
            not isinstance(key_hash, str)
            or _SHA256_PATTERN.fullmatch(key_hash) is None
            or not isinstance(request_hash, str)
            or _SHA256_PATTERN.fullmatch(request_hash) is None
        ):
            raise task_snapshot_invalid(
                "持久任务快照幂等摘要无效",
                stored_snapshot=True,
            )
        safe_payload = {
            str(key): self._sanitize(value, key_path=str(key), depth=0)
            for key, value in payload.items()
        }
        if _sha256_json(safe_payload) != request_hash:
            raise task_snapshot_invalid(
                "持久任务快照完整性校验失败",
                stored_snapshot=True,
            )
        return FrozenTaskSnapshot(
            serialized=serialized,
            key_hash=key_hash,
            request_hash=request_hash,
            handler_version=handler_version,
            payload=safe_payload,
            creation_attempt=creation_attempt,
            retry_of_task_id=retry_of_task_id,
            requested_timeout_seconds=requested_timeout_seconds,
        )

    def _sanitize(
        self,
        value: object,
        *,
        key_path: str,
        depth: int,
    ) -> JsonValue:
        if depth > _MAX_NESTING_DEPTH:
            raise task_snapshot_invalid(f"任务快照字段 {key_path} 嵌套过深")
        self._reject_sensitive_key(key_path)

        if value is None or isinstance(value, (bool, str)):
            return value
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            if not math.isfinite(value):
                raise task_snapshot_invalid(f"任务快照字段 {key_path} 不是有限数值")
            return value
        if isinstance(value, list):
            return [
                self._sanitize(
                    item,
                    key_path=f"{key_path}[{index}]",
                    depth=depth + 1,
                )
                for index, item in enumerate(value)
            ]
        if isinstance(value, Mapping):
            return {
                str(key): self._sanitize(
                    item,
                    key_path=f"{key_path}.{key}",
                    depth=depth + 1,
                )
                for key, item in value.items()
            }
        raise task_snapshot_invalid(f"任务快照字段 {key_path} 不是 JSON 安全类型")

    def _reject_sensitive_key(self, key_path: str) -> None:
        raw_key = key_path.rsplit(".", maxsplit=1)[-1].split("[", maxsplit=1)[0]
        normalized = _KEY_NORMALIZER.sub("", raw_key.lower())
        safe_reference = normalized.endswith(("id", "ids", "ref", "refs", "version"))
        if (
            normalized in _FORBIDDEN_KEYS
            or "password" in normalized
            or ("secret" in normalized and not safe_reference)
            or ("credential" in normalized and not safe_reference)
            or ("token" in normalized and not safe_reference)
        ):
            raise task_snapshot_invalid(f"任务快照禁止保存敏感字段：{key_path}")


def task_id_for(
    *,
    scope_key: str,
    task_type: str,
    idempotency_key_hash: str,
) -> str:
    stable_value = f"{scope_key}|{task_type}|{idempotency_key_hash}"
    return f"task_{uuid5(NAMESPACE_URL, stable_value).hex}"


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_json(value: object) -> str:
    return _sha256_text(_canonical_json(value))


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )
