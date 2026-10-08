from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session, sessionmaker

from repositories.account_configuration_v1_repository import (
    AccountConfigurationV1Repository,
)
from repositories.account_connection_v1_repository import (
    AccountConnectionV1Repository,
)
from repositories.account_repository import AccountRepository
from repositories.account_workspace_v1_repository import (
    AccountWorkspaceV1Repository,
)
from repositories.ai_capability_repository import AICapabilityRepository
from repositories.ai_configuration_v1 import AIConfigurationV1Repository
from repositories.ai_execution_v1 import AIExecutionV1Repository
from repositories.ai_job_repository import AIJobRepository
from repositories.asset_repository import AssetRepository
from repositories.automation_repository import AutomationRepository
from repositories.dashboard_repository import DashboardRepository
from repositories.device_workspace_repository import DeviceWorkspaceRepository
from repositories.imported_video_repository import ImportedVideoRepository
from repositories.knowledge_v1_repository import KnowledgeV1Repository
from repositories.knowledge_asset_v1_repository import (
    KnowledgeAssetV1Repository,
)
from repositories.license_repository import LicenseRepository
from repositories.mutation_idempotency_repository import (
    MutationIdempotencyRepository,
)
from repositories.prompt_template_repository import PromptTemplateRepository
from repositories.publishing_repository import PublishingRepository
from repositories.render_repository import RenderRepository
from repositories.review_repository import ReviewRepository
from repositories.runtime_event_repository import RuntimeEventRepository
from repositories.runtime_task_repository import RuntimeTaskRepository
from repositories.script_repository import ScriptRepository
from repositories.storyboard_repository import StoryboardRepository
from repositories.subtitle_repository import SubtitleRepository
from repositories.system_config_repository import SystemConfigRepository
from repositories.timeline_repository import TimelineRepository
from repositories.video_deconstruction_repository import (
    VideoDeconstructionRepository,
)
from repositories.voice_profile_repository import VoiceProfileRepository
from repositories.voice_repository import VoiceRepository


@dataclass(frozen=True, slots=True)
class RuntimeRepositories:
    settings: SystemConfigRepository
    license: LicenseRepository
    imported_video: ImportedVideoRepository
    prompt_template: PromptTemplateRepository
    video_deconstruction: VideoDeconstructionRepository
    dashboard: DashboardRepository
    ai_capability: AICapabilityRepository
    ai_configuration_v1: AIConfigurationV1Repository
    ai_execution_v1: AIExecutionV1Repository
    ai_job: AIJobRepository
    script: ScriptRepository
    storyboard: StoryboardRepository
    asset: AssetRepository
    account: AccountRepository
    account_workspace_v1: AccountWorkspaceV1Repository
    account_connection_v1: AccountConnectionV1Repository
    account_configuration_v1: AccountConfigurationV1Repository
    knowledge_v1: KnowledgeV1Repository
    knowledge_asset_v1: KnowledgeAssetV1Repository
    mutation_idempotency: MutationIdempotencyRepository
    device_workspace: DeviceWorkspaceRepository
    automation: AutomationRepository
    publishing: PublishingRepository
    render: RenderRepository
    review: ReviewRepository
    voice: VoiceRepository
    voice_profile: VoiceProfileRepository
    subtitle: SubtitleRepository
    timeline: TimelineRepository
    runtime_task: RuntimeTaskRepository
    runtime_event: RuntimeEventRepository


def build_runtime_repositories(
    session_factory: sessionmaker[Session],
) -> RuntimeRepositories:
    return RuntimeRepositories(
        settings=SystemConfigRepository(session_factory=session_factory),
        license=LicenseRepository(session_factory=session_factory),
        imported_video=ImportedVideoRepository(
            session_factory=session_factory
        ),
        prompt_template=PromptTemplateRepository(
            session_factory=session_factory
        ),
        video_deconstruction=VideoDeconstructionRepository(
            session_factory=session_factory
        ),
        dashboard=DashboardRepository(session_factory=session_factory),
        ai_capability=AICapabilityRepository(
            session_factory=session_factory
        ),
        ai_configuration_v1=AIConfigurationV1Repository(),
        ai_execution_v1=AIExecutionV1Repository(),
        ai_job=AIJobRepository(session_factory=session_factory),
        script=ScriptRepository(session_factory=session_factory),
        storyboard=StoryboardRepository(session_factory=session_factory),
        asset=AssetRepository(session_factory=session_factory),
        account=AccountRepository(session_factory=session_factory),
        account_workspace_v1=AccountWorkspaceV1Repository(),
        account_connection_v1=AccountConnectionV1Repository(),
        account_configuration_v1=AccountConfigurationV1Repository(),
        knowledge_v1=KnowledgeV1Repository(),
        knowledge_asset_v1=KnowledgeAssetV1Repository(),
        mutation_idempotency=MutationIdempotencyRepository(),
        device_workspace=DeviceWorkspaceRepository(
            session_factory=session_factory
        ),
        automation=AutomationRepository(session_factory=session_factory),
        publishing=PublishingRepository(session_factory=session_factory),
        render=RenderRepository(session_factory=session_factory),
        review=ReviewRepository(session_factory=session_factory),
        voice=VoiceRepository(session_factory=session_factory),
        voice_profile=VoiceProfileRepository(
            session_factory=session_factory
        ),
        subtitle=SubtitleRepository(session_factory=session_factory),
        timeline=TimelineRepository(session_factory=session_factory),
        runtime_task=RuntimeTaskRepository(
            session_factory=session_factory
        ),
        runtime_event=RuntimeEventRepository(
            session_factory=session_factory
        ),
    )
