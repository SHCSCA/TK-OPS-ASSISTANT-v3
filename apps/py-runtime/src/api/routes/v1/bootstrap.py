from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status

from api.dependencies.license_guard import require_active_license
from api.dependencies.request_context import RequestContext, get_request_context
from api.dependencies.request_origin_guard import require_request_origin
from api.dependencies.runtime_session_guard import require_runtime_session
from errors import DomainError, ErrorCode, FieldError
from schemas.v1.bootstrap import (
    DirectoryInitializationInput,
    LicenseActivationInput,
    SelfCheckInput,
)
from schemas.v1.envelope import ok_response
from services.bootstrap_v1 import BootstrapV1Service

router = APIRouter(
    prefix="/api/v1/bootstrap",
    tags=["v1-bootstrap"],
    dependencies=[
        Depends(require_request_origin),
        Depends(require_runtime_session),
    ],
)


@router.get("/status")
def get_bootstrap_status(
    request: Request,
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = _service(request).get_status(
        request_id=context.request_id,
        operation_id=context.operation_id,
    )
    return ok_response(result.model_dump(mode="json"))


@router.get("/license")
def get_license_status(
    request: Request,
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = _service(request).get_license_status(
        request_id=context.request_id,
        operation_id=context.operation_id,
    )
    return ok_response(result.model_dump(mode="json"))


@router.post("/license/activate")
def activate_license(
    payload: LicenseActivationInput,
    request: Request,
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    idempotency_key = _require_idempotency_key(context)
    result = _service(request).activate_license(
        license_key=payload.licenseKey,
        machine_code=payload.machineCode,
        idempotency_key=idempotency_key,
        request_id=context.request_id,
        operation_id=context.operation_id,
    )
    return ok_response(
        result.model_dump(mode="json"),
        meta={
            "revision": result.revision,
            "invalidations": ["bootstrap"],
        },
    )


@router.post(
    "/directories/initialize",
    dependencies=[Depends(require_active_license)],
)
def initialize_directories(
    payload: DirectoryInitializationInput,
    request: Request,
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    idempotency_key = _require_idempotency_key(context)
    result = _service(request).initialize_directories(
        workspace_root_ref=payload.workspaceRootRef,
        idempotency_key=idempotency_key,
    )
    return ok_response(
        result.model_dump(mode="json"),
        meta={
            "revision": result.revision,
            "invalidations": ["bootstrap"],
        },
    )


@router.post(
    "/self-checks",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_active_license)],
)
async def accept_self_checks(
    payload: SelfCheckInput,
    request: Request,
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = await _service(request).accept_self_checks(
        checks=payload.checks,
        idempotency_key=_require_idempotency_key(context),
        request_id=context.request_id,
        operation_id=context.operation_id,
    )
    return ok_response(
        result.model_dump(mode="json"),
        meta={"invalidations": ["system:tasks"]},
    )


def _service(request: Request) -> BootstrapV1Service:
    direct_service = getattr(request.app.state, "bootstrap_v1_service", None)
    if isinstance(direct_service, BootstrapV1Service):
        return direct_service

    container = getattr(request.app.state, "runtime_container", None)
    container_service = getattr(
        getattr(container, "services", None),
        "bootstrap_v1",
        None,
    )
    if isinstance(container_service, BootstrapV1Service):
        return container_service

    raise DomainError(
        ErrorCode.RUNTIME_NOT_READY,
        "Bootstrap 服务尚未就绪",
        status_code=503,
        loggable=True,
        log_context={"service": "bootstrap_v1"},
    )


def _require_idempotency_key(context: RequestContext) -> str:
    if context.idempotency_key is not None:
        return context.idempotency_key
    raise DomainError(
        ErrorCode.REQUEST_VALIDATION_FAILED,
        "写操作必须提供 Idempotency-Key",
        status_code=422,
        field_errors=[
            FieldError(
                field="Idempotency-Key",
                code="required",
                message="必须提供幂等键",
            )
        ],
    )
