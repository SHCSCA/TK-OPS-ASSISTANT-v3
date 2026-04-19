from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request

from schemas.envelope import ok_response
from schemas.license import LicenseActivateInput

router = APIRouter(prefix="/api/license", tags=["license"])
log = logging.getLogger(__name__)


def get_license_service(request: Request):
    license_service = getattr(request.app.state, "license_service", None)
    if license_service is None:
        import_error = getattr(request.app.state, "license_import_error", None)
        if import_error:
            log.error("许可证服务依赖未就绪: %s", import_error)
        raise HTTPException(
            status_code=503,
            detail="许可证服务暂不可用，请检查运行时依赖与授权配置",
        )
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
