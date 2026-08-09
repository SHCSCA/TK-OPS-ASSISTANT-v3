from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from ai.providers import dispatch_tts
from app.config import RuntimeConfig
from app.logging import configure_logging, log_event
from app.repository_assembly import (
    RuntimeRepositories,
    build_runtime_repositories,
)
from app.runtime_kernel import RuntimeKernel, build_runtime_kernel
from app.secret_store import SecretStore
from persistence.engine import create_session_factory
from persistence.migration import MigrationReport
from schemas.settings import AppSettingsDto
from services.account_service import AccountService
from services.accounts.assembly import (
    AccountV1Services,
    build_account_v1_services,
)
from services.accounts.login_sessions import LoginBrowserNavigationPort
from services.accounts.tiktok_session_probe import TikTokSessionProbePort
from services.ai_capability_service import AICapabilityService
from services.ai_configuration_v1 import (
    AIConfigurationV1Services,
    build_ai_configuration_v1_services,
)
from services.ai_text_generation_service import AITextGenerationService
from services.asset_service import AssetService
from services.automation_service import AutomationService
from services.bootstrap_service import BootstrapService
from services.bootstrap_v1 import (
    BootstrapV1Service,
    build_bootstrap_v1_service,
)
from services.browser_runtime import BrowserRuntime, LocalBrowserRuntime
from services.config import ConfigBusService, ConfigBusSnapshot
from services.config.event_evidence import write_config_updated_event
from services.config.projection import MigrationBootstrapProjectionWriter
from services.dashboard_service import DashboardService
from services.device_workspace_service import DeviceWorkspaceService
from services.diagnostics import RuntimeDiagnosticsService
from services.events import RuntimeEventService
from services.execution_environments import (
    ExecutionEnvironmentService,
    build_execution_environment_service,
)
from services.events.migration_evidence import record_migration_cutover_event
from services.license_activation_base import LicenseActivationUnavailableError
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
from services.task_manager import TaskManager, task_manager
from services.tasks.coordinator import TaskCoordinator
from services.video_deconstruction_service import VideoDeconstructionService
from services.video_import_service import VideoImportService
from services.video_multimodal_analysis_service import (
    VideoMultimodalAnalysisService,
)
from services.video_transcription_service import VideoTranscriptionService
from services.voice_artifact_store import VoiceArtifactStore
from services.voice_service import VoiceService
from services.workspace_assembly import WorkspaceAssemblyService
from services.workspace_service import WorkspaceService

log = logging.getLogger(__name__)

LICENSE_DEPENDENCY_UNAVAILABLE_MESSAGE = "许可证激活依赖未就绪，请检查运行时依赖与授权配置"


@dataclass(frozen=True, slots=True)
class RuntimeDependencyOverrides:
    browser_runtime: BrowserRuntime | None = None
    login_browser_runtime: LoginBrowserNavigationPort | None = None
    login_session_probe: TikTokSessionProbePort | None = None

try:
    from services.license_activation import OfflineLicenseActivationAdapter
except ModuleNotFoundError as exc:  # pragma: no cover
    LICENSE_IMPORT_ERROR: ModuleNotFoundError | None = exc
    OfflineLicenseActivationAdapter = None  # type: ignore[assignment]
else:
    LICENSE_IMPORT_ERROR = None


class UnavailableLicenseActivationAdapter:
    def __init__(self, detail: str) -> None:
        self._detail = detail

    def activate(self, activation_code: str, *, machine_code: str):
        raise LicenseActivationUnavailableError(self._detail)


@dataclass(frozen=True, slots=True)
class RuntimeServices:
    license: LicenseService
    settings: SettingsService
    config_bus: ConfigBusService
    diagnostics: RuntimeDiagnosticsService
    bootstrap: BootstrapService
    bootstrap_v1: BootstrapV1Service
    task_coordinator: TaskCoordinator
    dashboard: DashboardService
    ai_capability: AICapabilityService
    ai_configuration: AIConfigurationV1Services
    ai_text_generation: AITextGenerationService
    video_transcription: VideoTranscriptionService
    video_multimodal_analysis: VideoMultimodalAnalysisService
    prompt_template: PromptTemplateService
    script: ScriptService
    storyboard: StoryboardService
    video_deconstruction: VideoDeconstructionService
    asset: AssetService
    account: AccountService
    account_v1: AccountV1Services
    execution_environment: ExecutionEnvironmentService
    device_workspace: DeviceWorkspaceService
    automation: AutomationService
    publishing: PublishingService
    render: RenderService
    review: ReviewService
    voice_artifact_store: VoiceArtifactStore
    voice: VoiceService
    subtitle: SubtitleService
    workspace: WorkspaceService
    workspace_assembly: WorkspaceAssemblyService
    video_import: VideoImportService
    search: SearchService
    legacy_task_manager: TaskManager


