from __future__ import annotations

import hashlib
import json
import logging
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy.orm import Session

from common.identifiers import is_stable_id
from domain.models.mutation_idempotency import RuntimeMutationIdempotency
from errors import DomainError, ErrorCode, FieldError
from repositories.mutation_idempotency_repository import (
    MutationIdempotencyRecord,
    MutationIdempotencyRepository,
)

log = logging.getLogger(__name__)

_OPERATION_PATTERN = re.compile(r"^[a-z][a-z0-9._-]{0,127}$")
_IDEMPOTENCY_KEY_PATTERN = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$"
)
_LOCAL_PATH_PATTERN = re.compile(
    r"^(?:[A-Za-z]:[\\/]|\\\\[^\\/]+[\\/]|/(?!api(?:/|$)))"
)
_FORBIDDEN_RESPONSE_KEYS = frozenset(
    {
        "activationcode",
        "apikey",
        "body",
        "credential",
        "credentialref",
        "executablepath",
        "licensekey",
        "localpath",
        "password",
        "profilepath",
        "prompt",
        "requestbody",
        "responsebody",
        "rootpath",
        "secret",
        "sessionref",
        "systemprompt",
        "tasktemplate",
        "text",
        "token",
        "workspacepath",
    }
)
_SAFE_REFERENCE_RESPONSE_KEYS = frozenset(
    {
        "promptprofileid",
    }
)


@dataclass(frozen=True, slots=True)
class MutationCommand:
    account_id: str | None
    operation_name: str
    idempotency_key: str
    request_payload: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class MutationReplay:
    response: dict[str, object]
    resource_type: str | None
    resource_id: str | None


