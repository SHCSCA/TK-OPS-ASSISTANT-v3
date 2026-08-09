from __future__ import annotations

import hmac
import logging
from typing import NoReturn

from fastapi import Request
from starlette.requests import HTTPConnection

from app.logging import log_event
from errors import DomainError, ErrorCode

log = logging.getLogger(__name__)


def require_runtime_session(request: Request) -> None:
    """校验 HTTP 请求携带的本机 Runtime 会话。"""

    authorization_values = _header_values(request, "authorization")
    if not authorization_values:
        _reject_session(
            request,
            error_code=ErrorCode.RUNTIME_SESSION_REQUIRED,
            message="缺少本机 Runtime 会话凭据",
        )
    if len(authorization_values) != 1:
        _reject_session(
            request,
            error_code=ErrorCode.RUNTIME_SESSION_INVALID,
            message="本机 Runtime 会话凭据无效",
        )

    authorization = authorization_values[0]
    scheme, separator, presented_token = authorization.partition(" ")
    if (
        separator != " "
        or scheme.lower() != "bearer"
        or not presented_token
        or presented_token != presented_token.strip()
        or any(character.isspace() for character in presented_token)
    ):
        _reject_session(
            request,
            error_code=ErrorCode.RUNTIME_SESSION_INVALID,
            message="本机 Runtime 会话凭据无效",
        )

    validate_runtime_session_token(request, presented_token)


def validate_runtime_session_token(
    connection: HTTPConnection,
    presented_token: str,
) -> None:
    """校验由 HTTP Header 或 WebSocket 子协议提取的会话令牌。"""

    runtime_config = getattr(connection.app.state, "runtime_config", None)
    expected_token = getattr(runtime_config, "runtime_session_token", "")
    if not expected_token:
        log.error("Runtime 会话令牌未配置，已拒绝请求")
        _reject_session(
            connection,
            error_code=ErrorCode.RUNTIME_SESSION_INVALID,
            message="本机 Runtime 会话尚未就绪",
            config_missing=True,
        )

    if not hmac.compare_digest(
        presented_token.encode("utf-8"),
        expected_token.encode("utf-8"),
    ):
        _reject_session(
            connection,
            error_code=ErrorCode.RUNTIME_SESSION_INVALID,
            message="本机 Runtime 会话已失效",
        )


def _reject_session(
    connection: HTTPConnection,
    *,
    error_code: ErrorCode,
    message: str,
    config_missing: bool = False,
) -> NoReturn:
    log_event(
        "security",
        "runtime.session_rejected",
        level=logging.WARNING,
        error_code=str(error_code),
        context={
            "path": connection.url.path,
            "connectionType": connection.scope.get("type", "http"),
            "configMissing": config_missing,
        },
    )
    raise DomainError(
        error_code,
        message,
        status_code=401,
        headers={"WWW-Authenticate": "Bearer"},
        log_context={
            "path": connection.url.path,
            "connectionType": connection.scope.get("type", "http"),
            "configMissing": config_missing,
        },
    )


def _header_values(connection: HTTPConnection, header_name: str) -> list[str]:
    expected_name = header_name.lower().encode("ascii")
    return [
        value.decode("latin-1")
        for name, value in connection.scope.get("headers", ())
        if name.lower() == expected_name
    ]
