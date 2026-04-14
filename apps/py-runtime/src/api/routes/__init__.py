from __future__ import annotations

from api.routes.ai_capabilities import router as ai_capabilities_router
from api.routes.dashboard import router as dashboard_router
from api.routes.license import router as license_router
from api.routes.scripts import router as scripts_router
from api.routes.settings import router as settings_router
from api.routes.storyboards import router as storyboards_router
from api.routes.video_deconstruction import router as video_deconstruction_router
from api.routes.ws import router as ws_router

__all__ = [
    'ai_capabilities_router',
    'dashboard_router',
    'license_router',
    'scripts_router',
    'settings_router',
    'storyboards_router',
    'video_deconstruction_router',
    'ws_router',
]
