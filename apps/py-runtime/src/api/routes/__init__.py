from __future__ import annotations

from api.routes.accounts import router as accounts_router
from api.routes.ai_capabilities import router as ai_capabilities_router
from api.routes.ai_providers import router as ai_providers_router
from api.routes.assets import router as assets_router
from api.routes.automation import router as automation_router
from api.routes.dashboard import router as dashboard_router
from api.routes.device_workspaces import router as device_workspaces_router
from api.routes.license import router as license_router
from api.routes.publishing import router as publishing_router
from api.routes.renders import router as renders_router
from api.routes.review import router as review_router
from api.routes.scripts import router as scripts_router
from api.routes.settings import router as settings_router
from api.routes.storyboards import router as storyboards_router
from api.routes.subtitles import router as subtitles_router
from api.routes.tasks import router as tasks_router
from api.routes.video_deconstruction import router as video_deconstruction_router
from api.routes.voice import router as voice_router
from api.routes.workspace import router as workspace_router
from api.routes.ws import router as ws_router

__all__ = [
    'accounts_router',
    'ai_capabilities_router',
    'ai_providers_router',
    'assets_router',
    'automation_router',
    'dashboard_router',
    'device_workspaces_router',
    'license_router',
    'publishing_router',
    'renders_router',
    'review_router',
    'scripts_router',
    'settings_router',
    'storyboards_router',
    'subtitles_router',
    'tasks_router',
    'video_deconstruction_router',
    'voice_router',
    'workspace_router',
    'ws_router',
]
