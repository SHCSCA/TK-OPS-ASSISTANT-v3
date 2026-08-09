from __future__ import annotations

from api.routes.legacy.bootstrap import router as bootstrap_legacy_router
from api.routes.legacy.system import router as system_legacy_router
from api.routes.legacy.tasks import router as tasks_legacy_router

__all__ = [
    "bootstrap_legacy_router",
    "system_legacy_router",
    "tasks_legacy_router",
]
