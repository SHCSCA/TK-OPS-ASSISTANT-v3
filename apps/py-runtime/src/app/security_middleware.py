from __future__ import annotations

from fastapi import FastAPI, Request

from api.dependencies.request_origin_guard import validate_connection_origin
from api.dependencies.runtime_session_guard import require_runtime_session
from app.exception_handlers import handle_domain_error
from errors import DomainError


def install_v1_security_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def v1_security_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
        if not _is_v1_path(request.url.path):
            return await call_next(request)

        try:
            validate_connection_origin(request)
            if request.method != "OPTIONS":
                require_runtime_session(request)
        except DomainError as exc:
            return await handle_domain_error(request, exc)
        return await call_next(request)


def _is_v1_path(path: str) -> bool:
    return path == "/api/v1" or path.startswith("/api/v1/")
