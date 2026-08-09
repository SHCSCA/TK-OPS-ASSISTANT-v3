from __future__ import annotations

import logging
from typing import NoReturn

from fastapi import Request
from starlette.requests import HTTPConnection

from app.logging import log_event
from errors import DomainError, ErrorCode

log = logging.getLogger(__name__)


def require_request_origin(request: Request) -> None:
    """校验 HTTP 请求的 Host 与可选 Origin。"""

    validate_connection_origin(request)


def validate_connection_origin(connection: HTTPConnection) -> None:
    """为 HTTP 与 WebSocket 提供同一来源校验入口。"""

    runtime_config = getattr(connection.app.state, "runtime_config", None)
    expected_host = getattr(runtime_config, "expected_host", "")
    host_values = _header_values(connection, "host")
    if (
        not expected_host
        or len(host_values) != 1
        or host_values[0] != expected_host
    ):
        if not expected_host:
            log.error("Runtime 预期 Host 未配置，已拒绝请求")
        _reject_origin(
            connection,
            error_code=ErrorCode.RUNTIME_HOST_INVALID,
            message="Runtime 请求目标不合法",
            status_code=400,
            config_missing=not expected_host,
        )

    origin_values = _header_values(connection, "origin")
    if not origin_values:
        return

    allowed_origins = tuple(getattr(runtime_config, "allowed_origins", ()))
    if (
        len(origin_values) != 1
        or origin_values[0] == "*"
        or origin_values[0] not in allowed_origins
    ):
        _reject_origin(
            connection,
            error_code=ErrorCode.RUNTIME_ORIGIN_FORBIDDEN,
            message="请求来源不受信任",
            status_code=403,
            config_missing=not allowed_origins,
        )


def _reject_origin(
    connection: HTTPConnection,
    *,
    error_code: ErrorCode,
    message: str,
    status_code: int,
    config_missing: bool,
) -> NoReturn:
    log_context = {
        "path": connection.url.path,
        "connectionType": connection.scope.get("type", "http"),
        "hasOrigin": bool(_header_values(connection, "origin")),
        "configMissing": config_missing,
    }
    log_event(
        "security",
        "runtime.origin_rejected",
        level=logging.WARNING,
        error_code=str(error_code),
        context=log_context,
    )
    raise DomainError(
        error_code,
        message,
        status_code=status_code,
        log_context=log_context,
    )


def _header_values(connection: HTTPConnection, header_name: str) -> list[str]:
    expected_name = header_name.lower().encode("ascii")
    return [
        value.decode("latin-1")
        for name, value in connection.scope.get("headers", ())
        if name.lower() == expected_name
    ]
