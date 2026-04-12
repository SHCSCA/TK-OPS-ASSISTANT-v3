from __future__ import annotations

import logging
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from api.routes import (
    ai_capabilities_router,
    dashboard_router,
    license_router,
    scripts_router,
    settings_router,
    storyboards_router,
)
from app.config import load_runtime_config
from app.logging import configure_logging, log_event, pop_request_id, push_request_id
from app.secret_store import build_secret_store
from repositories.ai_capability_repository import AICapabilityRepository
from repositories.ai_job_repository import AIJobRepository
from repositories.dashboard_repository import DashboardRepository
from repositories.license_repository import LicenseRepository
from repositories.script_repository import ScriptRepository
from repositories.storyboard_repository import StoryboardRepository
from repositories.system_config_repository import SystemConfigRepository
from schemas.envelope import error_response
from services.ai_capability_service import AICapabilityService
from services.ai_text_generation_service import AITextGenerationService
from services.dashboard_service import DashboardService
from services.license_activation import OfflineLicenseActivationAdapter
from services.license_service import LicenseService
from services.machine_code import MachineCodeService
from services.script_service import ScriptService
from services.settings_service import SettingsService
from services.storyboard_service import StoryboardService


def create_app() -> FastAPI:
    runtime_config = load_runtime_config()
    secret_store = build_secret_store(runtime_config)

    settings_repository = SystemConfigRepository(runtime_config.database_path)
    license_repository = LicenseRepository(runtime_config.database_path)
    dashboard_repository = DashboardRepository(runtime_config.database_path)
    ai_capability_repository = AICapabilityRepository(runtime_config.database_path)
    ai_job_repository = AIJobRepository(runtime_config.database_path)
    script_repository = ScriptRepository(runtime_config.database_path)
    storyboard_repository = StoryboardRepository(runtime_config.database_path)

    settings_service = SettingsService(
        runtime_config=runtime_config,
        repository=settings_repository,
        on_settings_updated=lambda settings: configure_logging(
            Path(settings.paths.logDir), settings.logging.level
        ),
    )
    dashboard_service = DashboardService(dashboard_repository)
    ai_capability_service = AICapabilityService(ai_capability_repository, secret_store)
    ai_text_generation_service = AITextGenerationService(
        ai_capability_service,
        ai_job_repository,
    )
    script_service = ScriptService(
        dashboard_service,
        script_repository,
        ai_job_repository,
        ai_text_generation_service,
    )
    storyboard_service = StoryboardService(
        dashboard_service,
        storyboard_repository,
        ai_job_repository,
        ai_text_generation_service,
        script_service,
    )
    machine_code_service = MachineCodeService()
    license_service = LicenseService(
        runtime_config=runtime_config,
        repository=license_repository,
        activation_adapter=OfflineLicenseActivationAdapter(
            runtime_config.license_public_key_path
        ),
        machine_code_service=machine_code_service,
    )
    current_settings = settings_service.get_settings()
    configure_logging(Path(current_settings.paths.logDir), current_settings.logging.level)

    app = FastAPI(
        title='TK-OPS Runtime',
        summary='TK-OPS creative chain foundation runtime',
        version=runtime_config.version,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:1420",
            "http://localhost:1420",
            "tauri://localhost",
            "http://tauri.localhost",
        ],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.runtime_config = runtime_config
    app.state.secret_store = secret_store
    app.state.license_service = license_service
    app.state.settings_service = settings_service
    app.state.dashboard_service = dashboard_service
    app.state.ai_capability_service = ai_capability_service
    app.state.ai_text_generation_service = ai_text_generation_service
    app.state.script_service = script_service
    app.state.storyboard_service = storyboard_service

    @app.middleware('http')
    async def request_context_middleware(request, call_next):  # type: ignore[no-untyped-def]
        request_id = uuid4().hex
        request.state.request_id = request_id
        token = push_request_id(request_id)

        try:
            response = await call_next(request)
        except Exception:
            pop_request_id(token)
            raise

        response.headers['X-Request-ID'] = request_id
        pop_request_id(token)
        return response

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request, exc: RequestValidationError):  # type: ignore[no-untyped-def]
        request_id = getattr(request.state, 'request_id', uuid4().hex)
        log_event(
            'system',
            'request.validation_failed',
            level=logging.WARNING,
            request_id=request_id,
            context={
                'path': request.url.path,
                'method': request.method,
                'errors': exc.errors(),
            },
        )
        return JSONResponse(
            status_code=422,
            content=error_response(
                'Request validation failed',
                request_id=request_id,
                details=exc.errors(),
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request, exc: StarletteHTTPException):  # type: ignore[no-untyped-def]
        request_id = getattr(request.state, 'request_id', uuid4().hex)
        message = exc.detail if isinstance(exc.detail, str) else 'Request failed'
        level = logging.ERROR if exc.status_code >= 500 else logging.WARNING
        log_event(
            'system',
            'request.http_error',
            level=level,
            request_id=request_id,
            context={
                'path': request.url.path,
                'method': request.method,
                'statusCode': exc.status_code,
                'detail': message,
            },
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(message, request_id=request_id),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_exception(request, exc: Exception):  # type: ignore[no-untyped-def]
        request_id = getattr(request.state, 'request_id', uuid4().hex)
        log_event(
            'system',
            'request.unhandled_exception',
            level=logging.ERROR,
            request_id=request_id,
            context={
                'path': request.url.path,
                'method': request.method,
                'errorType': exc.__class__.__name__,
            },
        )
        return JSONResponse(
            status_code=500,
            content=error_response('Internal server error', request_id=request_id),
        )

    app.include_router(ai_capabilities_router)
    app.include_router(dashboard_router)
    app.include_router(license_router)
    app.include_router(scripts_router)
    app.include_router(settings_router)
    app.include_router(storyboards_router)
    log_event(
        'system',
        'runtime.started',
        context={
            'mode': current_settings.runtime.mode,
            'databasePath': str(runtime_config.database_path),
        },
    )
    return app
