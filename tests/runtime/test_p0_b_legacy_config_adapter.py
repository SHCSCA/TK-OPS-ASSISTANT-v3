from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, Request

from api.dependencies.request_context import RequestContext
from api.routes.legacy.system import (
    _reject_migrated_sections,
    get_runtime_config,
    update_runtime_config,
)
from app.config import RuntimeConfig
from config.migration import MigrationConfig
from errors import DomainError, ErrorCode
from repositories.system_config_repository import StoredSystemConfig
from schemas.settings import (
    AISettingsSection,
    AppSettingsDto,
    AppSettingsUpdateInput,
    BrowserSettingsSection,
    LoggingSettingsSection,
    MediaSettingsSection,
    PathSettingsSection,
    RuntimeSettingsSection,
)
from services.config import ConfigBusService
from services.settings_service import SettingsService


def test_legacy_config_rejects_runtime_path_and_ai_writes() -> None:
    current = _settings()
    changed_ai = current.model_copy(
        update={
            "ai": current.ai.model_copy(
                update={"provider": "other-provider"}
            )
        }
    )

    with pytest.raises(DomainError) as captured:
        _reject_migrated_sections(changed_ai, current)

    assert captured.value.error_code == ErrorCode.LEGACY_WRITE_UNSUPPORTED
    assert captured.value.status_code == 410


def test_legacy_config_repeated_get_is_read_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _ConfigRepository(_settings_document())
    request = _legacy_config_request(
        tmp_path=tmp_path,
        repository=repository,
    )
    mkdir_calls: list[Path] = []

    def capture_mkdir(path: Path, *args: object, **kwargs: object) -> None:
        mkdir_calls.append(path)

    monkeypatch.setattr(Path, "mkdir", capture_mkdir)

    first = get_runtime_config(request)
    second = get_runtime_config(request)

    assert first == second
    assert first["data"]["revision"] == 7
    assert first["data"]["ai"]["provider"] == "legacy-provider"
    assert repository.load_calls == 2
    assert repository.save_calls == 0
    assert repository.save_if_revision_calls == 0
    assert mkdir_calls == []


def test_legacy_config_put_maps_saved_bus_snapshot_without_legacy_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _ConfigRepository(_settings_document())
    request = _legacy_config_request(
        tmp_path=tmp_path,
        repository=repository,
    )
    mkdir_calls: list[Path] = []

    def capture_mkdir(path: Path, *args: object, **kwargs: object) -> None:
        mkdir_calls.append(path)

    monkeypatch.setattr(Path, "mkdir", capture_mkdir)
    current = _settings()
    payload = AppSettingsUpdateInput.model_validate(
        current.model_dump(mode="json")
    ).model_copy(
        update={"logging": LoggingSettingsSection(level="DEBUG")}
    )

    response = update_runtime_config(
        payload,
        request,
        RequestContext(
            request_id="req-legacy-config",
            operation_id="op-legacy-config",
            idempotency_key=None,
        ),
    )

    assert response["data"]["revision"] == 8
    assert response["data"]["logging"]["level"] == "DEBUG"
    assert response["data"]["ai"]["model"] == "legacy-model"
    assert repository.load_calls == 2
    assert repository.save_calls == 0
    assert repository.save_if_revision_calls == 1
    assert mkdir_calls == []


class _ConfigRepository:
    def __init__(self, document: dict[str, object]) -> None:
        self.document = document
        self.revision = 7
        self.load_calls = 0
        self.save_calls = 0
        self.save_if_revision_calls = 0

    def load(self) -> StoredSystemConfig:
        self.load_calls += 1
        return StoredSystemConfig(
            revision=self.revision,
            document=self.document,
            updated_at="2026-07-26T10:00:00Z",
        )

    def save(self, document: dict[str, object]) -> StoredSystemConfig:
        self.save_calls += 1
        raise AssertionError("只读兼容路径不得调用旧配置保存")

    def save_if_revision(
        self,
        document: dict[str, object],
        *,
        expected_revision: int,
        before_commit: object = None,
    ) -> StoredSystemConfig:
        self.save_if_revision_calls += 1
        assert expected_revision == self.revision
        assert before_commit is not None
        self.revision += 1
        self.document = document
        return StoredSystemConfig(
            revision=self.revision,
            document=document,
            updated_at="2026-07-26T10:01:00Z",
        )


class _LegacySettingsServiceTrap(SettingsService):
    def __init__(self) -> None:
        pass

    def get_settings(self) -> AppSettingsDto:
        raise AssertionError("兼容配置读取不得调用旧 SettingsService")


def _settings() -> AppSettingsDto:
    return AppSettingsDto(
        runtime=RuntimeSettingsSection(
            mode="test",
            workspaceRoot="C:/workspace",
        ),
        paths=PathSettingsSection(
            cacheDir="C:/workspace/cache",
            exportDir="C:/workspace/exports",
            logDir="C:/workspace/logs",
        ),
        logging=LoggingSettingsSection(level="INFO"),
        ai=AISettingsSection(
            provider="legacy-provider",
            model="legacy-model",
            voice="default",
            subtitleMode="auto",
        ),
        media=MediaSettingsSection(),
        browser=BrowserSettingsSection(),
        revision=1,
    )


def _settings_document() -> dict[str, object]:
    settings = _settings().model_dump(mode="json")
    settings.pop("revision")
    settings.pop("scope")
    return settings


def _legacy_config_request(
    *,
    tmp_path: Path,
    repository: _ConfigRepository,
) -> Request:
    runtime_config = _runtime_config(tmp_path)
    app = FastAPI()
    app.state.runtime_config = runtime_config
    app.state.runtime_container = SimpleNamespace(
        config=runtime_config,
        current_settings=_settings(),
    )
    app.state.config_bus_service = ConfigBusService(repository)
    app.state.settings_service = _LegacySettingsServiceTrap()
    return Request(
        {
            "type": "http",
            "app": app,
            "method": "GET",
            "scheme": "http",
            "path": "/api/settings/config",
            "raw_path": b"/api/settings/config",
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 43120),
            "server": ("127.0.0.1", 43119),
        }
    )


def _runtime_config(tmp_path: Path) -> RuntimeConfig:
    data_dir = tmp_path / "runtime-data"
    database_path = data_dir / "runtime.db"
    return RuntimeConfig(
        version="0.4.7",
        mode="test",
        repo_root=tmp_path,
        data_dir=data_dir,
        database_path=database_path,
        migration=MigrationConfig(
            backup_dir=data_dir / "migration-backups",
            backup_retention_count=5,
            lock_path=data_dir / "migration.lock",
            lock_timeout_seconds=1.0,
        ),
        license_public_key_path=data_dir / "license-public.pem",
        allowed_origins=("http://127.0.0.1:5173",),
    )
