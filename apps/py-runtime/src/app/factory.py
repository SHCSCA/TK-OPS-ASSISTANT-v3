from __future__ import annotations

import logging
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from api.routes import settings_router
from app.config import load_runtime_config
from app.logging import configure_logging, log_event, pop_request_id, push_request_id
from app.secret_store import NoopSecretStore
from repositories.system_config_repository import SystemConfigRepository
from schemas.envelope import error_response
from services.settings_service import SettingsService


def create_app() -> FastAPI:
    runtime_config = load_runtime_config()
    settings_repository = SystemConfigRepository(runtime_config.database_path)
    settings_service = SettingsService(
        runtime_config=runtime_config,
        repository=settings_repository,
        on_settings_updated=lambda settings: configure_logging(
            Path(settings.paths.logDir), settings.logging.level
        ),
    )
    current_settings = settings_service.get_settings()
    configure_logging(Path(current_settings.paths.logDir), current_settings.logging.level)

    app = FastAPI(
        title="TK-OPS Runtime",
        summary="TK-OPS M0 local runtime",
        version=runtime_config.version,
    )
    app.state.runtime_config = runtime_config
    app.state.secret_store = NoopSecretStore()
    app.state.settings_service = settings_service

    @app.middleware("http")
    async def request_context_middleware(request, call_next):  # type: ignore[no-untyped-def]
        request_id = uuid4().hex
        request.state.request_id = request_id
        token = push_request_id(request_id)

        try:
            response = await call_next(request)
        except Exception:
            pop_request_id(token)
            raise

        response.headers["X-Request-ID"] = request_id
        pop_request_id(token)
        return response

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request, exc: RequestValidationError):  # type: ignore[no-untyped-def]
        request_id = getattr(request.state, "request_id", uuid4().hex)
        log_event(
            "system",
            "request.validation_failed",
            level=logging.WARNING,
            request_id=request_id,
            context={
                "path": request.url.path,
                "method": request.method,
                "errors": exc.errors(),
            },
        )
        return JSONResponse(
            status_code=422,
            content=error_response(
                "Request validation failed",
                request_id=request_id,
                details=exc.errors(),
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request, exc: StarletteHTTPException):  # type: ignore[no-untyped-def]
        request_id = getattr(request.state, "request_id", uuid4().hex)
        message = exc.detail if isinstance(exc.detail, str) else "Request failed"
        level = logging.ERROR if exc.status_code >= 500 else logging.WARNING
        log_event(
            "system",
            "request.http_error",
            level=level,
            request_id=request_id,
            context={
                "path": request.url.path,
                "method": request.method,
                "statusCode": exc.status_code,
                "detail": message,
            },
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(message, request_id=request_id),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_exception(request, exc: Exception):  # type: ignore[no-untyped-def]
        request_id = getattr(request.state, "request_id", uuid4().hex)
        log_event(
            "system",
            "request.unhandled_exception",
            level=logging.ERROR,
            request_id=request_id,
            context={
                "path": request.url.path,
                "method": request.method,
                "errorType": exc.__class__.__name__,
            },
        )
        return JSONResponse(
            status_code=500,
            content=error_response("Internal server error", request_id=request_id),
        )

    app.include_router(settings_router)
    log_event(
        "system",
        "runtime.started",
        context={
            "mode": current_settings.runtime.mode,
            "databasePath": str(runtime_config.database_path),
        },
    )
    return app