class MutationIdempotencyService:
    def __init__(
        self,
        repository: MutationIdempotencyRepository,
        *,
        retention_seconds: int | Callable[[], int],
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if callable(retention_seconds):
            self._retention_seconds_provider = retention_seconds
        else:
            _validate_retention_seconds(retention_seconds)
            self._retention_seconds_provider = lambda: retention_seconds
        self._repository = repository
        self._clock = clock or (lambda: datetime.now(UTC))

    def find_replay(
        self,
        session: Session,
        command: MutationCommand,
    ) -> MutationReplay | None:
        key_hash, request_hash = self._validate_and_hash(command)
        stored = self._get_stored(session, command, key_hash)
        if stored is None:
            return None
        now_text = _to_utc_text(_normalize_utc(self._clock()))
        if stored.expires_at <= now_text:
            removed = self._repository.delete_expired_record(
                session,
                record_id=stored.id,
                now=now_text,
            )
            if removed:
                return None
            stored = self._get_stored(session, command, key_hash)
            if stored is None:
                return None
        if stored.request_hash != request_hash:
            raise DomainError(
                ErrorCode.REQUEST_CONFLICT,
                "同一幂等键已用于不同的请求内容",
                status_code=409,
                meta={"operation": command.operation_name},
            )
        try:
            response = json.loads(stored.response_json)
        except (json.JSONDecodeError, TypeError) as exc:
            log.exception(
                "普通写操作幂等响应记录损坏",
                extra={
                    "account_id": command.account_id,
                    "resource_type": stored.resource_type,
                    "resource_id": stored.resource_id,
                },
            )
            raise DomainError(
                ErrorCode.INTERNAL_ERROR,
                "幂等响应记录异常，请查看诊断日志",
                status_code=500,
                loggable=True,
            ) from exc
        if not isinstance(response, dict):
            log.error(
                "普通写操作幂等响应不是对象",
                extra={
                    "account_id": command.account_id,
                    "resource_type": stored.resource_type,
                    "resource_id": stored.resource_id,
                },
            )
            raise DomainError(
                ErrorCode.INTERNAL_ERROR,
                "幂等响应记录异常，请查看诊断日志",
                status_code=500,
                loggable=True,
            )
        return MutationReplay(
            response=response,
            resource_type=stored.resource_type,
            resource_id=stored.resource_id,
        )

    def _get_stored(
        self,
        session: Session,
        command: MutationCommand,
        key_hash: str,
    ) -> MutationIdempotencyRecord | None:
        if command.account_id is None:
            return self._repository.get_system(
                session,
                operation_name=command.operation_name,
                idempotency_key_hash=key_hash,
            )
        return self._repository.get_account(
            session,
            account_id=command.account_id,
            operation_name=command.operation_name,
            idempotency_key_hash=key_hash,
        )

    def store(
        self,
        session: Session,
        command: MutationCommand,
        *,
        response: Mapping[str, object],
        resource_type: str | None = None,
        resource_id: str | None = None,
    ) -> MutationReplay:
        key_hash, request_hash = self._validate_and_hash(command)
        if (resource_type is None) != (resource_id is None):
            raise ValueError("幂等资源类型与资源 ID 必须同时提供")
        serialized = _serialize_safe_response(response)
        created_at = _normalize_utc(self._clock())
        retention_seconds = self._retention_seconds_provider()
        _validate_retention_seconds(retention_seconds)
        expires_at = created_at + timedelta(seconds=retention_seconds)
        self._repository.add(
            session,
            RuntimeMutationIdempotency(
                id=f"mut_{uuid4().hex}",
                scope="system" if command.account_id is None else "account",
                account_id=command.account_id,
                operation_name=command.operation_name,
                idempotency_key_hash=key_hash,
                request_hash=request_hash,
                response_json=serialized,
                resource_type=resource_type,
                resource_id=resource_id,
                created_at=_to_utc_text(created_at),
                expires_at=_to_utc_text(expires_at),
            ),
        )
        return MutationReplay(
            response=json.loads(serialized),
            resource_type=resource_type,
            resource_id=resource_id,
        )

    @staticmethod
    def _validate_and_hash(command: MutationCommand) -> tuple[str, str]:
        if (
            command.account_id is not None
            and not is_stable_id(command.account_id)
        ):
            raise ValueError("账号 ID 格式无效")
        if not _OPERATION_PATTERN.fullmatch(command.operation_name):
            raise ValueError("普通写操作名称格式无效")
        key = command.idempotency_key
        if not _IDEMPOTENCY_KEY_PATTERN.fullmatch(key):
            raise DomainError(
                ErrorCode.REQUEST_VALIDATION_FAILED,
                "写操作缺少有效的幂等键",
                status_code=422,
                field_errors=[
                    FieldError(
                        field="Idempotency-Key",
                        code="invalid_idempotency_key",
                        message="必须为 1 至 128 位受控标识",
                    )
                ],
            )
        return (
            hashlib.sha256(key.encode("utf-8")).hexdigest(),
            _hash_json(command.request_payload),
        )


def _hash_json(payload: Mapping[str, object]) -> str:
    try:
        serialized = json.dumps(
            payload,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError, RecursionError) as exc:
        raise DomainError(
            ErrorCode.REQUEST_VALIDATION_FAILED,
            "请求内容无法用于幂等校验",
            status_code=422,
        ) from exc
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _serialize_safe_response(response: Mapping[str, object]) -> str:
    _validate_safe_response_value(response, field="$")
    try:
        return json.dumps(
            response,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError, RecursionError) as exc:
        raise ValueError("幂等响应必须是有效 JSON 对象") from exc


def _validate_safe_response_value(value: object, *, field: str) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("幂等响应字段名必须是字符串")
            normalized_key = re.sub(r"[^a-z0-9]", "", key.casefold())
            if _is_forbidden_response_key(normalized_key):
                raise ValueError(f"幂等响应不得保存敏感字段：{field}.{key}")
            _validate_safe_response_value(item, field=f"{field}.{key}")
        return
    if isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _validate_safe_response_value(item, field=f"{field}[{index}]")
        return
    if isinstance(value, str) and _LOCAL_PATH_PATTERN.match(value):
        raise ValueError(f"幂等响应不得保存本地路径：{field}")
    if value is None or isinstance(value, (bool, int, float, str)):
        return
    raise ValueError(f"幂等响应字段不是 JSON 类型：{field}")


def _normalize_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("幂等记录时钟必须包含时区")
    return value.astimezone(UTC)


def _to_utc_text(value: datetime) -> str:
    return value.isoformat(timespec="microseconds").replace("+00:00", "Z")


def _is_forbidden_response_key(normalized_key: str) -> bool:
    if normalized_key in _SAFE_REFERENCE_RESPONSE_KEYS:
        return False
    if normalized_key in _FORBIDDEN_RESPONSE_KEYS:
        return True
    return any(
        part in normalized_key
        for part in (
            "activationcode",
            "credential",
            "licensekey",
            "password",
            "prompt",
            "secret",
            "token",
        )
    )


def _validate_retention_seconds(value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError("普通写操作幂等保留时间必须大于零")
