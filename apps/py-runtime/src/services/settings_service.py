from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from typing import TYPE_CHECKING, Any, Callable
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import HTTPException

from app.config import RuntimeConfig
from app.logging import log_event
from repositories.publishing_repository import PublishingRepository
from repositories.render_repository import RenderRepository
from repositories.system_config_repository import StoredSystemConfig, SystemConfigRepository
from schemas.settings import (
    AppSettingsDto,
    AppSettingsUpdateInput,
    ConfigChangedEventDto,
    AIProviderHealthDto,
    DiagnosticsBundleDto,
    FfprobeDiagnosticsDto,
    LicenseHealthDto,
    MediaDiagnosticsDto,
    PublishingQueueHealthDto,
    RenderQueueHealthDto,
    RuntimeDiagnosticsDto,
    RuntimeDiagnosticItemDto,
    RuntimeHealthSnapshotDto,
    RuntimeSubsystemHealthDto,
    RuntimeLogItemDto,
    RuntimeLogPageDto,
    TaskBusHealthDto,
)
from services.ffprobe import get_ffprobe_availability
from services.license_service import LicenseService
from services.media_tool_resolver import configure_ffprobe_path
from services.task_manager import TaskManager
from services.ws_manager import ws_manager

log = logging.getLogger(__name__)

if TYPE_CHECKING:
    from services.ai_capability_service import AICapabilityService

