from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, Request

from api.dependencies.license_guard import require_active_license
from api.dependencies.request_context import RequestContext, get_request_context
from api.routes.legacy.access import (
    legacy_write_unsupported,
    record_legacy_api_use,
    require_legacy_access,
)
from api.routes.legacy.settings_mapper import map_legacy_settings
from app.config import RuntimeConfig
from errors import DomainError, ErrorCode
from schemas.envelope import ok_response
from schemas.settings import (
    AISettingsSection,
    AppSettingsDto,
    AppSettingsUpdateInput,
    FfmpegDiagnosticsDto,
    FfprobeDiagnosticsDto,
    MediaDiagnosticsDto,
    RuntimeDiagnosticItemDto,
    RuntimeDiagnosticsDto,
)
from services.bootstrap_v1 import BootstrapV1Service
from services.config import ConfigBusService, ConfigBusSnapshot
from services.diagnostics import RuntimeDiagnosticsService

router = APIRouter(
    prefix="/api/settings",
    tags=["legacy-system"],
    dependencies=[
        Depends(require_legacy_access),
        Depends(require_active_license),
    ],
)


@router.get("/health")
async def get_runtime_health(
    request: Request,
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    record_legacy_api_use(
        request,
        replacement=(
            "/api/v1/bootstrap/status, "
            "/api/v1/bootstrap/self-checks"
        ),
    )
    bootstrap = _bootstrap_service(request).get_status(
        request_id=context.request_id,
        operation_id=context.operation_id,
    )
    diagnostics = _diagnostics_service(request).get_diagnostics()
    checked_at = str(diagnostics["checkedAt"])
    payload: dict[str, object] = {
        "runtime": {
            "status": diagnostics["runtime"]["status"],
            "port": _runtime_port(request),
            "uptimeMs": None,
            "version": bootstrap.runtime.version,
        },
        "license": {
            "status": bootstrap.license.status,
            "expiresAt": bootstrap.license.expiresAt,
        },
        "lastSyncAt": checked_at,
        "service": diagnostics["runtime"]["status"],
        "version": bootstrap.runtime.version,
        "now": checked_at,
        "mode": diagnostics["runtime"]["mode"],
        "unavailableSections": [
            "aiProvider",
            "renderQueue",
            "publishingQueue",
        ],
    }
    list_tasks = getattr(_task_coordinator(request), "list_system_tasks", None)
    if callable(list_tasks):
        records = await list_tasks(limit=200)
        payload["taskBus"] = _task_counts(records)
    return ok_response(payload)


@router.get("/config")
def get_runtime_config(
    request: Request,
) -> dict[str, object]:
    record_legacy_api_use(
        request,
        replacement="/api/v1/system/config",
    )
    settings = _map_settings(request, _config_bus(request).get())
    return ok_response(settings.model_dump(mode="json"))


@router.put("/config")
def update_runtime_config(
    payload: AppSettingsUpdateInput,
    request: Request,
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    record_legacy_api_use(
        request,
        replacement="/api/v1/system/config",
    )
    config_bus = _config_bus(request)
    current_snapshot = config_bus.get()
    current = _map_settings(request, current_snapshot)
    _reject_migrated_sections(payload, current)
    snapshot = config_bus.update(
        {
            "logging.level": payload.logging.level,
            "media.ffprobePath": payload.media.ffprobePath,
            "media.ffmpegPath": payload.media.ffmpegPath,
            "browser.executablePath": payload.browser.executablePath,
        },
        expected_revision=current_snapshot.revision,
        request_id=context.request_id,
        operation_id=context.operation_id,
    )
    result = _map_settings(request, snapshot)
    return ok_response(result.model_dump(mode="json"))


@router.get("/diagnostics")
def get_runtime_diagnostics(
    request: Request,
) -> dict[str, object]:
    record_legacy_api_use(
        request,
        replacement="/api/v1/system/diagnostics",
    )
    diagnostics = _diagnostics_service(request).get_diagnostics()
    items = _legacy_diagnostic_items(diagnostics)
    result = RuntimeDiagnosticsDto(
        databasePath="",
        cacheDir="",
        logDir="",
        revision=_config_bus(request).get().revision,
        mode=str(diagnostics["runtime"]["mode"]),
        healthStatus=str(diagnostics["runtime"]["status"]),
        configScope="runtime_local",
        checkedAt=str(diagnostics["checkedAt"]),
        overallStatus=_overall_status(items),
        items=items,
    )
    return ok_response(result.model_dump(mode="json"))


@router.get("/diagnostics/media")
def get_runtime_media_diagnostics(
    request: Request,
) -> dict[str, object]:
    record_legacy_api_use(
        request,
        replacement="/api/v1/system/diagnostics",
    )
    diagnostics = _diagnostics_service(request).get_diagnostics()
    media_tools = diagnostics["mediaTools"]
    result = MediaDiagnosticsDto(
        ffprobe=_legacy_media_tool(media_tools["ffprobe"], probe=True),
        ffmpeg=_legacy_media_tool(media_tools["ffmpeg"], probe=False),
        checkedAt=str(diagnostics["checkedAt"]),
    )
    return ok_response(result.model_dump(mode="json"))


@router.get("/logs")
def get_runtime_logs(
    request: Request,
) -> None:
    record_legacy_api_use(
        request,
        replacement="/api/v1/system/logs/{log_id}",
    )
    legacy_write_unsupported(
        replacement="/api/v1/system/logs/{log_id}",
    )


@router.post("/diagnostics/export")
def export_runtime_diagnostics(
    request: Request,
) -> None:
    record_legacy_api_use(
        request,
        replacement="受控 Tauri 诊断导出",
    )
    legacy_write_unsupported(
        replacement="受控 Tauri 诊断导出",
    )


def _bootstrap_service(request: Request) -> BootstrapV1Service:
    service = getattr(request.app.state, "bootstrap_v1_service", None)
    if isinstance(service, BootstrapV1Service):
        return service
    container = getattr(request.app.state, "runtime_container", None)
    service = getattr(getattr(container, "services", None), "bootstrap_v1", None)
    if isinstance(service, BootstrapV1Service):
        return service
    raise _service_unavailable("bootstrap_v1")


def _diagnostics_service(request: Request) -> RuntimeDiagnosticsService:
    service = getattr(request.app.state, "runtime_diagnostics_service", None)
    if isinstance(service, RuntimeDiagnosticsService):
        return service
    container = getattr(request.app.state, "runtime_container", None)
    service = getattr(getattr(container, "services", None), "diagnostics", None)
    if isinstance(service, RuntimeDiagnosticsService):
        return service
    raise _service_unavailable("runtime_diagnostics")


def _config_bus(request: Request) -> ConfigBusService:
    service = getattr(request.app.state, "config_bus_service", None)
    if isinstance(service, ConfigBusService):
        return service
    container = getattr(request.app.state, "runtime_container", None)
    service = getattr(getattr(container, "services", None), "config_bus", None)
    if isinstance(service, ConfigBusService):
        return service
    raise _service_unavailable("config_bus")


def _map_settings(
    request: Request,
    snapshot: ConfigBusSnapshot,
) -> AppSettingsDto:
    runtime_config = getattr(request.app.state, "runtime_config", None)
    if not isinstance(runtime_config, RuntimeConfig):
        container = getattr(request.app.state, "runtime_container", None)
        runtime_config = getattr(container, "config", None)
    if not isinstance(runtime_config, RuntimeConfig):
        raise _service_unavailable("runtime_config")

    container = getattr(request.app.state, "runtime_container", None)
    current_settings = getattr(container, "current_settings", None)
    ai_settings = getattr(current_settings, "ai", None)
    if not isinstance(ai_settings, AISettingsSection):
        raise _service_unavailable("legacy_settings_ai_snapshot")

    return map_legacy_settings(
        snapshot,
        runtime_config=runtime_config,
        ai_settings=ai_settings,
    )


def _task_coordinator(request: Request) -> object:
    service = getattr(request.app.state, "task_coordinator", None)
    if service is not None:
        return service
    container = getattr(request.app.state, "runtime_container", None)
    return getattr(
        getattr(container, "services", None),
        "task_coordinator",
        object(),
    )


def _reject_migrated_sections(
    payload: AppSettingsUpdateInput,
    current: AppSettingsDto,
) -> None:
    if payload.runtime != current.runtime or payload.paths != current.paths:
        legacy_write_unsupported(
            replacement="/api/v1/system/config",
        )
    if payload.ai != current.ai:
        legacy_write_unsupported(
            replacement="/api/v1/system/providers",
        )


def _legacy_diagnostic_items(
    diagnostics: dict[str, object],
) -> list[RuntimeDiagnosticItemDto]:
    checked_at = str(diagnostics["checkedAt"])
    runtime = diagnostics["runtime"]
    database = diagnostics["database"]
    directories = diagnostics["directories"]
    media_tools = diagnostics["mediaTools"]
    return [
        _diagnostic_item(
            item_id="runtime.status",
            label="Runtime 服务",
            group="基础运行",
            status=str(runtime["status"]),
            summary=f"Runtime 状态：{runtime['status']}",
            checked_at=checked_at,
        ),
        _diagnostic_item(
            item_id="database.schema",
            label="本地数据库",
            group="基础运行",
            status=str(database["status"]),
            summary=f"Schema 修订：{database['schemaRevision']}",
            checked_at=checked_at,
        ),
        _diagnostic_item(
            item_id="directories.status",
            label="本地目录",
            group="本地资源",
            status=str(directories["status"]),
            summary=f"目录状态：{directories['status']}",
            checked_at=checked_at,
        ),
        _diagnostic_item(
            item_id="media-tools.status",
            label="媒体工具",
            group="本地资源",
            status=str(media_tools["status"]),
            summary=f"媒体工具状态：{media_tools['status']}",
            checked_at=checked_at,
        ),
    ]


def _diagnostic_item(
    *,
    item_id: str,
    label: str,
    group: str,
    status: str,
    summary: str,
    checked_at: str,
) -> RuntimeDiagnosticItemDto:
    normalized_status = (
        "ready"
        if status == "ready"
        else "failed"
        if status == "failed"
        else "warning"
    )
    return RuntimeDiagnosticItemDto(
        id=item_id,
        label=label,
        group=group,
        status=normalized_status,
        summary=summary,
        impact="该状态影响 Runtime 基础能力",
        detail=f"检查时间：{checked_at}",
        actionLabel="重新检测",
        actionTarget="settings.diagnostics.rescan",
    )


def _legacy_media_tool(
    item: dict[str, object],
    *,
    probe: bool,
) -> FfprobeDiagnosticsDto | FfmpegDiagnosticsDto:
    values = {
        "status": str(item["status"]),
        "path": None,
        "source": item.get("source"),
        "version": None,
        "errorCode": item.get("errorCode"),
        "errorMessage": None,
    }
    if probe:
        return FfprobeDiagnosticsDto(**values)
    return FfmpegDiagnosticsDto(**values)


def _overall_status(
    items: list[RuntimeDiagnosticItemDto],
) -> str:
    statuses = {item.status for item in items}
    if "failed" in statuses:
        return "failed"
    if "warning" in statuses:
        return "warning"
    return "ready"


def _task_counts(records: Sequence[object]) -> dict[str, int]:
    statuses = [_status_value(record) for record in records]
    cutoff = datetime.now(UTC) - timedelta(hours=24)
    return {
        "running": statuses.count("running"),
        "queued": statuses.count("queued"),
        "blocked": statuses.count("blocked"),
        "failed24h": sum(
            1
            for record, status in zip(records, statuses, strict=True)
            if status == "failed"
            and _parse_time(getattr(record, "updated_at", None)) >= cutoff
        ),
    }


def _status_value(record: object) -> str:
    status = getattr(record, "status", "")
    return str(getattr(status, "value", status))


def _parse_time(value: object) -> datetime:
    if not isinstance(value, str) or not value:
        return datetime.min.replace(tzinfo=UTC)
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return datetime.min.replace(tzinfo=UTC)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _runtime_port(request: Request) -> int:
    runtime_config = getattr(request.app.state, "runtime_config", None)
    expected_host = str(getattr(runtime_config, "expected_host", ""))
    try:
        return int(urlsplit(f"//{expected_host}").port or 0)
    except ValueError:
        return 0


def _service_unavailable(service: str) -> DomainError:
    return DomainError(
        ErrorCode.RUNTIME_NOT_READY,
        "Runtime 兼容服务尚未就绪",
        status_code=503,
        loggable=True,
        log_context={"service": service},
    )
