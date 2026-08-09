from __future__ import annotations

import logging
import re
from collections.abc import Mapping
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.logging import log_event
from errors import DomainError, ErrorCode, FieldError
from schemas.envelope import error_response as legacy_error_response
from schemas.v1.envelope import error_response as v1_error_response

log = logging.getLogger(__name__)

REQUEST_VALIDATION_FAILED_MESSAGE = "请求参数校验失败"
REQUEST_FAILED_MESSAGE = "请求处理失败"
INTERNAL_SERVER_ERROR_MESSAGE = "系统内部错误，请稍后重试"
HTTP_ERROR_MESSAGES: dict[int, str] = {
    400: "请求格式不正确",
    401: "请求身份校验失败",
    403: "当前请求不被允许",
    404: "请求的接口不存在",
    405: "请求方法不受支持",
    409: "请求状态发生冲突",
    413: "请求内容超过允许大小",
    422: REQUEST_VALIDATION_FAILED_MESSAGE,
    429: "请求过于频繁，请稍后重试",
    500: INTERNAL_SERVER_ERROR_MESSAGE,
    503: "Runtime 服务暂不可用",
    504: "请求处理超时，请稍后重试",
}
LEGACY_ERROR_CODE_MAP: dict[str, str] = {
    ErrorCode.REQUEST_VALIDATION_FAILED: "request.validation_failed",
    ErrorCode.ROUTE_NOT_FOUND: "runtime.resource_not_found",
    ErrorCode.METHOD_NOT_ALLOWED: "runtime.method_not_allowed",
    ErrorCode.REQUEST_CONFLICT: "task.conflict",
    ErrorCode.REQUEST_TIMEOUT: "runtime.timeout",
    ErrorCode.INTERNAL_ERROR: "runtime.internal_error",
}
_VALIDATION_LOCATION_ROOTS = frozenset(
    {"body", "query", "path", "header", "cookie"}
)
_STATIC_LOCATION_SEGMENT_PATTERN = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_]{0,63}$"
)
_DYNAMIC_LOCATION_SEGMENT = "field"


def install_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, handle_domain_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, handle_http_exception)
    app.add_exception_handler(Exception, handle_unexpected_exception)


async def handle_domain_error(
    request: Request,
    exc: DomainError,
) -> JSONResponse:
    request_id, operation_id = _request_ids(request)
    log_id = (
        _new_log_id()
        if exc.loggable or exc.status_code >= 500
        else None
    )
    log_event(
        "domain",
        "request.domain_error",
        level=logging.ERROR if exc.status_code >= 500 else logging.WARNING,
        request_id=request_id,
        operation_id=operation_id,
        log_id=log_id,
        error_code=exc.error_code,
        context={
            "path": request.url.path,
            "method": request.method,
            "statusCode": exc.status_code,
            **exc.log_context,
        },
    )
    return _error_json_response(
        request=request,
        status_code=exc.status_code,
        message=exc.message,
        error_code=exc.error_code,
        request_id=request_id,
        log_id=log_id,
        field_errors=exc.field_errors,
        meta=exc.meta,
        headers=exc.headers,
    )


