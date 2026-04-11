from __future__ import annotations

from fastapi import APIRouter, Request

from schemas.envelope import ok_response
from schemas.license import LicenseActivateInput
from services.license_service import LicenseService

router = APIRouter(prefix="/api/license", tags=["license"])


def get_license_service(request: Request) -> LicenseService:
    license_service = request.app.state.license_service
    assert isinstance(license_service, LicenseService)
    return license_service


@router.get("/status")
def get_license_status(request: Request) -> dict[str, object]:
    status = get_license_service(request).get_status(
        request_id=getattr(request.state, "request_id", None)
    )
    return ok_response(status.model_dump(mode="json"))


@router.post("/activate")
def activate_license(
    payload: LicenseActivateInput,
    request: Request,
) -> dict[str, object]:
    result = get_license_service(request).activate(
        payload,
        request_id=getattr(request.state, "request_id", None),
    )
    return ok_response(result.model_dump(mode="json"))
