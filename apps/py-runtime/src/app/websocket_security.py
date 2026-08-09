from __future__ import annotations

import asyncio
import base64
import binascii
import logging
from collections.abc import Awaitable, Callable
from uuid import uuid4

from fastapi import WebSocket

from api.dependencies.request_origin_guard import validate_connection_origin
from api.dependencies.runtime_session_guard import (
    validate_runtime_session_token,
)
from api.websocket import WebSocketAccessContext
from app.config import is_development_mode
from app.logging import log_event
from errors import DomainError, ErrorCode
from repositories.account_repository import AccountRepository
from services.bootstrap_v1 import BootstrapV1Service
from services.events.topics import (
    SYSTEM_AI_TOPIC,
    SYSTEM_BOOTSTRAP_TOPIC,
    SYSTEM_CONFIG_TOPIC,
    SYSTEM_HEALTH_TOPIC,
    SYSTEM_TASKS_TOPIC,
)

log = logging.getLogger(__name__)

WEBSOCKET_APPLICATION_PROTOCOL = "tk-ops-runtime-v1"
WEBSOCKET_SESSION_PROTOCOL_PREFIX = "tk-ops-session."
ALLOWED_SYSTEM_TOPICS = frozenset(
    {
        SYSTEM_BOOTSTRAP_TOPIC,
        SYSTEM_CONFIG_TOPIC,
        SYSTEM_HEALTH_TOPIC,
        SYSTEM_AI_TOPIC,
        SYSTEM_TASKS_TOPIC,
    }
)

AccountAuthorizer = Callable[
    [WebSocketAccessContext, str],
    Awaitable[None],
]


def build_websocket_connection_authorizer(
    bootstrap_service: BootstrapV1Service,
) -> Callable[[WebSocket], Awaitable[WebSocketAccessContext]]:
    async def authorize(websocket: WebSocket) -> WebSocketAccessContext:
        validate_connection_origin(websocket)
        token = _read_session_token(websocket)
        validate_runtime_session_token(websocket, token)

        request_id = f"req_ws_{uuid4().hex}"
        operation_id = f"op_ws_{uuid4().hex}"
        status = await asyncio.to_thread(
            bootstrap_service.get_license_status,
            request_id=request_id,
            operation_id=operation_id,
        )
        if status.status != "active":
            error_code = (
                ErrorCode.LICENSE_MACHINE_MISMATCH
                if status.status == "machine_mismatch"
                else ErrorCode.LICENSE_INVALID
            )
            raise DomainError(
                error_code,
                "许可证与本机不匹配"
                if status.status == "machine_mismatch"
                else "许可证无效，请先完成激活",
                status_code=403,
                log_context={"licenseStatus": status.status},
            )

        return WebSocketAccessContext(
            session_id=f"ws_{uuid4().hex}",
            accepted_subprotocol=WEBSOCKET_APPLICATION_PROTOCOL,
            allowed_system_topics=ALLOWED_SYSTEM_TOPICS,
        )

    return authorize


def build_legacy_websocket_connection_authorizer(
    bootstrap_service: BootstrapV1Service,
) -> Callable[[WebSocket], Awaitable[WebSocketAccessContext]]:
    v1_authorizer = build_websocket_connection_authorizer(
        bootstrap_service
    )

    async def authorize(websocket: WebSocket) -> WebSocketAccessContext:
        runtime_config = getattr(websocket.app.state, "runtime_config", None)
        mode = str(getattr(runtime_config, "mode", "")).strip().lower()
        if is_development_mode(mode):
            expected_host = str(
                getattr(runtime_config, "expected_host", "")
            ).strip()
            if expected_host:
                validate_connection_origin(websocket)
            else:
                _validate_legacy_development_origin(websocket)
            access = await _authorize_active_license_without_subprotocol(
                bootstrap_service
            )
        else:
            access = await v1_authorizer(websocket)

        log_event(
            "audit",
            "legacy_api.used",
            context={
                "method": "WEBSOCKET",
                "path": websocket.url.path,
                "replacement": "/api/v1/ws",
            },
        )
        return access

    return authorize


