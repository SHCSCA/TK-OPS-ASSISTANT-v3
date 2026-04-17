from __future__ import annotations

import asyncio
import json
import os
import socket
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from importlib.util import find_spec
from typing import Any, Callable
from zipfile import ZIP_DEFLATED, ZipFile

from app.config import RuntimeConfig
from app.logging import log_event
from repositories.system_config_repository import StoredSystemConfig, SystemConfigRepository
from schemas.bootstrap import (
    BootstrapDirectoryReportDto,
    BootstrapDirectoryStatusDto,
    RuntimeSelfCheckItemDto,
    RuntimeSelfCheckReportDto,
)
from schemas.error_codes import ErrorCodes
from schemas.settings import (
    AppSettingsDto,
    AppSettingsUpdateInput,
    DiagnosticsBundleDto,
    DiagnosticsBundleEntryDto,
    RuntimeDiagnosticsDto,
    RuntimeHealthAIProviderDto,
    RuntimeHealthLicenseDto,
    RuntimeHealthPublishingQueueDto,
    RuntimeHealthRenderQueueDto,
    RuntimeHealthRuntimeDto,
    RuntimeHealthSnapshotDto,
    RuntimeLogEntryDto,
    RuntimeLogPageDto,
    RuntimeHealthTaskBusDto,
)
from services.task_manager import TaskManager
from services.ws_manager import ws_manager


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
        task_manager: TaskManager | None = None,
    ) -> None:
        self._runtime_config = runtime_config
        self._repository = repository
        self._on_settings_updated = on_settings_updated
        self._task_manager = task_manager
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
        current_settings = self.get_settings()
        changed_keys = _collect_changed_keys(
            current_settings.model_dump(mode="json", exclude={"revision"}),
            payload.model_dump(mode="json", exclude={"revision"}),
        )

        stored = self._repository.save(payload.model_dump(mode="json", exclude={"revision"}))
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
        asyncio.run(
            ws_manager.broadcast(
                {
                    "type": "config.changed",
                    "payload": {
                        "changedKeys": changed_keys,
                        "revision": settings.revision,
                    },
                }
            )
        )
        return settings

    def get_health(self) -> dict[str, object]:
        settings = self.get_settings()
        now = datetime.now(UTC)
        now_iso = now.isoformat().replace("+00:00", "Z")
        uptime_ms = max(0, int((now - self._started_at).total_seconds() * 1000))
        provider_id = settings.ai.provider or None
        provider_name = _provider_label(provider_id) if provider_id else None
        tasks = self._task_manager.list_tasks() if self._task_manager is not None else []
        snapshot = RuntimeHealthSnapshotDto(
            runtime=RuntimeHealthRuntimeDto(
                status="online",
                port=self._runtime_config.port,
                uptimeMs=uptime_ms,
                version=self._runtime_config.version,
            ),
            aiProvider=RuntimeHealthAIProviderDto(
                status="configured" if provider_id else "missing",
                latencyMs=None,
                providerId=provider_id,
                providerName=provider_name,
                lastChecked=None,
            ),
            renderQueue=RuntimeHealthRenderQueueDto(
                running=0,
                queued=0,
                avgWaitMs=None,
            ),
            publishingQueue=RuntimeHealthPublishingQueueDto(
                pendingToday=0,
                failedToday=0,
            ),
            taskBus=RuntimeHealthTaskBusDto(
                running=sum(1 for item in tasks if item.status == "running"),
                queued=sum(1 for item in tasks if item.status == "queued"),
                blocked=sum(1 for item in tasks if item.status == "blocked"),
                failed24h=sum(1 for item in tasks if item.status == "failed"),
            ),
            license=RuntimeHealthLicenseDto(
                status="missing",
                expiresAt=None,
            ),
            lastSyncAt=now_iso,
            service="online",
            version=self._runtime_config.version,
            now=now_iso,
            mode=settings.runtime.mode,
        )
        return snapshot.model_dump(mode="json")

    def get_diagnostics(self) -> RuntimeDiagnosticsDto:
        settings = self.get_settings()
        return RuntimeDiagnosticsDto(
            databasePath=str(self._runtime_config.database_path),
            logDir=settings.paths.logDir,
            revision=settings.revision,
            mode=settings.runtime.mode,
            healthStatus="online",
        )

    def initialize_directories(
        self,
        *,
        request_id: str | None = None,
    ) -> BootstrapDirectoryReportDto:
        settings = self.get_settings()
        checked_at = _utc_now_iso()
        directories = [
            self._ensure_directory("workspace", "工作区目录", Path(settings.runtime.workspaceRoot)),
            self._ensure_directory("cache", "缓存目录", Path(settings.paths.cacheDir)),
            self._ensure_directory("exports", "导出目录", Path(settings.paths.exportDir)),
            self._ensure_directory("logs", "日志目录", Path(settings.paths.logDir)),
            self._ensure_directory("projects", "项目目录", self._runtime_config.data_dir / "projects"),
            self._ensure_directory("assets", "资产目录", self._runtime_config.data_dir / "assets"),
            self._ensure_directory("licenses", "许可证目录", self._runtime_config.data_dir / "licenses"),
        ]
        status = "ok" if all(item.status == "ok" for item in directories) else "degraded"
        report = BootstrapDirectoryReportDto(
            rootDir=str(self._runtime_config.data_dir),
            databasePath=str(self._runtime_config.database_path),
            status=status,
            directories=directories,
            checkedAt=checked_at,
        )
        log_event(
            "audit",
            "bootstrap.initialize_directories",
            context={
                "status": status,
                "rootDir": report.rootDir,
            },
            request_id=request_id,
        )
        return report

    def run_runtime_selfcheck(
        self,
        *,
        request_id: str | None = None,
    ) -> RuntimeSelfCheckReportDto:
        checked_at = _utc_now_iso()
        items = [
            self._check_runtime_port(checked_at),
            self._check_runtime_version(checked_at),
            self._check_runtime_dependencies(checked_at),
            self._check_runtime_database(checked_at),
        ]
        status = "ok" if all(item.status == "ok" for item in items) else "degraded"
        report = RuntimeSelfCheckReportDto(
            status=status,
            runtimeVersion=self._runtime_config.version,
            checkedAt=checked_at,
            items=items,
        )
        log_event(
            "system",
            "bootstrap.runtime_selfcheck",
            context={
                "status": status,
                "items": [item.model_dump(mode="json") for item in items],
            },
            request_id=request_id,
        )
        return report

    def get_logs(
        self,
        *,
        kind: str | None = None,
        since: str | None = None,
        level: str | None = None,
        limit: int = 100,
    ) -> RuntimeLogPageDto:
        settings = self.get_settings()
        log_path = Path(settings.paths.logDir) / "runtime.jsonl"
        if not log_path.exists():
            return RuntimeLogPageDto(items=[], nextCursor=None)

        since_dt = _parse_iso_datetime(since)
        normalized_level = level.strip().upper() if level else None
        entries: list[RuntimeLogEntryDto] = []

        for line in log_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue

            timestamp = str(payload.get("timestamp", ""))
            category = str(payload.get("category", "system"))
            entry_level = str(payload.get("level", "INFO")).upper()
            if kind and category != kind:
                continue
            if normalized_level and entry_level != normalized_level:
                continue
            if since_dt is not None:
                entry_dt = _parse_iso_datetime(timestamp)
                if entry_dt is None or entry_dt < since_dt:
                    continue

            entries.append(
                RuntimeLogEntryDto(
                    timestamp=timestamp,
                    level=entry_level,
                    kind=category,
                    requestId=str(payload.get("requestId", "")),
                    message=str(payload.get("message", "")),
                    context=_coerce_log_context(payload.get("context")),
                )
            )

        entries.sort(key=lambda item: item.timestamp, reverse=True)
        page_items = entries[:limit]
        next_cursor = entries[limit].timestamp if len(entries) > limit else None
        return RuntimeLogPageDto(items=page_items, nextCursor=next_cursor)

    def export_diagnostics_bundle(
        self,
        *,
        request_id: str | None = None,
    ) -> DiagnosticsBundleDto:
        settings = self.get_settings()
        export_dir = Path(settings.paths.exportDir) / "diagnostics"
        export_dir.mkdir(parents=True, exist_ok=True)

        created_at = _utc_now_iso()
        bundle_path = export_dir / f"tk-ops-diagnostics-{_timestamp_slug(created_at)}.zip"
        log_event(
            "audit",
            "settings.diagnostics.export",
            context={"bundlePath": str(bundle_path)},
            request_id=request_id,
        )

        files: list[tuple[str, bytes]] = [
            (
                "settings.json",
                json.dumps(
                    settings.model_dump(mode="json"),
                    ensure_ascii=False,
                    indent=2,
                ).encode("utf-8"),
            ),
            (
                "health.json",
                json.dumps(
                    self.get_health(),
                    ensure_ascii=False,
                    indent=2,
                ).encode("utf-8"),
            ),
            (
                "diagnostics.json",
                json.dumps(
                    self.get_diagnostics().model_dump(mode="json"),
                    ensure_ascii=False,
                    indent=2,
                ).encode("utf-8"),
            ),
        ]

        log_path = Path(settings.paths.logDir) / "runtime.jsonl"
        if log_path.exists():
            files.append(("runtime.jsonl", log_path.read_bytes()))

        with ZipFile(bundle_path, "w", compression=ZIP_DEFLATED) as archive:
            for name, content in files:
                archive.writestr(name, content)

        entries = [
            DiagnosticsBundleEntryDto(
                name=name,
                path=name,
                sizeBytes=len(content),
            )
            for name, content in files
        ]
        return DiagnosticsBundleDto(
            bundlePath=str(bundle_path),
            createdAt=created_at,
            entries=entries,
        )

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

    def _ensure_directory(
        self,
        key: str,
        label: str,
        path: Path,
    ) -> BootstrapDirectoryStatusDto:
        try:
            path.mkdir(parents=True, exist_ok=True)
            writable = os.access(path, os.W_OK)
            return BootstrapDirectoryStatusDto(
                key=key,
                label=label,
                path=str(path),
                exists=path.exists(),
                writable=writable,
                status="ok" if writable else "error",
                message="目录已就绪" if writable else "目录不可写",
            )
        except OSError as exc:
            return BootstrapDirectoryStatusDto(
                key=key,
                label=label,
                path=str(path),
                exists=path.exists(),
                writable=False,
                status="error",
                message=str(exc),
            )

    def _check_runtime_port(self, checked_at: str) -> RuntimeSelfCheckItemDto:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(("127.0.0.1", self._runtime_config.port))
        except OSError:
            return RuntimeSelfCheckItemDto(
                key="port",
                label="端口检查",
                status="error",
                detail=f"端口 {self._runtime_config.port} 已被占用。",
                errorCode=ErrorCodes.RUNTIME_PORT_OCCUPIED,
                checkedAt=checked_at,
            )
        finally:
            sock.close()

        return RuntimeSelfCheckItemDto(
            key="port",
            label="端口检查",
            status="ok",
            detail=f"端口 {self._runtime_config.port} 可用。",
            checkedAt=checked_at,
        )

    def _check_runtime_version(self, checked_at: str) -> RuntimeSelfCheckItemDto:
        status = "ok" if self._runtime_config.version != "unknown" else "error"
        return RuntimeSelfCheckItemDto(
            key="version",
            label="版本检查",
            status=status,
            detail=f"当前 Runtime 版本：{self._runtime_config.version}",
            errorCode=ErrorCodes.RUNTIME_NOT_READY if status != "ok" else None,
            checkedAt=checked_at,
        )

    def _check_runtime_dependencies(self, checked_at: str) -> RuntimeSelfCheckItemDto:
        required_modules = ("fastapi", "sqlalchemy")
        missing = [name for name in required_modules if find_spec(name) is None]
        if missing:
            return RuntimeSelfCheckItemDto(
                key="dependencies",
                label="依赖检查",
                status="error",
                detail=f"缺少依赖：{', '.join(missing)}",
                errorCode=ErrorCodes.RUNTIME_NOT_READY,
                checkedAt=checked_at,
            )

        return RuntimeSelfCheckItemDto(
            key="dependencies",
            label="依赖检查",
            status="ok",
            detail="FastAPI、SQLAlchemy 与 SQLite 运行依赖已就绪。",
            checkedAt=checked_at,
        )

    def _check_runtime_database(self, checked_at: str) -> RuntimeSelfCheckItemDto:
        database_path = self._runtime_config.database_path
        try:
            database_path.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(database_path) as connection:
                connection.execute("PRAGMA schema_version;").fetchone()
            writable = os.access(database_path, os.W_OK) if database_path.exists() else os.access(
                database_path.parent,
                os.W_OK,
            )
        except sqlite3.Error as exc:
            return RuntimeSelfCheckItemDto(
                key="database",
                label="数据库检查",
                status="error",
                detail=f"数据库检查失败：{exc}",
                errorCode=ErrorCodes.RUNTIME_NOT_READY,
                checkedAt=checked_at,
            )

        return RuntimeSelfCheckItemDto(
            key="database",
            label="数据库检查",
            status="ok" if writable else "error",
            detail=(
                f"数据库文件可访问：{database_path}"
                if writable
                else f"数据库目录不可写：{database_path.parent}"
            ),
            errorCode=None if writable else ErrorCodes.RUNTIME_NOT_READY,
            checkedAt=checked_at,
        )


def _collect_changed_keys(
    current: dict[str, object],
    updated: dict[str, object],
    *,
    prefix: str = "",
) -> list[str]:
    changed: list[str] = []
    for key, value in updated.items():
        path = f"{prefix}.{key}" if prefix else key
        current_value = current.get(key)
        if isinstance(value, dict) and isinstance(current_value, dict):
            changed.extend(_collect_changed_keys(current_value, value, prefix=path))
            continue
        if current_value != value:
            changed.append(path)
    return changed


def _provider_label(provider_id: str | None) -> str | None:
    if provider_id is None:
        return None
    labels = {
        "openai": "OpenAI",
        "openai_compatible": "OpenAI-compatible",
        "anthropic": "Anthropic",
        "gemini": "Gemini",
    }
    return labels.get(provider_id, provider_id.replace("_", " ").title())


def _coerce_log_context(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _timestamp_slug(value: str) -> str:
    return value.replace("-", "").replace(":", "").replace("T", "-").replace("Z", "")
