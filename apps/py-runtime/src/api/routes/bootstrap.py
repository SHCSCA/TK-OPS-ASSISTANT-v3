from __future__ import annotations

from fastapi import APIRouter, Request

from schemas.bootstrap import (
    BootstrapDirectoryReportDto,
    BootstrapReadinessReportDto,
    RuntimeSelfCheckReportDto,
)
from schemas.envelope import ok_response
from services.bootstrap_service import BootstrapService

router = APIRouter(prefix="/api/bootstrap", tags=["bootstrap"])


def _svc(request: Request) -> BootstrapService:
    return request.app.state.bootstrap_service  # type: ignore[no-any-return]


@router.post("/initialize-directories")
def initialize_directories(request: Request) -> dict[str, object]:
    report = _svc(request).initialize_directories()
    assert isinstance(report, BootstrapDirectoryReportDto)
    return ok_response(report.model_dump(mode="json"))


@router.post("/runtime-selfcheck")
def runtime_selfcheck(request: Request) -> dict[str, object]:
    report = _svc(request).runtime_selfcheck()
    assert isinstance(report, RuntimeSelfCheckReportDto)
    return ok_response(report.model_dump(mode="json"))


@router.get("/readiness")
def bootstrap_readiness(request: Request) -> dict[str, object]:
    report = _svc(request).get_readiness()
    assert isinstance(report, BootstrapReadinessReportDto)
    return ok_response(report.model_dump(mode="json"))

