from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from api.dependencies.license_guard import require_active_license
from api.dependencies.request_context import RequestContext, get_request_context
from api.dependencies.resource_id import StablePathId
from errors import DomainError, ErrorCode
from schemas.v1.envelope import ok_response
from services.diagnostics import RuntimeDiagnosticsService

router = APIRouter(
    prefix="/api/v1/system",
    tags=["v1-system-diagnostics"],
    dependencies=[Depends(require_active_license)],
)


def _service(request: Request) -> RuntimeDiagnosticsService:
    service = getattr(request.app.state, "runtime_diagnostics_service", None)
    if isinstance(service, RuntimeDiagnosticsService):
        return service
    container = getattr(request.app.state, "runtime_container", None)
    service = getattr(getattr(container, "services", None), "diagnostics", None)
    if isinstance(service, RuntimeDiagnosticsService):
        return service
    raise DomainError(
        ErrorCode.RUNTIME_NOT_READY,
        "Runtime 诊断服务尚未就绪",
        status_code=503,
        loggable=True,
    )


@router.get("/diagnostics")
def get_diagnostics(
    request: Request,
    sections: Annotated[str | None, Query(max_length=128)] = None,
    _: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    diagnostics = _service(request).get_diagnostics()
    selected = _filter_sections(diagnostics, sections)
    return ok_response(selected)


@router.get("/logs/{log_id}")
def get_log_excerpt(
    log_id: StablePathId,
    request: Request,
    _: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    return ok_response(_service(request).get_safe_log_excerpt(log_id))


def _filter_sections(
    diagnostics: dict[str, object],
    raw_sections: str | None,
) -> dict[str, object]:
    if raw_sections is None or not raw_sections.strip():
        return diagnostics
    allowed = {"runtime", "database", "directories", "mediaTools", "sidecar"}
    requested = {
        section.strip()
        for section in raw_sections.split(",")
        if section.strip()
    }
    invalid = requested - allowed
    if invalid:
        raise DomainError(
            ErrorCode.REQUEST_VALIDATION_FAILED,
            "诊断分区参数无效",
            status_code=422,
        )
    return {
        key: value
        for key, value in diagnostics.items()
        if key in requested or key == "checkedAt"
    }
