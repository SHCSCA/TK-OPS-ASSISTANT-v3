from __future__ import annotations

import logging
from typing import NoReturn

from fastapi import Request

from api.dependencies.request_origin_guard import validate_connection_origin
from api.dependencies.runtime_session_guard import require_runtime_session
from app.config import is_development_mode
from app.logging import log_event
from errors import DomainError, ErrorCode

log = logging.getLogger(__name__)


def require_legacy_access(request: Request) -> None:
    """兼容期开发调用保留旧客户端，生产调用仍强制本机会话。"""

    runtime_config = getattr(request.app.state, "runtime_config", None)
    mode = str(getattr(runtime_config, "mode", "")).strip().lower()
    requires_session = not is_development_mode(mode)
    expected_host = str(
        getattr(runtime_config, "expected_host", "")
    ).strip()
    if requires_session or expected_host:
        validate_connection_origin(request)
    else:
        _validate_development_origin(request)
    if requires_session:
        require_runtime_session(request)


def record_legacy_api_use(
    request: Request,
    *,
    replacement: str,
) -> None:
    log_event(
        "audit",
        "legacy_api.used",
        request_id=getattr(request.state, "request_id", None),
        operation_id=getattr(request.state, "operation_id", None),
        context={
            "method": request.method,
            "path": request.url.path,
            "replacement": replacement,
        },
    )


def legacy_write_unsupported(
    *,
    replacement: str,
) -> NoReturn:
    raise DomainError(
        ErrorCode.LEGACY_WRITE_UNSUPPORTED,
        "旧写入方式已停用，请使用新的版本化接口",
        status_code=410,
        meta={"replacement": replacement},
    )


def _validate_development_origin(request: Request) -> None:
    origin_values = [
        value.decode("latin-1")
        for name, value in request.scope.get("headers", ())
        if name.lower() == b"origin"
    ]
    if not origin_values:
        return
    runtime_config = getattr(request.app.state, "runtime_config", None)
    allowed_origins = tuple(
        getattr(runtime_config, "allowed_origins", ())
    )
    if (
        len(origin_values) != 1
        or origin_values[0] == "*"
        or origin_values[0] not in allowed_origins
    ):
        log.warning("开发模式 legacy 请求来源被拒绝")
        raise DomainError(
            ErrorCode.RUNTIME_ORIGIN_FORBIDDEN,
            "请求来源不受信任",
            status_code=403,
        )
