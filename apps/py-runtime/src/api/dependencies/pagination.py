from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Annotated

from fastapi import Query, Request

from common.pagination import (
    CursorPosition,
    PaginationCursorCodec,
    PaginationCursorError,
)
from errors import DomainError, ErrorCode, FieldError
from services.config import ConfigBusService, ConfigBusSnapshot
from services.config.schema import (
    API_PAGINATION_LIMIT_MAXIMUM,
    API_PAGINATION_LIMIT_MINIMUM,
)

PAGINATION_DEFAULT_LIMIT_KEY = "api.paginationDefaultLimit"
PAGINATION_MAX_LIMIT_KEY = "api.paginationMaxLimit"
PAGINATION_CURSOR_MAX_LENGTH = 2_048
_CURSOR_CODEC = PaginationCursorCodec()


@dataclass(frozen=True, slots=True)
class PaginationParams:
    """集中校验、编解码并绑定分页范围与筛选条件。"""

    cursor: str | None
    limit: int
    codec: PaginationCursorCodec = field(
        default=_CURSOR_CODEC,
        compare=False,
        repr=False,
    )

    def decode_cursor(
        self,
        *,
        scope: str,
        resource_kind: str,
        filters: Mapping[str, object],
    ) -> CursorPosition | None:
        if self.cursor is None:
            return None
        try:
            fingerprint = self.codec.fingerprint(filters)
            return self.codec.decode(
                self.cursor,
                scope=scope,
                resource_kind=resource_kind,
                filter_fingerprint=fingerprint,
            )
        except PaginationCursorError as exc:
            raise _invalid_scoped_cursor_error() from exc

    def encode_cursor(
        self,
        position: CursorPosition | None,
        *,
        scope: str,
        resource_kind: str,
        filters: Mapping[str, object],
    ) -> str | None:
        if position is None:
            return None
        try:
            fingerprint = self.codec.fingerprint(filters)
            return self.codec.encode(
                position,
                scope=scope,
                resource_kind=resource_kind,
                filter_fingerprint=fingerprint,
            )
        except PaginationCursorError as exc:
            raise DomainError(
                ErrorCode.INTERNAL_ERROR,
                "分页结果编码失败，请查看诊断日志",
                status_code=500,
                loggable=True,
            ) from exc


def parse_pagination(
    snapshot: ConfigBusSnapshot,
    *,
    cursor: str | None = None,
    limit: int | None = None,
) -> PaginationParams:
    """根据配置快照解析公共分页参数。"""

    default_limit, maximum_limit = _pagination_limits(snapshot)
    field_errors: list[FieldError] = []

    if cursor is not None and (
        not isinstance(cursor, str)
        or not cursor
        or len(cursor) > PAGINATION_CURSOR_MAX_LENGTH
        or cursor != cursor.strip()
    ):
        field_errors.append(
            FieldError(
                field="cursor",
                code="invalid_cursor",
                message=(
                    "分页游标必须为 1 至 2048 位非空字符串，"
                    "且不能包含首尾空白"
                ),
            )
        )

    resolved_limit = default_limit
    if limit is not None:
        if (
            not isinstance(limit, int)
            or isinstance(limit, bool)
            or limit < API_PAGINATION_LIMIT_MINIMUM
        ):
            field_errors.append(
                FieldError(
                    field="limit",
                    code="invalid_limit",
                    message="分页条数必须为大于零的整数",
                )
            )
        elif limit > maximum_limit:
            field_errors.append(
                FieldError(
                    field="limit",
                    code="limit_exceeded",
                    message=f"分页条数不能超过配置上限 {maximum_limit}",
                )
            )
        else:
            resolved_limit = limit

    if field_errors:
        raise DomainError(
            ErrorCode.REQUEST_VALIDATION_FAILED,
            "分页参数格式无效",
            status_code=422,
            field_errors=field_errors,
        )
    return PaginationParams(cursor=cursor, limit=resolved_limit)


def get_pagination(
    request: Request,
    cursor: Annotated[str | None, Query()] = None,
    limit: Annotated[int | None, Query()] = None,
) -> PaginationParams:
    """从请求与配置总线生成公共分页参数。"""

    snapshot = _resolve_config_bus(request).get(prefix="api.pagination")
    return parse_pagination(snapshot, cursor=cursor, limit=limit)


def _resolve_config_bus(request: Request) -> ConfigBusService:
    service = getattr(request.app.state, "config_bus_service", None)
    if isinstance(service, ConfigBusService):
        return service

    container = getattr(request.app.state, "runtime_container", None)
    service = getattr(getattr(container, "services", None), "config_bus", None)
    if isinstance(service, ConfigBusService):
        return service

    raise DomainError(
        ErrorCode.RUNTIME_NOT_READY,
        "分页配置服务尚未就绪",
        status_code=503,
        loggable=True,
        log_context={
            "operation": "pagination.resolve_config",
            "serviceMissing": True,
        },
    )


def _pagination_limits(snapshot: ConfigBusSnapshot) -> tuple[int, int]:
    default_limit = _required_config_limit(
        snapshot,
        PAGINATION_DEFAULT_LIMIT_KEY,
    )
    maximum_limit = _required_config_limit(
        snapshot,
        PAGINATION_MAX_LIMIT_KEY,
    )
    if default_limit > maximum_limit:
        raise _pagination_config_error(
            PAGINATION_DEFAULT_LIMIT_KEY,
            PAGINATION_MAX_LIMIT_KEY,
        )
    return default_limit, maximum_limit


def _required_config_limit(
    snapshot: ConfigBusSnapshot,
    key: str,
) -> int:
    value = snapshot.values.get(key)
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < API_PAGINATION_LIMIT_MINIMUM
        or value > API_PAGINATION_LIMIT_MAXIMUM
    ):
        raise _pagination_config_error(key)
    return value


def _pagination_config_error(*keys: str) -> DomainError:
    return DomainError(
        ErrorCode.INTERNAL_ERROR,
        "API 分页配置异常，请查看诊断日志",
        status_code=500,
        loggable=True,
        log_context={
            "operation": "pagination.resolve_config",
            "invalidConfigKeys": list(keys),
        },
    )


def _invalid_scoped_cursor_error() -> DomainError:
    return DomainError(
        ErrorCode.REQUEST_VALIDATION_FAILED,
        "分页游标与当前资源或筛选条件不匹配",
        status_code=422,
        field_errors=[
            FieldError(
                field="cursor",
                code="invalid_scoped_cursor",
                message="请重新从当前资源与筛选条件的第一页加载",
            )
        ],
    )
