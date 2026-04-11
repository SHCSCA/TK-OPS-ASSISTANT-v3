from __future__ import annotations

from fastapi import FastAPI

from api.routes import settings_router
from app.config import load_runtime_config
from app.logging import configure_logging


def create_app() -> FastAPI:
    configure_logging()

    app = FastAPI(
        title="TK-OPS Runtime",
        summary="TK-OPS M0 local runtime",
        version=load_runtime_config().version,
    )
    app.state.runtime_config = load_runtime_config()
    app.include_router(settings_router)
    return app