@dataclass(frozen=True, slots=True)
class RuntimeContainer:
    config: RuntimeConfig
    migration_report: MigrationReport
    secret_store: SecretStore
    engine: Engine
    session_factory: sessionmaker[Session]
    repositories: RuntimeRepositories
    services: RuntimeServices
    kernel: RuntimeKernel
    current_settings: AppSettingsDto
    license_import_error: str | None


def build_runtime_container(
    *,
    runtime_config: RuntimeConfig,
    migration_report: MigrationReport,
    secret_store: SecretStore,
    engine: Engine,
    dependency_overrides: RuntimeDependencyOverrides | None = None,
) -> RuntimeContainer:
    session_factory = create_session_factory(engine)
    repositories = build_runtime_repositories(session_factory)
    services, current_settings, kernel = _build_services(
        runtime_config=runtime_config,
        migration_report=migration_report,
        secret_store=secret_store,
        session_factory=session_factory,
        repositories=repositories,
        dependency_overrides=dependency_overrides,
    )
    license_import_error = _license_import_error_text()

    configure_logging(
        Path(current_settings.paths.logDir),
        current_settings.logging.level,
    )
    log_event(
        "migration",
        "migration.ready",
        request_id=migration_report.log_id,
        context=migration_report.to_log_context(),
    )
    if license_import_error:
        log.warning("许可证服务依赖未就绪: %s", license_import_error)

    return RuntimeContainer(
        config=runtime_config,
        migration_report=migration_report,
        secret_store=secret_store,
        engine=engine,
        session_factory=session_factory,
        repositories=repositories,
        services=services,
        kernel=kernel,
        current_settings=current_settings,
        license_import_error=license_import_error,
    )


