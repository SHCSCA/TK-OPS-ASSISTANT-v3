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
    accounts_router,
    ai_capabilities_router,
    ai_providers_router,
    assets_router,
    automation_router,
    bootstrap_router,
    dashboard_router,
    device_workspaces_router,
    license_router,
    prompt_templates_router,
    publishing_router,
    renders_router,
    review_router,
    search_router,
    scripts_router,
    settings_router,
    storyboards_router,
    subtitles_router,
    tasks_router,
    video_deconstruction_router,
    voice_router,
    workspace_router,
    ws_router,
)
from app.config import load_runtime_config
from app.logging import configure_logging, log_event, pop_request_id, push_request_id
from app.secret_store import build_secret_store
from persistence.engine import create_runtime_engine, create_session_factory, initialize_domain_schema
from repositories.account_repository import AccountRepository
from repositories.ai_capability_repository import AICapabilityRepository
from repositories.ai_job_repository import AIJobRepository
from repositories.asset_repository import AssetRepository
from repositories.automation_repository import AutomationRepository
from repositories.dashboard_repository import DashboardRepository
from repositories.device_workspace_repository import DeviceWorkspaceRepository
from repositories.imported_video_repository import ImportedVideoRepository
from repositories.license_repository import LicenseRepository
from repositories.prompt_template_repository import PromptTemplateRepository
from repositories.publishing_repository import PublishingRepository
from repositories.render_repository import RenderRepository
from repositories.review_repository import ReviewRepository
from repositories.script_repository import ScriptRepository
from repositories.storyboard_repository import StoryboardRepository
from repositories.subtitle_repository import SubtitleRepository
from repositories.system_config_repository import SystemConfigRepository
from repositories.timeline_repository import TimelineRepository
from repositories.video_deconstruction_repository import VideoDeconstructionRepository
from repositories.voice_profile_repository import VoiceProfileRepository
from repositories.voice_repository import VoiceRepository
from schemas.envelope import error_response
from schemas.error_codes import ErrorCodes
from services.account_service import AccountService
from services.ai_text_generation_service import AITextGenerationService
from services.asset_service import AssetService
from services.automation_service import AutomationService
from services.broadcasting_ai_capability_service import BroadcastingAICapabilityService
from services.dashboard_service import DashboardService
from services.device_workspace_service import DeviceWorkspaceService
from services.license_activation import OfflineLicenseActivationAdapter
from services.license_service import LicenseService
from services.machine_code import MachineCodeService
from services.prompt_template_service import PromptTemplateService
from services.publishing_service import PublishingService
from services.render_service import RenderService
from services.review_service import ReviewService
from services.script_service import ScriptService
from services.search_service import SearchService
from services.settings_service import SettingsService
from services.storyboard_service import StoryboardService
from services.subtitle_service import SubtitleService
from services.task_manager import task_manager
from services.video_deconstruction_service import VideoDeconstructionService
from services.video_import_service import VideoImportService
from services.voice_service import VoiceService
from services.workspace_service import WorkspaceService