async def handle_validation_error(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    request_id, operation_id = _request_ids(request)
    field_errors = _safe_validation_errors(exc)
    log_event(
        "validation",
        "request.validation_failed",
        level=logging.WARNING,
        request_id=request_id,
        operation_id=operation_id,
        error_code=ErrorCode.REQUEST_VALIDATION_FAILED,
        context={
            "path": request.url.path,
            "method": request.method,
            "fields": [item.field for item in field_errors],
            "rules": [item.code for item in field_errors],
        },
    )
    return _error_json_response(
        request=request,
        status_code=422,
        message=REQUEST_VALIDATION_FAILED_MESSAGE,
        error_code=ErrorCode.REQUEST_VALIDATION_FAILED,
        request_id=request_id,
        field_errors=field_errors,
    )


async def handle_http_exception(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    request_id, operation_id = _request_ids(request)
    message = HTTP_ERROR_MESSAGES.get(
        exc.status_code,
        REQUEST_FAILED_MESSAGE,
    )
    raw_error_code = getattr(exc, "error_code", None)
    error_code = str(raw_error_code or _http_error_code(exc.status_code))
    should_create_log = exc.status_code >= 500
    log_id = _new_log_id() if should_create_log else None
    log_event(
        "http",
        "request.http_error",
        level=logging.ERROR if should_create_log else logging.WARNING,
        request_id=request_id,
        operation_id=operation_id,
        log_id=log_id,
        error_code=error_code,
        context={
            "path": request.url.path,
            "method": request.method,
            "statusCode": exc.status_code,
        },
    )
    return _error_json_response(
        request=request,
        status_code=exc.status_code,
        message=message,
        error_code=error_code,
        request_id=request_id,
        log_id=log_id,
        legacy_details=getattr(exc, "details", None),
        headers=exc.headers,
    )


async def handle_unexpected_exception(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    request_id, operation_id = _request_ids(request)
    log_id = _new_log_id()
    log.exception(
        "Runtime 未知请求异常",
        extra={
            "category": "system",
            "operation": "request.unhandled_exception",
            "request_id": request_id,
            "operation_id": operation_id,
            "log_id": log_id,
            "error_code": ErrorCode.INTERNAL_ERROR,
            "context": {
                "path": request.url.path,
                "method": request.method,
                "errorType": exc.__class__.__name__,
            },
        },
    )
    return _error_json_response(
        request=request,
        status_code=500,
        message=INTERNAL_SERVER_ERROR_MESSAGE,
        error_code=ErrorCode.INTERNAL_ERROR,
        request_id=request_id,
        log_id=log_id,
    )


def _error_json_response(
    *,
    request: Request,
    status_code: int,
    message: str,
    error_code: ErrorCode | str,
    request_id: str,
    log_id: str | None = None,
    field_errors: tuple[FieldError, ...] | list[FieldError] = (),
    meta: Mapping[str, object] | None = None,
    legacy_details: object | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    if request.url.path.startswith("/api/v1"):
        content = v1_error_response(
            message,
            error_code=str(error_code),
            log_id=log_id,
            field_errors=field_errors,
            meta=meta,
        )
    else:
        content = legacy_error_response(
            message,
            request_id=request_id,
            details=(
                [item.to_dict() for item in field_errors]
                or _safe_legacy_details(legacy_details)
            ),
            error_code=_legacy_error_code(str(error_code)),
        )
    return JSONResponse(
        status_code=status_code,
        content=content,
        headers=dict(headers or {}),
    )


def _request_ids(request: Request) -> tuple[str, str]:
    context = getattr(request.state, "request_context", None)
    request_id = getattr(context, "request_id", None) or getattr(
        request.state,
        "request_id",
        None,
    )
    operation_id = getattr(context, "operation_id", None) or getattr(
        request.state,
        "operation_id",
        None,
    )
    return (
        request_id if isinstance(request_id, str) else f"req_{uuid4().hex}",
        operation_id if isinstance(operation_id, str) else f"op_{uuid4().hex}",
    )


def _safe_validation_errors(exc: RequestValidationError) -> list[FieldError]:
    safe_errors: list[FieldError] = []
    # FastAPI 的兼容异常包装器不接收 Pydantic 的过滤参数，因此只读取安全字段。
    for item in exc.errors():
        rule_code = str(item.get("type", "invalid"))
        location = _safe_validation_location(
            item.get("loc", ()),
            rule_code=rule_code,
        )
        safe_errors.append(
            FieldError(
                field=location or "request",
                code=rule_code,
                message=_validation_message(rule_code),
            )
        )
    return safe_errors


def _safe_validation_location(
    raw_location: object,
    *,
    rule_code: str,
) -> str:
    if not isinstance(raw_location, (list, tuple)) or not raw_location:
        return "request"

    root = raw_location[0]
    if not isinstance(root, str) or root not in _VALIDATION_LOCATION_ROOTS:
        return "request.field"

    safe_parts = [root]
    for index, part in enumerate(raw_location[1:], start=1):
        if isinstance(part, int) and part >= 0:
            safe_parts.append(str(part))
            continue
        if (
            index == 1
            and rule_code != "extra_forbidden"
            and isinstance(part, str)
            and _STATIC_LOCATION_SEGMENT_PATTERN.fullmatch(part)
        ):
            safe_parts.append(part)
            continue
        # 深层映射键和额外字段可能来自用户输入，统一替换为中性字段名。
        safe_parts.append(_DYNAMIC_LOCATION_SEGMENT)
    return ".".join(safe_parts)


def _validation_message(rule_code: str) -> str:
    if rule_code == "missing":
        return "必填字段缺失"
    if rule_code in {"string_too_short", "too_short"}:
        return "内容长度不足"
    if rule_code in {"string_too_long", "too_long"}:
        return "内容长度超过限制"
    if rule_code.startswith(("int_", "float_", "decimal_")):
        return "数值格式或范围不正确"
    if rule_code in {"literal_error", "enum"}:
        return "字段值不在允许范围内"
    return "字段格式或取值不符合要求"


def _http_error_code(status_code: int) -> ErrorCode:
    if status_code == 404:
        return ErrorCode.ROUTE_NOT_FOUND
    if status_code == 405:
        return ErrorCode.METHOD_NOT_ALLOWED
    if status_code == 409:
        return ErrorCode.REQUEST_CONFLICT
    if status_code == 504:
        return ErrorCode.REQUEST_TIMEOUT
    if status_code >= 500:
        return ErrorCode.INTERNAL_ERROR
    return ErrorCode.REQUEST_VALIDATION_FAILED


def _legacy_error_code(error_code: str) -> str:
    if error_code in LEGACY_ERROR_CODE_MAP:
        return LEGACY_ERROR_CODE_MAP[error_code]
    if error_code == error_code.upper():
        return error_code.casefold().replace("_", ".")
    return error_code


def _safe_legacy_details(value: object) -> object | None:
    if isinstance(value, Mapping):
        return {
            str(key): (
                "[REDACTED]"
                if any(
                    marker in str(key).casefold()
                    for marker in (
                        "authorization",
                        "credential",
                        "secret",
                        "token",
                        "password",
                        "prompt",
                    )
                )
                else _safe_legacy_details(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_safe_legacy_details(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _new_log_id() -> str:
    return f"log_{uuid4().hex}"
