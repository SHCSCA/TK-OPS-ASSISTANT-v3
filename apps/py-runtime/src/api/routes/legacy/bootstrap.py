from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from fastapi import APIRouter, Depends, Request, status

from api.dependencies.license_guard import require_active_license
from api.dependencies.request_context import RequestContext, get_request_context
from api.routes.legacy.access import (
    record_legacy_api_use,
    require_legacy_access,
)
from errors import DomainError, ErrorCode
from schemas.bootstrap import (
    BootstrapActionDto,
    BootstrapBlockerDto,
    BootstrapDirectoryItemDto,
    BootstrapDirectoryReportDto,
    BootstrapReadinessItemDto,
    BootstrapReadinessReportDto,
    RuntimeSelfCheckItemDto,
    RuntimeSelfCheckReportDto,
)
from schemas.envelope import ok_response
from schemas.license import LicenseActivateInput
from schemas.v1.bootstrap import (
    BootstrapStatusDto,
    DirectoryReportDto,
    LicenseStatusDto,
    SelfCheckKey,
)
from services.bootstrap_v1 import BootstrapV1Service

router = APIRouter(
    tags=["legacy-bootstrap"],
    dependencies=[Depends(require_legacy_access)],
)


@router.get("/api/license/status")
def get_license_status(
    request: Request,
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    record_legacy_api_use(
        request,
        replacement="/api/v1/bootstrap/license",
    )
    result = _service(request).get_license_status(
        request_id=context.request_id,
        operation_id=context.operation_id,
    )
    return ok_response(_legacy_license(result))


@router.post("/api/license/activate")
def activate_license(
    payload: LicenseActivateInput,
    request: Request,
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    record_legacy_api_use(
        request,
        replacement="/api/v1/bootstrap/license/activate",
    )
    result = _service(request).activate_license(
        license_key=payload.activationCode,
        machine_code=None,
        idempotency_key=(
            context.idempotency_key
            or _stable_key("license", payload.activationCode)
        ),
        request_id=context.request_id,
        operation_id=context.operation_id,
    )
    return ok_response(_legacy_license(result))


@router.post("/api/bootstrap/initialize-directories")
def initialize_directories(
    request: Request,
    _: LicenseStatusDto = Depends(require_active_license),
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    record_legacy_api_use(
        request,
        replacement="/api/v1/bootstrap/directories/initialize",
    )
    result = _service(request).initialize_directories(
        workspace_root_ref=None,
        idempotency_key=(
            context.idempotency_key
            or _stable_key("directories", "runtime-default")
        ),
    )
    runtime_config = getattr(request.app.state, "runtime_config", None)
    database_path = getattr(runtime_config, "database_path", None)
    return ok_response(
        _legacy_directory_report(
            result,
            database_name=getattr(database_path, "name", ""),
        )
    )


@router.post(
    "/api/bootstrap/runtime-selfcheck",
    status_code=status.HTTP_202_ACCEPTED,
)
async def runtime_self_check(
    request: Request,
    _: LicenseStatusDto = Depends(require_active_license),
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    record_legacy_api_use(
        request,
        replacement="/api/v1/bootstrap/self-checks",
    )
    checks: list[SelfCheckKey] = [
        "database",
        "directories",
        "media_tools",
        "runtime",
    ]
    result = await _service(request).accept_self_checks(
        checks=checks,
        idempotency_key=(
            context.idempotency_key
            or _rolling_self_check_key()
        ),
        request_id=context.request_id,
        operation_id=context.operation_id,
    )
    checked_at = _utc_now()
    report = RuntimeSelfCheckReportDto(
        status="queued",
        runtimeVersion=_runtime_version(request),
        checkedAt=checked_at,
        items=[
            RuntimeSelfCheckItemDto(
                key="persistent-task",
                label="Runtime 自检",
                status="queued",
                detail=f"自检任务已进入持久队列：{result.taskId}",
                errorCode=None,
                checkedAt=checked_at,
            )
        ],
    )
    return ok_response(report.model_dump(mode="json"))


@router.get("/api/bootstrap/readiness")
def get_bootstrap_readiness(
    request: Request,
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    record_legacy_api_use(
        request,
        replacement="/api/v1/bootstrap/status",
    )
    result = _service(request).get_status(
        request_id=context.request_id,
        operation_id=context.operation_id,
    )
    return ok_response(
        _legacy_readiness(result).model_dump(mode="json")
    )


def _service(request: Request) -> BootstrapV1Service:
    service = getattr(request.app.state, "bootstrap_v1_service", None)
    if isinstance(service, BootstrapV1Service):
        return service
    container = getattr(request.app.state, "runtime_container", None)
    service = getattr(getattr(container, "services", None), "bootstrap_v1", None)
    if isinstance(service, BootstrapV1Service):
        return service
    raise DomainError(
        ErrorCode.RUNTIME_NOT_READY,
        "Bootstrap 服务尚未就绪",
        status_code=503,
        loggable=True,
        log_context={"service": "bootstrap_v1"},
    )


def _legacy_license(result: LicenseStatusDto) -> dict[str, object]:
    return {
        "active": result.status == "active",
        "restrictedMode": result.status != "active",
        "machineCode": result.machineCodeMasked,
        "machineBound": result.status == "active",
        "licenseType": "local_device",
        "maskedCode": result.machineCodeMasked,
        "activatedAt": result.activatedAt,
    }


def _legacy_directory_report(
    result: DirectoryReportDto,
    *,
    database_name: str,
) -> dict[str, object]:
    checked_at = _utc_now()
    report = BootstrapDirectoryReportDto(
        rootDir=result.workspaceRootDisplay,
        databasePath=database_name,
        status=result.status,
        directories=[
            BootstrapDirectoryItemDto(
                key=item.key,
                label=_directory_label(item.key),
                path="",
                exists=item.status in {"ready", "created"},
                writable=item.writable,
                status=item.status,
                message=None,
            )
            for item in result.directories
        ],
        checkedAt=checked_at,
    )
    return report.model_dump(mode="json")


def _legacy_readiness(
    result: BootstrapStatusDto,
) -> BootstrapReadinessReportDto:
    checked_at = _utc_now()
    items = [
        _readiness_item(
            key="license",
            label="设备许可证",
            ready=result.license.status == "active",
            detail=(
                "设备许可证有效"
                if result.license.status == "active"
                else "设备许可证尚未就绪"
            ),
            error_code=(
                result.license.blockingIssue.code
                if result.license.blockingIssue is not None
                else None
            ),
            checked_at=checked_at,
        ),
        _readiness_item(
            key="directories",
            label="本地目录",
            ready=result.directories.status == "ready",
            detail=f"目录状态：{result.directories.status}",
            error_code=(
                result.directories.issues[0].code
                if result.directories.issues
                else None
            ),
            checked_at=checked_at,
        ),
        _readiness_item(
            key="runtime",
            label="Runtime 服务",
            ready=result.runtime.status == "ready",
            detail=f"Runtime {result.runtime.version}",
            error_code=None,
            checked_at=checked_at,
        ),
        _readiness_item(
            key="media-tools",
            label="媒体工具",
            ready=result.mediaTools.status == "ready",
            detail=f"媒体工具状态：{result.mediaTools.status}",
            error_code=(
                result.mediaTools.issues[0]
                if result.mediaTools.issues
                else None
            ),
            checked_at=checked_at,
            blocking=False,
        ),
    ]
    blockers = [
        BootstrapBlockerDto(
            key=f"blocker-{index}",
            errorCode=issue.code,
            blockedReason=issue.message,
            affectedTarget="bootstrap",
            nextStep="打开首启向导并按提示处理",
            action=BootstrapActionDto(
                key="open-bootstrap",
                label="打开首启向导",
            ),
        )
        for index, issue in enumerate(result.blockingIssues, start=1)
    ]
    return BootstrapReadinessReportDto(
        status="ready" if result.canContinue else "blocked",
        canContinue=result.canContinue,
        checkedAt=checked_at,
        items=items,
        blockers=blockers,
    )


def _readiness_item(
    *,
    key: str,
    label: str,
    ready: bool,
    detail: str,
    error_code: str | None,
    checked_at: str,
    blocking: bool = True,
) -> BootstrapReadinessItemDto:
    return BootstrapReadinessItemDto(
        key=key,
        label=label,
        status="ready" if ready else "warning",
        detail=detail,
        errorCode=error_code,
        blockedReason=None if ready or not blocking else detail,
        affectedTarget=None if ready or not blocking else "bootstrap",
        nextStep=(
            None
            if ready or not blocking
            else "打开首启向导并按提示处理"
        ),
        action=(
            None
            if ready or not blocking
            else BootstrapActionDto(
                key="open-bootstrap",
                label="打开首启向导",
            )
        ),
        checkedAt=checked_at,
    )


def _directory_label(key: str) -> str:
    labels = {
        "data_root": "Runtime 数据",
        "projects": "项目",
        "assets": "资产",
        "renders": "渲染",
        "cache": "缓存",
        "exports": "导出",
        "logs": "日志",
        "licenses": "许可证",
    }
    return labels.get(key, key)


def _runtime_version(request: Request) -> str:
    runtime_config = getattr(request.app.state, "runtime_config", None)
    return str(getattr(runtime_config, "version", "unknown"))


def _stable_key(namespace: str, value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return f"legacy:{namespace}:{digest[:48]}"


def _rolling_self_check_key() -> str:
    minute = datetime.now(UTC).strftime("%Y%m%d%H%M")
    return _stable_key("self-check", minute)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
