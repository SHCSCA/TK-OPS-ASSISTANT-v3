from __future__ import annotations

from fastapi import APIRouter, Query, Request

from schemas.envelope import ok_response
from schemas.settings import AppSettingsUpdateInput
from services.settings_service import SettingsService

router = APIRouter(prefix="/api/settings", tags=["settings"])


def get_settings_service(request: Request) -> SettingsService:
    settings_service = request.app.state.settings_service
    assert isinstance(settings_service, SettingsService)
    return settings_service


@router.get("/health")
def get_runtime_health(request: Request) -> dict[str, object]:
    return ok_response(
        get_settings_service(request).get_health(
            request_id=getattr(request.state, "request_id", None),
        )
    )


@router.get("/config")
def get_runtime_config(request: Request) -> dict[str, object]:
    settings = get_settings_service(request).get_settings()
    return ok_response(settings.model_dump(mode="json"))


@router.put("/config")
def update_runtime_config(
    payload: AppSettingsUpdateInput,
    request: Request,
) -> dict[str, object]:
    settings = get_settings_service(request).update_settings(
        payload,
        request_id=getattr(request.state, "request_id", None),
    )
    return ok_response(settings.model_dump(mode="json"))


@router.get("/diagnostics")
def get_runtime_diagnostics(request: Request) -> dict[str, object]:
    diagnostics = get_settings_service(request).get_diagnostics()
    return ok_response(diagnostics.model_dump(mode="json"))


@router.get("/logs")
def get_runtime_logs(
    request: Request,
    kind: str | None = None,
    since: str | None = None,
    level: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
) -> dict[str, object]:
    logs = get_settings_service(request).get_runtime_logs(
        kind=kind,
        since=since,
        level=level,
        limit=limit,
    )
    return ok_response(logs.model_dump(mode="json"))


@router.post("/diagnostics/export")
def export_runtime_diagnostics(
    request: Request,
) -> dict[str, object]:
    bundle = get_settings_service(request).export_diagnostics_bundle(
        request_id=getattr(request.state, "request_id", None),
    )
    return ok_response(bundle.model_dump(mode="json"))
