from __future__ import annotations

from .license import router as license_router
from .settings import router as settings_router

__all__ = ["license_router", "settings_router"]
