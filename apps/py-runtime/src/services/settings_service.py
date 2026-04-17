from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable

from app.config import RuntimeConfig
from app.logging import log_event
from repositories.system_config_repository import StoredSystemConfig, SystemConfigRepository
from schemas.settings import AppSettingsDto, AppSettingsUpdateInput, RuntimeDiagnosticsDto


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
    ) -> None:
        self._runtime_config = runtime_config
        self._repository = repository
        self._on_settings_updated = on_settings_updated

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

    def get_health(self) -> dict[str, str]:
        settings = self.get_settings()
        now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        return {
            "service": "online",
            "version": self._runtime_config.version,
            "now": now,
            "mode": settings.runtime.mode,
        }

    def get_diagnostics(self) -> RuntimeDiagnosticsDto:
        settings = self.get_settings()
        return RuntimeDiagnosticsDto(
            databasePath=str(self._runtime_config.database_path),
            logDir=settings.paths.logDir,
            revision=settings.revision,
            mode=settings.runtime.mode,
            healthStatus="online",
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
