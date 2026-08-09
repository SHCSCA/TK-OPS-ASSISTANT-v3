from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import FastAPI

if TYPE_CHECKING:
    from app.container import RuntimeContainer


def attach_container_state(
    app: FastAPI,
    container: RuntimeContainer,
) -> None:
    """将兼容期依赖别名集中挂载到 FastAPI 状态。"""

    app.state.runtime_container = container
    app.state.runtime_config = container.config
    app.state.migration_report = container.migration_report
    app.state.secret_store = container.secret_store
    app.state.runtime_engine = container.engine
    app.state.session_factory = container.session_factory
    app.state.license_import_error = container.license_import_error
    app.state.runtime_kernel = container.kernel

    repository_aliases = {
        "settings_repository": container.repositories.settings,
        "license_repository": container.repositories.license,
        "imported_video_repository": container.repositories.imported_video,
        "prompt_template_repository": container.repositories.prompt_template,
        "video_deconstruction_repository": (
            container.repositories.video_deconstruction
        ),
        "dashboard_repository": container.repositories.dashboard,
        "ai_capability_repository": container.repositories.ai_capability,
        "ai_configuration_v1_repository": (
            container.repositories.ai_configuration_v1
        ),
        "ai_job_repository": container.repositories.ai_job,
        "script_repository": container.repositories.script,
        "storyboard_repository": container.repositories.storyboard,
        "asset_repository": container.repositories.asset,
        "account_repository": container.repositories.account,
        "account_workspace_v1_repository": (
            container.repositories.account_workspace_v1
        ),
        "account_connection_v1_repository": (
            container.repositories.account_connection_v1
        ),
        "account_configuration_v1_repository": (
            container.repositories.account_configuration_v1
        ),
        "knowledge_v1_repository": container.repositories.knowledge_v1,
        "mutation_idempotency_repository": (
            container.repositories.mutation_idempotency
        ),
        "device_workspace_repository": (
            container.repositories.device_workspace
        ),
        "automation_repository": container.repositories.automation,
        "publishing_repository": container.repositories.publishing,
        "render_repository": container.repositories.render,
        "review_repository": container.repositories.review,
        "voice_repository": container.repositories.voice,
        "voice_profile_repository": container.repositories.voice_profile,
        "subtitle_repository": container.repositories.subtitle,
        "timeline_repository": container.repositories.timeline,
        "runtime_task_repository": container.repositories.runtime_task,
        "runtime_event_repository": container.repositories.runtime_event,
    }
    service_aliases = {
        "license_service": container.services.license,
        "settings_service": container.services.settings,
        "config_bus_service": container.services.config_bus,
        "runtime_diagnostics_service": container.services.diagnostics,
        "bootstrap_service": container.services.bootstrap,
        "bootstrap_v1_service": container.services.bootstrap_v1,
        "task_coordinator": container.services.task_coordinator,
        "runtime_event_service": container.kernel.event_service,
        "runtime_event_publisher": container.kernel.event_publisher,
        "runtime_websocket_manager": container.kernel.websocket_manager,
        "dashboard_service": container.services.dashboard,
        "ai_capability_service": container.services.ai_capability,
        "ai_configuration_v1_service": (
            container.services.ai_configuration
        ),
        "ai_text_generation_service": container.services.ai_text_generation,
        "video_transcription_service": (
            container.services.video_transcription
        ),
        "script_service": container.services.script,
        "storyboard_service": container.services.storyboard,
        "prompt_template_service": container.services.prompt_template,
        "video_deconstruction_service": (
            container.services.video_deconstruction
        ),
        "asset_service": container.services.asset,
        "account_service": container.services.account,
        "account_v1_service": container.services.account_v1,
        "account_unit_of_work": container.services.account_v1.unit_of_work,
        "account_read_model": container.services.account_v1.read_model,
        "account_command_service": container.services.account_v1.commands,
        "account_copy_service": container.services.account_v1.copy_config,
        "account_task_submission_service": container.services.account_v1.tasks,
        "account_connection_service": container.services.account_v1.connection,
        "account_positioning_service": (
            container.services.account_v1.positioning
        ),
        "account_knowledge_service": container.services.account_v1.knowledge,
        "knowledge_index_submission_service": (
            container.services.account_v1.knowledge_index
        ),
        "account_branding_service": container.services.account_v1.branding,
        "device_workspace_service": container.services.device_workspace,
        "automation_service": container.services.automation,
        "publishing_service": container.services.publishing,
        "render_service": container.services.render,
        "review_service": container.services.review,
        "voice_artifact_store": container.services.voice_artifact_store,
        "voice_service": container.services.voice,
        "subtitle_service": container.services.subtitle,
        "workspace_service": container.services.workspace,
        "workspace_assembly_service": (
            container.services.workspace_assembly
        ),
        "video_import_service": container.services.video_import,
        "task_manager": container.services.legacy_task_manager,
        "search_service": container.services.search,
    }
    for name, value in (*repository_aliases.items(), *service_aliases.items()):
        setattr(app.state, name, value)