DEFAULT_RUNTIME_PORT = 8000
MAX_RUNTIME_LOG_LIMIT = 200


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _to_datetime(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


@dataclass(frozen=True, slots=True)
class SettingsDefaults:
    runtime_mode: str
    workspace_root: str
    cache_dir: str
    export_dir: str
    log_dir: str


class SettingsService:
    def __init__(
        self,
        *,
        runtime_config: RuntimeConfig,
        repository: SystemConfigRepository,
        on_settings_updated: Callable[[AppSettingsDto], None] | None = None,
        render_repository: RenderRepository | None = None,
        publishing_repository: PublishingRepository | None = None,
        task_manager: TaskManager | None = None,
        license_service: LicenseService | None = None,
        ai_capability_service: AICapabilityService | None = None,
    ) -> None:
        self._runtime_config = runtime_config
        self._repository = repository
        self._on_settings_updated = on_settings_updated
        self._render_repository = render_repository
        self._publishing_repository = publishing_repository
        self._task_manager = task_manager
        self._license_service = license_service
        self._ai_capability_service = ai_capability_service
        self._started_at = datetime.now(UTC)

    def bind_ai_capability_service(self, service: AICapabilityService) -> None:
        self._ai_capability_service = service

    def get_settings(self) -> AppSettingsDto:
        stored = self._load_or_create()
        settings = self._to_settings_dto(stored)
        self._sync_media_tool_config(settings)
        self._ensure_runtime_directories(settings)
        return settings

    def update_settings(
        self,
        payload: AppSettingsUpdateInput,
        *,
        request_id: str | None = None,
    ) -> AppSettingsDto:
        previous = self._repository.load()
        previous_document = None if previous is None else previous.document
        document = payload.model_dump(mode="json")
        stored = self._repository.save(document)
        settings = self._to_settings_dto(stored)
        self._sync_media_tool_config(settings)
        self._ensure_runtime_directories(settings)

        if self._on_settings_updated is not None:
            self._on_settings_updated(settings)

        log_event(
            "audit",
            "settings.updated",
            request_id=request_id,
            context={"revision": settings.revision},
        )
        self._broadcast_event(
            self._build_config_changed_event(
                settings=settings,
                updated_at=stored.updated_at,
                changed_keys=self._diff_settings_keys(previous_document, document),
            )
        )
        return settings

    def get_health(self, *, request_id: str | None = None) -> RuntimeHealthSnapshotDto:
        settings = self.get_settings()
        now = _utc_now_iso()
        return RuntimeHealthSnapshotDto(
            runtime=RuntimeSubsystemHealthDto(
                status="online",
                port=DEFAULT_RUNTIME_PORT,
                uptimeMs=self._calc_uptime_ms(),
                version=self._runtime_config.version,
            ),
            aiProvider=self._build_ai_provider_health(settings),
            renderQueue=self._build_render_queue_health(),
            publishingQueue=self._build_publishing_queue_health(),
            taskBus=self._build_task_bus_health(),
            license=self._build_license_health(request_id=request_id),
            lastSyncAt=now,
            service="online",
            version=self._runtime_config.version,
            now=now,
            mode=settings.runtime.mode,
        )

    def get_diagnostics(self) -> RuntimeDiagnosticsDto:
        settings = self.get_settings()
        items = self._build_diagnostic_items(settings)
        return RuntimeDiagnosticsDto(
            databasePath=str(self._runtime_config.database_path),
            cacheDir=settings.paths.cacheDir,
            logDir=settings.paths.logDir,
            revision=settings.revision,
            mode=settings.runtime.mode,
            healthStatus="online",
            configScope=settings.scope,
            checkedAt=_utc_now_iso(),
            overallStatus=self._summarize_diagnostic_status(items),
            items=items,
        )

    def get_media_diagnostics(self) -> MediaDiagnosticsDto:
        ffprobe = get_ffprobe_availability()
        return MediaDiagnosticsDto(
            ffprobe=FfprobeDiagnosticsDto(
                status=ffprobe.status,
                path=ffprobe.path,
                source=ffprobe.source,
                version=ffprobe.version,
                errorCode=ffprobe.error_code,
                errorMessage=ffprobe.error_message,
            ),
            checkedAt=_utc_now_iso(),
        )

    def _build_diagnostic_items(self, settings: AppSettingsDto) -> list[RuntimeDiagnosticItemDto]:
        return [
            self._build_license_diagnostic_item(),
            RuntimeDiagnosticItemDto(
                id="runtime.health",
                label="Runtime 服务",
                group="基础运行",
                status="ready",
                summary="Runtime 在线。",
                impact="前端可以访问本地服务和任务状态。",
                detail=f"模式：{settings.runtime.mode}；版本：{self._runtime_config.version}",
                actionLabel="重新检测",
                actionTarget="settings.diagnostics.rescan",
            ),
            self._build_database_diagnostic_item(),
            self._build_directory_diagnostic_item(
                item_id="directory.workspace",
                label="工作目录",
                path=Path(settings.runtime.workspaceRoot),
                impact="项目工程、资产引用和本地工作区需要可写目录。",
            ),
            self._build_directory_diagnostic_item(
                item_id="directory.cache",
                label="缓存目录",
                path=Path(settings.paths.cacheDir),
                impact="AI 生成、预览和媒体处理缓存需要可写目录。",
            ),
            self._build_directory_diagnostic_item(
                item_id="directory.logs",
                label="日志目录",
                path=Path(settings.paths.logDir),
                impact="异常、任务和审计日志需要写入该目录。",
            ),
            self._build_ffprobe_diagnostic_item(),
            self._build_ai_provider_diagnostic_item(settings),
            self._build_video_transcription_diagnostic_item(),
            RuntimeDiagnosticItemDto(
                id="websocket.task_bus",
                label="WebSocket 任务通道",
                group="任务通信",
                status="ready",
                summary="任务通道已随 Runtime 初始化。",
                impact="长任务进度、配置变更和状态刷新依赖该通道。",
                detail="当前 Runtime 已注册 WebSocket 路由。",
                actionLabel="重新检测",
                actionTarget="settings.diagnostics.rescan",
            ),
        ]

    def _build_license_diagnostic_item(self) -> RuntimeDiagnosticItemDto:
        health = self._build_license_health()
        if health.status == "active":
            return RuntimeDiagnosticItemDto(
                id="license.status",
                label="许可证",
                group="授权",
                status="ready",
                summary="许可证已激活。",
                impact="可使用完整本地创作链路。",
                detail="授权状态：active",
                actionLabel="重新检测",
                actionTarget="settings.diagnostics.rescan",
            )
        return RuntimeDiagnosticItemDto(
            id="license.status",
            label="许可证",
            group="授权",
            status="warning",
            summary="许可证未激活或处于受限状态。",
            impact="部分创作、发布或自动化能力可能受限。",
            detail=f"授权状态：{health.status}",
            actionLabel="前往授权",
            actionTarget="settings.license.open",
        )

    def _build_database_diagnostic_item(self) -> RuntimeDiagnosticItemDto:
        database_path = self._runtime_config.database_path
        parent = database_path.parent
        if self._is_directory_writable(parent):
            return RuntimeDiagnosticItemDto(
                id="database.sqlite",
                label="数据库",
                group="基础运行",
                status="ready",
                summary="数据库目录可读写。",
                impact="项目、任务、配置和资产索引可正常持久化。",
                detail=str(database_path),
                actionLabel="重新检测",
                actionTarget="settings.diagnostics.rescan",
            )
        return RuntimeDiagnosticItemDto(
            id="database.sqlite",
            label="数据库",
            group="基础运行",
            status="failed",
            summary="数据库目录不可写。",
            impact="项目、任务、配置和资产索引无法可靠保存。",
            detail=str(database_path),
            actionLabel="检查目录权限",
            actionTarget="settings.paths.open",
        )

    def _build_directory_diagnostic_item(
        self,
        *,
        item_id: str,
        label: str,
        path: Path,
        impact: str,
    ) -> RuntimeDiagnosticItemDto:
        if self._is_directory_writable(path):
            return RuntimeDiagnosticItemDto(
                id=item_id,
                label=label,
                group="目录",
                status="ready",
                summary=f"{label}可读写。",
                impact=impact,
                detail=str(path),
                actionLabel="重新检测",
                actionTarget="settings.diagnostics.rescan",
            )
        return RuntimeDiagnosticItemDto(
            id=item_id,
            label=label,
            group="目录",
            status="failed",
            summary=f"{label}不可写。",
            impact=impact,
            detail=str(path),
            actionLabel="检查目录权限",
            actionTarget="settings.paths.open",
        )

    def _build_ffprobe_diagnostic_item(self) -> RuntimeDiagnosticItemDto:
        ffprobe = get_ffprobe_availability()
        if ffprobe.status == "ready":
            return RuntimeDiagnosticItemDto(
                id="media.ffprobe",
                label="FFprobe 媒体探针",
                group="媒体工具",
                status="ready",
                summary="已检测到 FFprobe。",
                impact="可解析视频时长、分辨率、编码格式等元数据。",
                detail=f"来源：{ffprobe.source}；路径：{ffprobe.path}；版本：{ffprobe.version or '未知'}",
                actionLabel="重新检测",
                actionTarget="settings.diagnostics.rescan",
            )
        return RuntimeDiagnosticItemDto(
            id="media.ffprobe",
            label="FFprobe 媒体探针",
            group="媒体工具",
            status="warning",
            summary="未检测到 FFprobe，视频元数据将使用基础降级解析。",
            impact="视频时长、分辨率、编码格式识别可能不完整。",
            detail=ffprobe.error_message,
            actionLabel="准备媒体工具",
            actionTarget="settings.media_tools.prepare",
        )

    def _build_ai_provider_diagnostic_item(self, settings: AppSettingsDto) -> RuntimeDiagnosticItemDto:
        health = self._build_ai_provider_health(settings)
        if health.status in {"ready", "configured"}:
            return RuntimeDiagnosticItemDto(
                id="ai.provider",
                label="AI Provider",
                group="AI",
                status="ready",
                summary="默认 AI Provider 已配置。",
                impact="脚本、改写、分镜和其他 AI 能力可按配置调用。",
                detail=f"Provider：{health.providerId}；模型：{settings.ai.model}",
                actionLabel="连接检查",
                actionTarget="settings.provider.check",
            )
        return RuntimeDiagnosticItemDto(
            id="ai.provider",
            label="AI Provider",
            group="AI",
            status="warning",
            summary="默认 AI Provider 尚未完成配置。",
            impact="脚本、改写、分镜和其他 AI 能力可能不可用。",
            detail=f"Provider：{health.providerId}；状态：{health.status}",
            actionLabel="配置 Provider",
            actionTarget="settings.provider.open",
        )

    def _build_video_transcription_diagnostic_item(self) -> RuntimeDiagnosticItemDto:
        if self._ai_capability_service is None:
            return RuntimeDiagnosticItemDto(
                id="ai.video_transcription",
                label="视频解析模型",
                group="AI",
                status="warning",
                summary="视频解析模型尚未接入配置总线。",
                impact="视频拆解无法调用多模态模型。",
                detail="Runtime 未绑定 AI 能力服务。",
                actionLabel="重新检测",
                actionTarget="settings.diagnostics.rescan",
            )

        try:
            capability, runtime = self._resolve_video_analysis_capability()
        except Exception as exc:
            log.exception("视频解析模型诊断失败")
            return RuntimeDiagnosticItemDto(
                id="ai.video_transcription",
                label="视频解析模型",
                group="AI",
                status="warning",
                summary="视频解析模型配置读取失败。",
                impact="视频拆解可能不可用。",
                detail=str(exc),
                actionLabel="重新检测",
                actionTarget="settings.diagnostics.rescan",
            )

        if capability is None or runtime is None:
            return RuntimeDiagnosticItemDto(
                id="ai.video_transcription",
                label="视频解析模型",
                group="AI",
                status="warning",
                summary="视频解析模型未启用。",
                impact="视频拆解会退回基础分段，无法生成画面与语音对齐结果。",
                detail="请在 AI 能力中启用素材分析，或把视频转录能力绑定到多模态文本模型。",
                actionLabel="配置视频解析模型",
                actionTarget="settings.provider.open",
            )

        if not runtime.supports_text_generation:
            return RuntimeDiagnosticItemDto(
                id="ai.video_transcription",
                label="视频解析模型",
                group="AI",
                status="warning",
                summary="视频解析模型尚未配置为多模态文本模型。",
                impact="视频拆解无法直接生成画面与语音对齐时间轴。",
                detail=f"Provider：{runtime.provider}；协议：{runtime.protocol_family}",
                actionLabel="切换视频解析模型",
                actionTarget="settings.provider.open",
            )
        if runtime.requires_secret and not runtime.api_key:
            return RuntimeDiagnosticItemDto(
                id="ai.video_transcription",
                label="视频解析模型",
                group="AI",
                status="warning",
                summary="视频解析模型尚未配置 API Key。",
                impact="视频拆解无法调用远端多模态模型。",
                detail=f"Provider：{runtime.provider}；模型：{capability.model}",
                actionLabel="配置视频解析模型",
                actionTarget="settings.provider.open",
            )
        if runtime.base_url.strip() == "":
            return RuntimeDiagnosticItemDto(
                id="ai.video_transcription",
                label="视频解析模型",
                group="AI",
                status="warning",
                summary="视频解析模型尚未配置 Base URL。",
                impact="视频拆解无法调用远端多模态模型。",
                detail=f"Provider：{runtime.provider}；模型：{capability.model}",
                actionLabel="配置视频解析模型",
                actionTarget="settings.provider.open",
            )
        return RuntimeDiagnosticItemDto(
            id="ai.video_transcription",
            label="视频解析模型",
            group="AI",
            status="ready",
            summary="视频解析模型已配置。",
            impact="视频拆解可直接生成画面、语音与内容结构。",
            detail=f"能力：{capability.capabilityId}；Provider：{runtime.provider}；模型：{capability.model}",
            actionLabel="重新检测",
            actionTarget="settings.diagnostics.rescan",
        )

    def _resolve_video_analysis_capability(self):
        assert self._ai_capability_service is not None
        candidates = []
        for capability_id in ("asset_analysis", "video_transcription"):
            capability = self._ai_capability_service.get_capability(capability_id)
            if not capability.enabled:
                continue
            runtime = self._ai_capability_service.get_provider_runtime_config(capability.provider)
            candidates.append((capability, runtime))
            if runtime.supports_text_generation:
                return capability, runtime
        if candidates:
            return candidates[0]
        return None, None

    def _summarize_diagnostic_status(
        self,
        items: list[RuntimeDiagnosticItemDto],
    ) -> str:
        if any(item.status == "failed" for item in items):
            return "failed"
        if any(item.status == "warning" for item in items):
            return "warning"
        return "ready"

    def _is_directory_writable(self, path: Path) -> bool:
        try:
            path.mkdir(parents=True, exist_ok=True)
            probe = path / ".tkops-write-test"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return True
        except Exception:
            log.exception("目录写入检测失败: %s", path)
            return False

    def _build_config_changed_event(
        self,
        *,
        settings: AppSettingsDto,
        updated_at: str,
        changed_keys: list[str],
    ) -> dict[str, object]:
        return ConfigChangedEventDto(
            scope=settings.scope,
            revision=settings.revision,
            updatedAt=updated_at,
            changedKeys=changed_keys,
        ).model_dump(mode="json")

    def _broadcast_event(self, event: dict[str, object]) -> None:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(ws_manager.broadcast(event))
        else:
            asyncio.create_task(ws_manager.broadcast(event))

    def _diff_settings_keys(
        self,
        previous: dict[str, Any] | None,
        current: dict[str, Any],
    ) -> list[str]:
        keys = ("runtime", "paths", "logging", "ai", "media")
        if previous is None:
            return list(keys)
        return [key for key in keys if previous.get(key) != current.get(key)]

    def get_runtime_logs(
        self,
        *,
        kind: str | None = None,
        since: str | None = None,
        level: str | None = None,
        limit: int = 50,
    ) -> RuntimeLogPageDto:
        settings = self.get_settings()
        log_path = Path(settings.paths.logDir) / "runtime.jsonl"
        limit_value = max(1, min(limit, MAX_RUNTIME_LOG_LIMIT))
        since_dt = self._parse_since(since)

        items = self._read_runtime_log_items(log_path)
        filtered = self._filter_runtime_log_items(
            items,
            kind=kind,
            since_dt=since_dt,
            level=level,
        )
        filtered = sorted(filtered, key=lambda item: item.timestamp, reverse=True)

        page = filtered[:limit_value]
        next_cursor: str | None = None
        if len(filtered) > len(page):
            next_cursor = page[-1].timestamp

        return RuntimeLogPageDto(items=page, nextCursor=next_cursor)

    def export_diagnostics_bundle(
        self,
        *,
        request_id: str | None = None,
    ) -> DiagnosticsBundleDto:
        now = _utc_now_iso()
        settings = self.get_settings()
        logs_path = Path(settings.paths.logDir) / "runtime.jsonl"
        bundle_dir = Path(settings.paths.logDir) / "diagnostics"
        bundle_dir.mkdir(parents=True, exist_ok=True)

        bundle_path = bundle_dir / f"runtime-diagnostics-{now.replace(':', '-')}.zip"
        entries: list[str] = ["settings.json", "health.json", "diagnostics.json"]

        try:
            health = self.get_health()
            diagnostics = self.get_diagnostics()
            with ZipFile(bundle_path, "w", compression=ZIP_DEFLATED) as archive:
                archive.writestr(
                    "settings.json",
                    json.dumps(settings.model_dump(mode="json"), ensure_ascii=False),
                )
                archive.writestr(
                    "health.json",
                    json.dumps(health.model_dump(mode="json"), ensure_ascii=False),
                )
                archive.writestr(
                    "diagnostics.json",
                    json.dumps(diagnostics.model_dump(mode="json"), ensure_ascii=False),
                )
                if logs_path.exists():
                    archive.write(logs_path, arcname="runtime.jsonl")
                    entries.append("runtime.jsonl")

            log_event(
                "audit",
                "settings.diagnostics_exported",
                request_id=request_id,
                context={
                    "bundlePath": str(bundle_path),
                    "entries": entries,
                },
            )
        except Exception as exc:  # noqa: BLE001
            log.exception("Failed to export diagnostics bundle")
            raise HTTPException(status_code=500, detail="diagnostics export failed") from exc

        return DiagnosticsBundleDto(bundlePath=str(bundle_path), createdAt=now, entries=entries)

    def _build_ai_provider_health(self, settings: AppSettingsDto) -> AIProviderHealthDto:
        provider = settings.ai.provider.strip()
        model_name = (settings.ai.model or "").strip()
        if not provider or not model_name:
            return AIProviderHealthDto(
                status="not_configured",
                latencyMs=None,
                providerId=provider or "none",
                providerName=provider or "none",
                lastChecked=None,
            )
        if self._ai_capability_service is None:
            return AIProviderHealthDto(
                status="configured",
                latencyMs=None,
                providerId=provider,
                providerName=provider,
                lastChecked=None,
            )
        overview = self._ai_capability_service.get_provider_health_overview()
        snapshot = next((item for item in overview.providers if item.provider == provider), None)
        return AIProviderHealthDto(
            status=snapshot.readiness if snapshot is not None else "configured",
            latencyMs=snapshot.latencyMs if snapshot is not None else None,
            providerId=provider,
            providerName=snapshot.label if snapshot is not None else provider,
            lastChecked=snapshot.lastCheckedAt if snapshot is not None else None,
        )

    def _build_render_queue_health(self) -> RenderQueueHealthDto:
        if self._render_repository is None:
            return RenderQueueHealthDto(running=0, queued=0, avgWaitMs=None)

        try:
            tasks = self._render_repository.list_tasks()
        except Exception as exc:  # noqa: BLE001
            log.exception("Failed to load render task health status")
            raise HTTPException(
                status_code=500,
                detail="render queue health check failed",
            ) from exc

        running = sum(1 for task in tasks if task.status == "running")
        queued = sum(1 for task in tasks if task.status == "queued")
        wait_times = [
            (datetime.now(UTC) - task.created_at).total_seconds() * 1000
            for task in tasks
            if task.status == "queued" and task.created_at is not None
        ]
        avg_wait_ms = int(mean(wait_times)) if wait_times else None
        return RenderQueueHealthDto(running=running, queued=queued, avgWaitMs=avg_wait_ms)

    def _build_publishing_queue_health(self) -> PublishingQueueHealthDto:
        if self._publishing_repository is None:
            return PublishingQueueHealthDto(pendingToday=0, failedToday=0)

        try:
            plans = self._publishing_repository.list_plans()
        except Exception as exc:  # noqa: BLE001
            log.exception("Failed to load publishing plan health status")
            raise HTTPException(
                status_code=500,
                detail="publishing queue health check failed",
            ) from exc

        pending_statuses = {"draft", "scheduled", "submitting"}
        pending_today = sum(1 for plan in plans if plan.status in pending_statuses)
        now = datetime.now(UTC)
        start_of_day = datetime(now.year, now.month, now.day, tzinfo=UTC)
        failed_today = 0
        for plan in plans:
            if plan.status != "failed":
                continue
            last_update = plan.updated_at
            if last_update is not None and last_update >= start_of_day:
                failed_today += 1

        return PublishingQueueHealthDto(
            pendingToday=pending_today,
            failedToday=failed_today,
        )

    def _build_task_bus_health(self) -> TaskBusHealthDto:
        if self._task_manager is None:
            return TaskBusHealthDto(running=0, queued=0, blocked=0, failed24h=0)

        active_tasks = self._task_manager.list_active()
        running = sum(1 for task in active_tasks if task.status == "running")
        queued = sum(1 for task in active_tasks if task.status == "queued")
        blocked = sum(1 for task in active_tasks if task.status == "blocked")
        return TaskBusHealthDto(
            running=running,
            queued=queued,
            blocked=blocked,
            failed24h=0,
        )

    def _build_license_health(self, *, request_id: str | None = None) -> LicenseHealthDto:
        if self._license_service is None:
            return LicenseHealthDto(status="missing", expiresAt=None)
        try:
            license_status = self._license_service.get_status(request_id=request_id)
        except Exception as exc:  # noqa: BLE001
            log.exception("Failed to load license status")
            return LicenseHealthDto(status="unknown", expiresAt=None)

        if license_status.active:
            status = "active"
        elif license_status.restrictedMode:
            status = "missing"
        else:
            status = "inactive"
        return LicenseHealthDto(status=status, expiresAt=None)

    def _calc_uptime_ms(self) -> int | None:
        uptime = datetime.now(UTC) - self._started_at
        return int(uptime.total_seconds() * 1000)

    def _parse_since(self, since: str | None) -> datetime | None:
        if since is None:
            return None
        try:
            return _to_datetime(since)
        except (ValueError, TypeError) as exc:
            raise HTTPException(
                status_code=422,
                detail="请求参数校验失败",
            ) from exc

    def _read_runtime_log_items(self, log_path: Path) -> list[RuntimeLogItemDto]:
        if not log_path.exists():
            return []

        items: list[RuntimeLogItemDto] = []
        try:
            with log_path.open("r", encoding="utf-8") as file:
                for raw_line in file:
                    raw = raw_line.strip()
                    if not raw:
                        continue
                    items.extend(self._parse_runtime_log_line(raw))
        except Exception as exc:  # noqa: BLE001
            log.exception("Failed to read runtime log file")
            raise HTTPException(status_code=500, detail="runtime log read failed") from exc
        return items

    def _parse_runtime_log_line(self, raw_line: str) -> list[RuntimeLogItemDto]:
        try:
            payload = json.loads(raw_line)
        except json.JSONDecodeError:
            return []
        if not isinstance(payload, dict):
            return []
        context = payload.get("context")
        return [
            RuntimeLogItemDto(
                timestamp=str(payload.get("timestamp", "")),
                level=str(payload.get("level", "INFO")),
                kind=str(payload.get("category", "system")),
                requestId=str(payload.get("requestId", "")) or None,
                message=str(payload.get("message", "")),
                context=context if isinstance(context, dict) else None,
            )
        ]

    def _filter_runtime_log_items(
        self,
        items: list[RuntimeLogItemDto],
        *,
        kind: str | None,
        since_dt: datetime | None,
        level: str | None,
    ) -> list[RuntimeLogItemDto]:
        result: list[RuntimeLogItemDto] = []
        for item in items:
            if kind is not None and item.kind != kind:
                continue
            if level is not None and item.level.lower() != level.lower():
                continue
            if since_dt is not None:
                try:
                    item_dt = _to_datetime(item.timestamp)
                except (ValueError, TypeError):
                    continue
                if item_dt <= since_dt:
                    continue
            result.append(item)
        return result

    def _load_or_create(self) -> StoredSystemConfig:
        stored = self._repository.load()
        if stored is not None:
            return stored

        defaults = self._build_default_settings()
        return self._repository.save(defaults.model_dump(mode="json"))

    def _build_default_settings(self) -> AppSettingsUpdateInput:
        defaults = SettingsDefaults(
            runtime_mode=self._runtime_config.mode,
            workspace_root=str(self._runtime_config.repo_root),
            cache_dir=str(self._runtime_config.data_dir / "cache"),
            export_dir=str(self._runtime_config.data_dir / "exports"),
            log_dir=str(self._runtime_config.data_dir / "logs"),
        )
        return AppSettingsUpdateInput.model_validate(
            {
                "runtime": {
                    "mode": defaults.runtime_mode,
                    "workspaceRoot": defaults.workspace_root,
                },
                "paths": {
                    "cacheDir": defaults.cache_dir,
                    "exportDir": defaults.export_dir,
                    "logDir": defaults.log_dir,
                },
                "logging": {"level": "INFO"},
                "ai": {
                    "provider": "openai",
                    "model": "gpt-5.4",
                    "voice": "alloy",
                    "subtitleMode": "balanced",
                },
                "media": {"ffprobePath": ""},
            }
        )

    def _to_settings_dto(self, stored: StoredSystemConfig) -> AppSettingsDto:
        document = dict(stored.document)
        document.setdefault("media", {"ffprobePath": ""})
        return AppSettingsDto.model_validate(
            {
                "revision": stored.revision,
                **document,
            }
        )

    def _sync_media_tool_config(self, settings: AppSettingsDto) -> None:
        configure_ffprobe_path(settings.media.ffprobePath)

    def _ensure_runtime_directories(self, settings: AppSettingsDto) -> None:
        for directory in (
            Path(settings.runtime.workspaceRoot),
            Path(settings.paths.cacheDir),
            Path(settings.paths.exportDir),
            Path(settings.paths.logDir),
        ):
            directory.mkdir(parents=True, exist_ok=True)
