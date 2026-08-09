"""统一分页游标编码与范围绑定。"""

from __future__ import annotations

import base64
import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass

from common.identifiers import is_stable_id

_CURSOR_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,2048}$")
_FILTER_FINGERPRINT_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_RESOURCE_KIND_PATTERN = re.compile(
    r"^[a-z][a-z0-9_-]*(?:\.[a-z][a-z0-9_-]*)*$"
)


class PaginationCursorError(ValueError):
    pass


class PaginationCursorMismatchError(PaginationCursorError):
    pass


@dataclass(frozen=True, slots=True)
class CursorPosition:
    sort_value: str
    resource_id: str


class PaginationCursorCodec:
    def fingerprint(self, filters: Mapping[str, object]) -> str:
        try:
            serialized = json.dumps(
                filters,
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
                sort_keys=True,
            )
        except (TypeError, ValueError, RecursionError) as exc:
            raise PaginationCursorError("分页筛选条件无法编码") from exc
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def encode(
        self,
        position: CursorPosition,
        *,
        scope: str,
        resource_kind: str,
        filter_fingerprint: str,
    ) -> str:
        self._validate_context(
            scope=scope,
            resource_kind=resource_kind,
            filter_fingerprint=filter_fingerprint,
        )
        self._validate_position(position)
        payload = json.dumps(
            {
                "version": 1,
                "scope": scope,
                "resourceKind": resource_kind,
                "filterFingerprint": filter_fingerprint,
                "sortValue": position.sort_value,
                "resourceId": position.resource_id,
            },
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        cursor = base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")
        if not _CURSOR_PATTERN.fullmatch(cursor):
            raise PaginationCursorError("分页游标超过允许长度")
        return cursor

    def decode(
        self,
        cursor: str,
        *,
        scope: str,
        resource_kind: str,
        filter_fingerprint: str,
    ) -> CursorPosition:
        self._validate_context(
            scope=scope,
            resource_kind=resource_kind,
            filter_fingerprint=filter_fingerprint,
        )
        if not _CURSOR_PATTERN.fullmatch(cursor):
            raise PaginationCursorError("分页游标格式无效")
        try:
            padding = "=" * (-len(cursor) % 4)
            raw = base64.urlsafe_b64decode(f"{cursor}{padding}")
            canonical = (
                base64.urlsafe_b64encode(raw)
                .decode("ascii")
                .rstrip("=")
            )
            payload = json.loads(raw.decode("utf-8"))
        except (
            ValueError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as exc:
            raise PaginationCursorError("分页游标格式无效") from exc
        if canonical != cursor:
            raise PaginationCursorError("分页游标不是规范编码")
        if not isinstance(payload, dict) or payload.get("version") != 1:
            raise PaginationCursorError("分页游标版本无效")
        if (
            payload.get("scope") != scope
            or payload.get("resourceKind") != resource_kind
            or payload.get("filterFingerprint") != filter_fingerprint
        ):
            raise PaginationCursorMismatchError(
                "分页游标不属于当前范围、资源或筛选条件"
            )
        sort_value = payload.get("sortValue")
        resource_id = payload.get("resourceId")
        if not isinstance(sort_value, str) or not isinstance(
            resource_id,
            str,
        ):
            raise PaginationCursorError("分页位置内容无效")
        position = CursorPosition(
            sort_value=sort_value,
            resource_id=resource_id,
        )
        self._validate_position(position)
        return position

    @staticmethod
    def _validate_context(
        *,
        scope: str,
        resource_kind: str,
        filter_fingerprint: str,
    ) -> None:
        if scope != "system" and not is_stable_id(scope):
            raise PaginationCursorError("分页范围格式无效")
        if not _RESOURCE_KIND_PATTERN.fullmatch(resource_kind):
            raise PaginationCursorError("分页资源类型格式无效")
        if not _FILTER_FINGERPRINT_PATTERN.fullmatch(filter_fingerprint):
            raise PaginationCursorError("分页筛选摘要格式无效")

    @staticmethod
    def _validate_position(position: CursorPosition) -> None:
        if (
            not isinstance(position.sort_value, str)
            or not position.sort_value
            or len(position.sort_value) > 512
            or not is_stable_id(position.resource_id)
        ):
            raise PaginationCursorError("分页位置内容无效")
