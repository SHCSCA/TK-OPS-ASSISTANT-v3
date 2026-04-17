from __future__ import annotations

from fastapi import APIRouter, Request

from api.routes.settings import get_settings_service
from schemas.envelope import ok_response

router = APIRouter(prefix="/api/bootstrap", tags=["bootstrap"])


@router.post("/initialize-directories")
def initialize_directories(request: Request) -> dict[str, object]:
    report = get_settings_service(request).initialize_directories(
        request_id=getattr(request.state, "request_id", None),
    )
    return ok_response(report.model_dump(mode="json"))


@router.post("/runtime-selfcheck")
def runtime_selfcheck(request: Request) -> dict[str, object]:
    report = get_settings_service(request).run_runtime_selfcheck(
        request_id=getattr(request.state, "request_id", None),
    )
    return ok_response(report.model_dump(mode="json"))