def _build_services(
    *,
    runtime_config: RuntimeConfig,
    migration_report: MigrationReport,
    secret_store: SecretStore,
    session_factory: sessionmaker[Session],
    repositories: RuntimeRepositories,
    dependency_overrides: RuntimeDependencyOverrides | None,
) -> tuple[RuntimeServices, AppSettingsDto, RuntimeKernel]:
    activation_adapter = _build_activation_adapter(runtime_config)
    license_service = LicenseService(
        runtime_config=runtime_config,
        repository=repositories.license,
        activation_adapter=activation_adapter,
        machine_code_service=MachineCodeService(
            secret_store=secret_store,
            runtime_mode=runtime_config.mode,
            allow_test_override=True,
        ),
    )
    settings_service = SettingsService(
        runtime_config=runtime_config,
        repository=repositories.settings,
        render_repository=repositories.render,
        publishing_repository=repositories.publishing,
        task_manager=task_manager,
        license_service=license_service,
    )
    bootstrap_service = BootstrapService(
        runtime_config=runtime_config,
        settings_service=settings_service,
        license_service=license_service,
        session_factory=session_factory,
    )
    dashboard_service = DashboardService(
        repositories.dashboard,
        task_manager=task_manager,
    )
    ai_capability_service = AICapabilityService(
        repositories.ai_capability,
        secret_store,
    )
    settings_service.bind_ai_capability_service(ai_capability_service)
    current_settings = settings_service.get_settings()
    browser_runtime = (
        dependency_overrides.browser_runtime
        if dependency_overrides is not None
        and dependency_overrides.browser_runtime is not None
        else LocalBrowserRuntime(
            executable_path_provider=lambda: (
                settings_service.get_settings().browser.executablePath
            )
        )
    )
    event_service_ref: list[RuntimeEventService] = []
    config_bus_service = ConfigBusService(
        repositories.settings,
        event_writer=lambda session, snapshot, changed_keys: (
            write_config_updated_event(
                session,
                snapshot,
                changed_keys,
                event_service_ref,
            )
        ),
        on_updated=lambda snapshot, changed_keys: _handle_config_updated(
            settings_service,
            snapshot,
            changed_keys,
        ),
        bootstrap_projection_writer=MigrationBootstrapProjectionWriter(
            runtime_config.data_dir
        ),
    )
    config_bus_service.sync_bootstrap_projection()
    diagnostics_service = RuntimeDiagnosticsService(
        runtime_config=runtime_config,
        migration_report=migration_report,
        log_dir=Path(current_settings.paths.logDir),
    )
    kernel = build_runtime_kernel(
        session_factory=session_factory,
        account_repository=repositories.account,
        task_repository=repositories.runtime_task,
        event_repository=repositories.runtime_event,
        config_bus_service=config_bus_service,
        diagnostics_service=diagnostics_service,
    )
    event_service_ref.append(kernel.event_service)
    record_migration_cutover_event(
        kernel.event_service,
        migration_report,
    )
    ai_configuration_services = build_ai_configuration_v1_services(
        session_factory=session_factory,
        repository=repositories.ai_configuration_v1,
        event_service=kernel.event_service,
        secret_store=secret_store,
        task_coordinator=kernel.task_coordinator,
        task_handler_registry=kernel.task_handler_registry,
        config_bus_service=config_bus_service,
        account_repository=repositories.account_workspace_v1,
        idempotency_repository=repositories.mutation_idempotency,
    )
    account_v1_services = build_account_v1_services(
        session_factory=session_factory,
        event_service=kernel.event_service,
        config_bus_service=config_bus_service,
        task_coordinator=kernel.task_coordinator,
        task_handler_registry=kernel.task_handler_registry,
        startup_reconciler_registrar=kernel.register_startup_reconciler,
        browser_runtime=browser_runtime,
        secret_store=secret_store,
        knowledge_content_root=runtime_config.data_dir / "accounts",
        account_repository=repositories.account_workspace_v1,
        connection_repository=repositories.account_connection_v1,
        configuration_repository=repositories.account_configuration_v1,
        knowledge_repository=repositories.knowledge_v1,
        idempotency_repository=repositories.mutation_idempotency,
        task_repository=repositories.runtime_task,
        ai_readiness_port=ai_configuration_services.readiness_port,
        ai_recipe_copy_port=ai_configuration_services.recipe_copy_port,
        login_browser_runtime=(
            dependency_overrides.login_browser_runtime
            if dependency_overrides is not None
            else None
        ),
        login_session_probe=(
            dependency_overrides.login_session_probe
            if dependency_overrides is not None
            else None
        ),
    )
    execution_environment_service = build_execution_environment_service(
        session_factory=session_factory,
        registry_path=(
            runtime_config.workspace_root_registry_path
            or runtime_config.data_dir.parent / "workspace-roots.v1.json"
        ),
        browser_runtime=browser_runtime,
        task_coordinator=kernel.task_coordinator,
        task_handler_registry=kernel.task_handler_registry,
        event_service=kernel.event_service,
        provision_timeout_seconds=_config_int(
            config_bus_service,
            "execution.provisionTimeoutSeconds",
        ),
        recovery_timeout_seconds=_config_int(
            config_bus_service,
            "execution.recoveryTimeoutSeconds",
        ),
    )
    bootstrap_v1_service = build_bootstrap_v1_service(
        runtime_config=runtime_config,
        license_repository=repositories.license,
        activation_adapter=activation_adapter,
        secret_store=secret_store,
        task_submitter=kernel.task_coordinator,
        event_service=kernel.event_service,
        machine_factor_timeout_seconds=_config_int(
            config_bus_service,
            "machineIdentity.factorTimeoutSeconds",
        ),
        machine_factor_retry_attempts=_config_int(
            config_bus_service,
            "machineIdentity.factorRetryAttempts",
        ),
    )
    ai_text_generation_service = AITextGenerationService(
        capability_service=ai_capability_service,
        ai_job_repository=repositories.ai_job,
    )
    video_transcription_service = VideoTranscriptionService(
        capability_service=ai_capability_service,
    )
    video_multimodal_analysis_service = VideoMultimodalAnalysisService(
        ai_text_generation_service=ai_text_generation_service,
    )
    prompt_template_service = PromptTemplateService(repositories.prompt_template)
    script_service = ScriptService(
        dashboard_service=dashboard_service,
        repository=repositories.script,
        ai_job_repository=repositories.ai_job,
        ai_text_generation_service=ai_text_generation_service,
        prompt_template_repository=repositories.prompt_template,
    )
    storyboard_service = StoryboardService(
        dashboard_service=dashboard_service,
        repository=repositories.storyboard,
        ai_job_repository=repositories.ai_job,
        ai_text_generation_service=ai_text_generation_service,
        script_service=script_service,
    )
    video_deconstruction_service = VideoDeconstructionService(
        imported_video_repository=repositories.imported_video,
        stage_repository=repositories.video_deconstruction,
        transcription_service=video_transcription_service,
        multimodal_analysis_service=video_multimodal_analysis_service,
        task_manager=task_manager,
    )
    asset_service = AssetService(
        repository=repositories.asset,
        task_manager=task_manager,
    )
    account_service = AccountService(
        repositories.account,
        binding_repository=repositories.device_workspace,
    )
    device_workspace_service = DeviceWorkspaceService(
        repositories.device_workspace,
        browser_runtime=browser_runtime,
    )
    automation_service = AutomationService(repositories.automation)
    publishing_service = PublishingService(
        repositories.publishing,
        account_repository=repositories.account,
        device_workspace_repository=repositories.device_workspace,
    )
    render_service = RenderService(
        repositories.render,
        timeline_repository=repositories.timeline,
        runtime_config=runtime_config,
    )
    review_service = ReviewService(
        repositories.review,
        dashboard_repository=repositories.dashboard,
        script_repository=repositories.script,
        storyboard_repository=repositories.storyboard,
        publishing_repository=repositories.publishing,
        ai_job_repository=repositories.ai_job,
    )
    voice_artifact_store = VoiceArtifactStore(settings_service=settings_service)
    voice_service = VoiceService(
        repository=repositories.voice,
        profile_repository=repositories.voice_profile,
        task_manager=task_manager,
        ai_capability_service=ai_capability_service,
        tts_dispatcher=dispatch_tts,
        voice_artifact_store=voice_artifact_store,
    )
    subtitle_service = SubtitleService(
        repositories.subtitle,
        voice_repository=repositories.voice,
    )
    workspace_service = WorkspaceService(
        repositories.timeline,
        asset_repository=repositories.asset,
        task_manager=task_manager,
        ai_text_generation_service=ai_text_generation_service,
    )
    workspace_assembly_service = WorkspaceAssemblyService(
        timeline_repository=repositories.timeline,
        script_repository=repositories.script,
        storyboard_repository=repositories.storyboard,
        voice_repository=repositories.voice,
        subtitle_repository=repositories.subtitle,
        workspace_service=workspace_service,
    )
    video_import_service = VideoImportService(
        repository=repositories.imported_video,
        stage_repository=repositories.video_deconstruction,
        task_manager=task_manager,
    )
    return (
        RuntimeServices(
            license=license_service,
            settings=settings_service,
            config_bus=config_bus_service,
            diagnostics=diagnostics_service,
            bootstrap=bootstrap_service,
            bootstrap_v1=bootstrap_v1_service,
            task_coordinator=kernel.task_coordinator,
            dashboard=dashboard_service,
            ai_capability=ai_capability_service,
            ai_configuration=ai_configuration_services,
            ai_text_generation=ai_text_generation_service,
            video_transcription=video_transcription_service,
            video_multimodal_analysis=video_multimodal_analysis_service,
            prompt_template=prompt_template_service,
            script=script_service,
            storyboard=storyboard_service,
            video_deconstruction=video_deconstruction_service,
            asset=asset_service,
            account=account_service,
            account_v1=account_v1_services,
            execution_environment=execution_environment_service,
            device_workspace=device_workspace_service,
            automation=automation_service,
            publishing=publishing_service,
            render=render_service,
            review=review_service,
            voice_artifact_store=voice_artifact_store,
            voice=voice_service,
            subtitle=subtitle_service,
            workspace=workspace_service,
            workspace_assembly=workspace_assembly_service,
            video_import=video_import_service,
            search=SearchService(session_factory=session_factory),
            legacy_task_manager=task_manager,
        ),
        current_settings,
        kernel,
    )


