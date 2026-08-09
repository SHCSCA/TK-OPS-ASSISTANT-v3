from __future__ import annotations

from domain.models.account import Account, AccountGroup, AccountGroupMember
from domain.models.account_configuration import (
    AccountConfigCopyRun,
    AccountPublishDefaults,
    BrandKit,
    PositioningProfile,
)
from domain.models.account_connection import AccountConnection
from domain.models.account_login_session import AccountLoginSession
from domain.models.ai_capability import (
    AICapabilityConfig,
    AIProviderHealth,
    AIProviderModel,
    AIProviderSetting,
)
from domain.models.ai_configuration_v1 import (
    AccountAIRecipe,
    CapabilityRoute,
    CompositionTemplateProfile,
    ModelCapability,
    ModelProfile,
    PromptProfile,
    ProviderProfile,
)
from domain.models.ai_job import AIJobRecord
from domain.models.asset import Asset, AssetGroup, AssetReference
from domain.models.automation import AutomationTask, AutomationTaskRun
from domain.models.base import Base, generate_uuid
from domain.models.device_workspace import (
    BrowserInstance,
    DeviceWorkspace,
    DeviceWorkspaceLog,
    ExecutionBinding,
)
from domain.models.imported_video import ImportedVideo
from domain.models.knowledge import (
    AccountKnowledgeBase,
    KnowledgeSnapshot,
    KnowledgeSource,
)
from domain.models.license import LicenseGrant
from domain.models.magic_cut import MagicCutSuggestionDraft
from domain.models.mutation_idempotency import RuntimeMutationIdempotency
from domain.models.project import Project
from domain.models.prompt_template import PromptTemplate
from domain.models.publishing import PublishPlan, PublishReceipt
from domain.models.render import ExportProfile, RenderTask
from domain.models.review import ReviewSummary
from domain.models.script import ScriptVersion
from domain.models.storyboard import StoryboardVersion
from domain.models.system_config import SessionContext, SystemConfig
from domain.models.timeline import SubtitleTrack, Timeline, VoiceTrack
from domain.models.video_deconstruction import (
    VideoDeconstructionArtifact,
    VideoStageRun,
    VideoTranscript,
)
from domain.models.voice_profile import VoiceProfile

__all__ = [
    'Account',
    'AccountConfigCopyRun',
    'AccountConnection',
    'AccountGroup',
    'AccountGroupMember',
    'AccountAIRecipe',
    'AccountKnowledgeBase',
    'AccountLoginSession',
    'AccountPublishDefaults',
    'AICapabilityConfig',
    'AIProviderHealth',
    'AIProviderModel',
    'AIJobRecord',
    'AIProviderSetting',
    'Asset',
    'AssetGroup',
    'AssetReference',
    'AutomationTask',
    'AutomationTaskRun',
    'Base',
    'BrandKit',
    'BrowserInstance',
    'CapabilityRoute',
    'CompositionTemplateProfile',
    'DeviceWorkspace',
    'DeviceWorkspaceLog',
    'ExecutionBinding',
    'ExportProfile',
    'ImportedVideo',
    'LicenseGrant',
    'MagicCutSuggestionDraft',
    'ModelCapability',
    'ModelProfile',
    'KnowledgeSnapshot',
    'KnowledgeSource',
    'PositioningProfile',
    'Project',
    'PromptTemplate',
    'PromptProfile',
    'ProviderProfile',
    'PublishPlan',
    'PublishReceipt',
    'RenderTask',
    'ReviewSummary',
    'RuntimeMutationIdempotency',
    'ScriptVersion',
    'SessionContext',
    'StoryboardVersion',
    'SubtitleTrack',
    'SystemConfig',
    'Timeline',
    'VideoStageRun',
    'VideoDeconstructionArtifact',
    'VideoTranscript',
    'VoiceProfile',
    'VoiceTrack',
    'generate_uuid',
]
