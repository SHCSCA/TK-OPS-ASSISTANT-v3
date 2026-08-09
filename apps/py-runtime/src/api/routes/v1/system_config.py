from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Request

from api.dependencies.license_guard import require_active_license
from api.dependencies.request_context import RequestContext, get_request_context
from errors import DomainError, ErrorCode
from schemas.v1.envelope import ok_response
from schemas.v1.system import SystemConfigPatchInput
from services.config import ConfigBusService

router = APIRouter(
    prefix="/api/v1/system/config",
    tags=["v1-system-config"],
    dependencies=[Depends(require_active_license)],
)


def _service(request: Request) -> ConfigBusService:
    service = getattr(request.app.state, "config_bus_service", None)
    if isinstance(service, ConfigBusService):
        return service
    container = getattr(request.app.state, "runtime_container", None)
    service = getattr(getattr(container, "services", None), "config_bus", None)
    if isinstance(service, ConfigBusService):
        return service
    raise DomainError(
        ErrorCode.RUNTIME_NOT_READY,
        "系统配置服务尚未就绪",
        status_code=503,
        loggable=True,
    )


@router.get("")
def get_system_config(
    request: Request,
    prefix: Annotated[str | None, Query(max_length=128)] = None,
    _: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    snapshot = _service(request).get(prefix=prefix)
    return ok_response(
        snapshot.to_dict(),
        meta={"revision": snapshot.revision, "invalidations": []},
    )


@router.patch("")
def patch_system_config(
    payload: SystemConfigPatchInput,
    request: Request,
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    expected_revision = _parse_if_match(if_match)
    snapshot = _service(request).update(
        payload.values,
        expected_revision=expected_revision,
        request_id=context.request_id,
        operation_id=context.operation_id,
    )
    restart_required = bool(
        set(payload.values).intersection(snapshot.restart_required_keys)
    )
    meta: dict[str, object] = {
        "revision": snapshot.revision,
        "invalidations": ["system-config"],
        "restartRequired": restart_required,
    }
    if snapshot.warnings:
        meta["warnings"] = list(snapshot.warnings)
    return ok_response(
        snapshot.to_dict(),
        meta=meta,
    )


def _parse_if_match(raw_value: str | None) -> int:
    if raw_value is None:
        raise DomainError(
            ErrorCode.CONFIG_REVISION_CONFLICT,
            "缺少配置修订号，请重新加载后再试",
            status_code=412,
        )
    normalized = raw_value.strip().strip('"')
    if not normalized.isdigit():
        raise DomainError(
            ErrorCode.REQUEST_VALIDATION_FAILED,
            "配置修订号格式无效",
            status_code=422,
        )
    return int(normalized)
