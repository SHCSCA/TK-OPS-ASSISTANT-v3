from __future__ import annotations

import re
from dataclasses import dataclass
from uuid import uuid4

from fastapi import FastAPI, Request

from app.logging import (
    pop_log_context,
    pop_request_id,
    push_log_context,
    push_request_id,
)
from errors import DomainError, ErrorCode, FieldError

_HEADER_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


@dataclass(frozen=True, slots=True)
class RequestContext:
    request_id: str
    operation_id: str
    idempotency_key: str | None
    invalid_headers: tuple[str, ...] = ()


def install_request_context_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_context_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
        context = _build_request_context(request)
        request.state.request_context = context
        request.state.request_id = context.request_id
        request.state.operation_id = context.operation_id
        request.state.idempotency_key = context.idempotency_key

        request_token = push_request_id(context.request_id)
        log_token = push_log_context(
            request_id=context.request_id,
            operation_id=context.operation_id,
        )
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = context.request_id
            response.headers["X-Operation-ID"] = context.operation_id
            return response
        finally:
            pop_log_context(log_token)
            pop_request_id(request_token)


def get_request_context(request: Request) -> RequestContext:
    context = getattr(request.state, "request_context", None)
    if not isinstance(context, RequestContext):
        context = _build_request_context(request)
        request.state.request_context = context

    if context.invalid_headers:
        raise DomainError(
            ErrorCode.REQUEST_VALIDATION_FAILED,
            "请求关联标识格式无效",
            status_code=422,
            field_errors=[
                FieldError(
                    field=header,
                    code="invalid_header_id",
                    message="必须为 1 至 128 位受控标识",
                )
                for header in context.invalid_headers
            ],
        )
    return context


def _build_request_context(request: Request) -> RequestContext:
    invalid_headers: list[str] = []
    request_id = _parse_optional_id(
        request.headers.get("X-Request-ID"),
        header_name="X-Request-ID",
        invalid_headers=invalid_headers,
    )
    operation_id = _parse_optional_id(
        request.headers.get("X-Operation-ID"),
        header_name="X-Operation-ID",
        invalid_headers=invalid_headers,
    )
    idempotency_key = _parse_optional_id(
        request.headers.get("Idempotency-Key"),
        header_name="Idempotency-Key",
        invalid_headers=invalid_headers,
    )
    return RequestContext(
        request_id=request_id or f"req_{uuid4().hex}",
        operation_id=operation_id or f"op_{uuid4().hex}",
        idempotency_key=idempotency_key,
        invalid_headers=tuple(invalid_headers),
    )


def _parse_optional_id(
    raw_value: str | None,
    *,
    header_name: str,
    invalid_headers: list[str],
) -> str | None:
    if raw_value is None:
        return None
    value = raw_value.strip()
    if not _HEADER_ID_PATTERN.fullmatch(value):
        invalid_headers.append(header_name)
        return None
    return value