def build_account_subscription_authorizer(
    repository: AccountRepository,
) -> AccountAuthorizer:
    async def authorize(
        _access: WebSocketAccessContext,
        account_id: str,
    ) -> None:
        try:
            account = await asyncio.to_thread(
                repository.get_account,
                account_id,
            )
        except Exception as exc:
            log.exception(
                "校验 WebSocket 账号订阅失败",
                extra={"account_id": account_id},
            )
            raise DomainError(
                ErrorCode.INTERNAL_ERROR,
                "账号订阅校验失败，请稍后重试",
                status_code=500,
                loggable=True,
                log_context={"accountId": account_id},
            ) from exc
        if account is None:
            raise DomainError(
                ErrorCode.ACCOUNT_NOT_FOUND,
                "账号不存在",
                status_code=404,
            )
        if account.status == "archived":
            raise DomainError(
                ErrorCode.ACCOUNT_ARCHIVED,
                "账号已归档，不能订阅工作区事件",
                status_code=409,
            )

    return authorize


async def _authorize_active_license_without_subprotocol(
    bootstrap_service: BootstrapV1Service,
) -> WebSocketAccessContext:
    request_id = f"req_ws_{uuid4().hex}"
    operation_id = f"op_ws_{uuid4().hex}"
    status = await asyncio.to_thread(
        bootstrap_service.get_license_status,
        request_id=request_id,
        operation_id=operation_id,
    )
    if status.status != "active":
        error_code = (
            ErrorCode.LICENSE_MACHINE_MISMATCH
            if status.status == "machine_mismatch"
            else ErrorCode.LICENSE_INVALID
        )
        raise DomainError(
            error_code,
            "许可证与本机不匹配"
            if status.status == "machine_mismatch"
            else "许可证无效，请先完成激活",
            status_code=403,
            log_context={"licenseStatus": status.status},
        )
    return WebSocketAccessContext(
        session_id=f"ws_legacy_{uuid4().hex}",
        accepted_subprotocol=None,
        allowed_system_topics=ALLOWED_SYSTEM_TOPICS,
    )


def _validate_legacy_development_origin(websocket: WebSocket) -> None:
    origin_values = [
        value.decode("latin-1")
        for name, value in websocket.scope.get("headers", ())
        if name.lower() == b"origin"
    ]
    if not origin_values:
        return
    runtime_config = getattr(websocket.app.state, "runtime_config", None)
    allowed_origins = tuple(
        getattr(runtime_config, "allowed_origins", ())
    )
    if (
        len(origin_values) != 1
        or origin_values[0] == "*"
        or origin_values[0] not in allowed_origins
    ):
        raise DomainError(
            ErrorCode.RUNTIME_ORIGIN_FORBIDDEN,
            "请求来源不受信任",
            status_code=403,
        )


def encode_runtime_session_subprotocol(token: str) -> str:
    encoded = base64.urlsafe_b64encode(token.encode("utf-8")).decode("ascii")
    return f"{WEBSOCKET_SESSION_PROTOCOL_PREFIX}{encoded.rstrip('=')}"


def _read_session_token(websocket: WebSocket) -> str:
    raw_values = [
        value.decode("latin-1")
        for name, value in websocket.scope.get("headers", ())
        if name.lower() == b"sec-websocket-protocol"
    ]
    if len(raw_values) != 1:
        raise DomainError(
            ErrorCode.RUNTIME_SESSION_INVALID,
            "WebSocket 会话子协议无效",
            status_code=401,
        )
    protocols = tuple(
        item.strip()
        for item in raw_values[0].split(",")
        if item.strip()
    )
    session_protocols = tuple(
        item
        for item in protocols
        if item.startswith(WEBSOCKET_SESSION_PROTOCOL_PREFIX)
    )
    if (
        len(protocols) != 2
        or protocols.count(WEBSOCKET_APPLICATION_PROTOCOL) != 1
        or len(session_protocols) != 1
    ):
        raise DomainError(
            ErrorCode.RUNTIME_SESSION_INVALID,
            "WebSocket 会话子协议无效",
            status_code=401,
        )

    encoded = session_protocols[0].removeprefix(
        WEBSOCKET_SESSION_PROTOCOL_PREFIX
    )
    if not encoded:
        raise DomainError(
            ErrorCode.RUNTIME_SESSION_INVALID,
            "WebSocket 会话子协议无效",
            status_code=401,
        )
    padding = "=" * (-len(encoded) % 4)
    try:
        token_bytes = base64.b64decode(
            encoded + padding,
            altchars=b"-_",
            validate=True,
        )
        token = token_bytes.decode("utf-8")
    except (binascii.Error, UnicodeDecodeError) as exc:
        raise DomainError(
            ErrorCode.RUNTIME_SESSION_INVALID,
            "WebSocket 会话子协议无效",
            status_code=401,
        ) from exc
    if not token or any(character.isspace() for character in token):
        raise DomainError(
            ErrorCode.RUNTIME_SESSION_INVALID,
            "WebSocket 会话子协议无效",
            status_code=401,
        )
    return token