def create_app() -> FastAPI:
    runtime_config = load_runtime_config()
    secret_store = build_secret_store(runtime_config)
    engine = create_runtime_engine(runtime_config.database_path)
    initialize_domain_schema(engine)
    session_factory = create_session_factory(engine)

    settings_repository = SystemConfigRepository(session_factory=session_factory)
    license_repository = LicenseRepository(session_factory=session_factory)
    imported_video_repository = ImportedVideoRepository(session_factory=session_factory)
    prompt_template_repository = PromptTemplateRepository(session_factory=session_factory)
    video_deconstruction_repository = VideoDeconstructionRepository(session_factory=session_factory)
    dashboard_repository = DashboardRepository(session_factory=session_factory)
    ai_capability_repository = AICapabilityRepository(session_factory=session_factory)
    ai_job_repository = AIJobRepository(session_factory=session_factory)
    script_repository = ScriptRepository(session_factory=session_factory)
    storyboard_repository = StoryboardRepository(session_factory=session_factory)
    asset_repository = AssetRepository(session_factory=session_factory)
    account_repository = AccountRepository(session_factory=session_factory)
    device_workspace_repository = DeviceWorkspaceRepository(session_factory=session_factory)
    automation_repository = AutomationRepository(session_factory=session_factory)
    publishing_repository = PublishingRepository(session_factory=session_factory)
    render_repository = RenderRepository(session_factory=session_factory)
    review_repository = ReviewRepository(session_factory=session_factory)
    voice_repository = VoiceRepository(session_factory=session_factory)
    voice_profile_repository = VoiceProfileRepository(session_factory=session_factory)
    subtitle_repository = SubtitleRepository(session_factory=session_factory)
    timeline_repository = TimelineRepository(session_factory=session_factory)

    settings_service = SettingsService(
        runtime_config=runtime_config,
        repository=settings_repository,
        on_settings_updated=lambda settings: configure_logging(
            Path(settings.paths.logDir), settings.logging.level
        ),
        task_manager=task_manager,
    )
    dashboard_service = DashboardService(dashboard_repository)
    ai_capability_service = BroadcastingAICapabilityService(
        ai_capability_repository,
        secret_store,
    )
    ai_text_generation_service = AITextGenerationService(
        ai_capability_service,
        ai_job_repository,
    )
    script_service = ScriptService(
        dashboard_service,
        script_repository,
        ai_job_repository,
        ai_text_generation_service,
        prompt_template_repository,
    )
    storyboard_service = StoryboardService(
        dashboard_service,
        storyboard_repository,
        ai_job_repository,
        ai_text_generation_service,
        script_service,
    )
    prompt_template_service = PromptTemplateService(prompt_template_repository)
    video_deconstruction_service = VideoDeconstructionService(
        imported_video_repository=imported_video_repository,
        stage_repository=video_deconstruction_repository,
        task_manager=task_manager,
    )
    video_import_service = VideoImportService(
        repository=imported_video_repository,
        stage_repository=video_deconstruction_repository,
        task_manager=task_manager,
    )
    asset_service = AssetService(asset_repository, task_manager=task_manager)
    account_service = AccountService(
        account_repository,
        binding_repository=device_workspace_repository,
    )
    device_workspace_service = DeviceWorkspaceService(device_workspace_repository)
    automation_service = AutomationService(automation_repository)
    publishing_service = PublishingService(publishing_repository)
    render_service = RenderService(render_repository)
    review_service = ReviewService(
        review_repository,
        dashboard_repository=dashboard_repository,
        script_repository=script_repository,
        storyboard_repository=storyboard_repository,
    )
    voice_service = VoiceService(
        voice_repository,
        profile_repository=voice_profile_repository,
        task_manager=task_manager,
    )
    subtitle_service = SubtitleService(subtitle_repository)
    workspace_service = WorkspaceService(timeline_repository)
    search_service = SearchService(
        session_factory=session_factory,
        task_manager=task_manager,
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
            'http://127.0.0.1:1420',
            'http://localhost:1420',
            'tauri://localhost',
            'http://tauri.localhost',
        ],
        allow_methods=['*'],
        allow_headers=['*'],
    )
    app.state.runtime_config = runtime_config
    app.state.secret_store = secret_store
    app.state.runtime_engine = engine
    app.state.session_factory = session_factory
    app.state.settings_repository = settings_repository
    app.state.license_repository = license_repository
    app.state.imported_video_repository = imported_video_repository
    app.state.prompt_template_repository = prompt_template_repository
    app.state.video_deconstruction_repository = video_deconstruction_repository
    app.state.dashboard_repository = dashboard_repository
    app.state.ai_capability_repository = ai_capability_repository
    app.state.ai_job_repository = ai_job_repository
    app.state.script_repository = script_repository
    app.state.storyboard_repository = storyboard_repository
    app.state.asset_repository = asset_repository
    app.state.account_repository = account_repository
    app.state.device_workspace_repository = device_workspace_repository
    app.state.automation_repository = automation_repository
    app.state.publishing_repository = publishing_repository
    app.state.render_repository = render_repository
    app.state.review_repository = review_repository
    app.state.voice_repository = voice_repository
    app.state.voice_profile_repository = voice_profile_repository
    app.state.subtitle_repository = subtitle_repository
    app.state.timeline_repository = timeline_repository
    app.state.license_service = license_service
    app.state.settings_service = settings_service
    app.state.dashboard_service = dashboard_service
    app.state.ai_capability_service = ai_capability_service
    app.state.ai_text_generation_service = ai_text_generation_service
    app.state.script_service = script_service
    app.state.storyboard_service = storyboard_service
    app.state.prompt_template_service = prompt_template_service
    app.state.video_deconstruction_service = video_deconstruction_service
    app.state.asset_service = asset_service
    app.state.account_service = account_service
    app.state.device_workspace_service = device_workspace_service
    app.state.automation_service = automation_service
    app.state.publishing_service = publishing_service
    app.state.render_service = render_service
    app.state.review_service = review_service
    app.state.voice_service = voice_service
    app.state.subtitle_service = subtitle_service
    app.state.workspace_service = workspace_service
    app.state.video_import_service = video_import_service
    app.state.search_service = search_service
    app.state.task_manager = task_manager

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
                error_code=ErrorCodes.REQUEST_VALIDATION_FAILED,
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

    app.include_router(accounts_router)
    app.include_router(ai_capabilities_router)
    app.include_router(ai_providers_router)
    app.include_router(assets_router)
    app.include_router(automation_router)
    app.include_router(bootstrap_router)
    app.include_router(dashboard_router)
    app.include_router(device_workspaces_router)
    app.include_router(license_router)
    app.include_router(prompt_templates_router)
    app.include_router(publishing_router)
    app.include_router(renders_router)
    app.include_router(review_router)
    app.include_router(search_router)
    app.include_router(scripts_router)
    app.include_router(settings_router)
    app.include_router(storyboards_router)
    app.include_router(subtitles_router)
    app.include_router(tasks_router)
    app.include_router(video_deconstruction_router)
    app.include_router(voice_router)
    app.include_router(workspace_router)
    app.include_router(ws_router)
    log_event(
        'system',
        'runtime.started',
        context={
            'mode': current_settings.runtime.mode,
            'databasePath': str(runtime_config.database_path),
        },
    )
    return app