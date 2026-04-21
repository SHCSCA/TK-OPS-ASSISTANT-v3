from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from typing import Any, Callable
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
    AIProviderHealthDto,
    DiagnosticsBundleDto,
    FfprobeDiagnosticsDto,
    LicenseHealthDto,
    MediaDiagnosticsDto,
    PublishingQueueHealthDto,
    RenderQueueHealthDto,
    RuntimeDiagnosticsDto,
    RuntimeHealthSnapshotDto,
    RuntimeSubsystemHealthDto,
    RuntimeLogItemDto,
    RuntimeLogPageDto,
    TaskBusHealthDto,
)
from services.ffprobe import get_ffprobe_availability
from services.license_service import LicenseService
from services.task_manager import TaskManager

log = logging.getLogger(__name__)

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
    ) -> None:
        self._runtime_config = runtime_config
        self._repository = repository
        self._on_settings_updated = on_settings_updated
        self._render_repository = render_repository
        self._publishing_repository = publishing_repository
        self._task_manager = task_manager
        self._license_service = license_service
        self._started_at = datetime.now(UTC)

    def get_settings(self) -> AppSettingsDto:
        stored = self._load_or_create()
        settings = self._to_settings_dto(stored)
        self._ensure_runtime_directories(settings)
        return settings

    def update_settings(
        self,
        payload: AppSettingsUpdateInput,
        *,
        request_id: str | None = None,
    ) -> AppSettingsDto:
        stored = self._repository.save(payload.model_dump(mode="json"))
        settings = self._to_settings_dto(stored)
        self._ensure_runtime_directories(settings)

        if self._on_settings_updated is not None:
            self._on_settings_updated(settings)

        log_event(
            "audit",
            "settings.updated",
            request_id=request_id,
            context={"revision": settings.revision},
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
        return RuntimeDiagnosticsDto(
            databasePath=str(self._runtime_config.database_path),
            logDir=settings.paths.logDir,
            revision=settings.revision,
            mode=settings.runtime.mode,
            healthStatus="online",
        )

    def get_media_diagnostics(self) -> MediaDiagnosticsDto:
        ffprobe = get_ffprobe_availability()
        return MediaDiagnosticsDto(
            ffprobe=FfprobeDiagnosticsDto(
                status=ffprobe.status,
                path=ffprobe.path,
                version=ffprobe.version,
                errorCode=ffprobe.error_code,
                errorMessage=ffprobe.error_message,
            ),
            checkedAt=_utc_now_iso(),
        )

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
        status = "configured" if provider and model_name else "not_configured"
        return AIProviderHealthDto(
            status=status,
            latencyMs=None,
            providerId=provider or "none",
            providerName=provider or "none",
            lastChecked=None,
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
            }
        )

    def _to_settings_dto(self, stored: StoredSystemConfig) -> AppSettingsDto:
        return AppSettingsDto.model_validate(
            {
                "revision": stored.revision,
                **stored.document,
            }
        )

    def _ensure_runtime_directories(self, settings: AppSettingsDto) -> None:
        for directory in (
            Path(settings.runtime.workspaceRoot),
            Path(settings.paths.cacheDir),
            Path(settings.paths.exportDir),
            Path(settings.paths.logDir),
        ):
            directory.mkdir(parents=True, exist_ok=True)