def _build_activation_adapter(runtime_config: RuntimeConfig):
    if OfflineLicenseActivationAdapter is not None:
        return OfflineLicenseActivationAdapter(
            public_key_path=runtime_config.license_public_key_path,
        )
    return UnavailableLicenseActivationAdapter(
        LICENSE_DEPENDENCY_UNAVAILABLE_MESSAGE,
    )


def _license_import_error_text() -> str | None:
    if LICENSE_IMPORT_ERROR is None:
        return None
    return f"{type(LICENSE_IMPORT_ERROR).__name__}: {LICENSE_IMPORT_ERROR}"


def _refresh_runtime_config(
    settings_service: SettingsService,
    _snapshot: ConfigBusSnapshot,
    _changed_keys: tuple[str, ...],
) -> None:
    settings = settings_service.get_settings()
    configure_logging(Path(settings.paths.logDir), settings.logging.level)


def _handle_config_updated(
    settings_service: SettingsService,
    snapshot: ConfigBusSnapshot,
    changed_keys: tuple[str, ...],
) -> None:
    _refresh_runtime_config(settings_service, snapshot, changed_keys)


def _config_int(config_bus: ConfigBusService, key: str) -> int:
    value = config_bus.get().values.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise RuntimeError(f"配置总线缺少有效整数配置：{key}")
    return value
