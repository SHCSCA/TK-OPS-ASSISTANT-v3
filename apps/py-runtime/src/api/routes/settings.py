from __future__ import annotations

from fastapi import APIRouter, Request

from app.config import RuntimeConfig
from schemas.envelope import ok_response
from services.settings_service import build_health_payload

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/health")
def get_runtime_health(request: Request) -> dict[str, object]:
    runtime_config = request.app.state.runtime_config
    assert isinstance(runtime_config, RuntimeConfig)
    return ok_response(build_health_payload(runtime_config))
