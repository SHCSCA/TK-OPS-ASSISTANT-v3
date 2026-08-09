from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.config import RuntimeConfig
from config.migration import MigrationConfig
from domain.models.system_config import SystemConfig
from errors import DomainError
from persistence.engine import (
    create_runtime_engine,
    create_session_factory,
)
from persistence.migration import MigrationReport
from repositories.system_config_repository import SystemConfigRepository
from services.config import ConfigBusService
from services.config.schema import DEFAULT_VALUES, WRITABLE_RULES
from services.diagnostics import RuntimeDiagnosticsService


def _repository(tmp_path: Path) -> SystemConfigRepository:
    engine = create_runtime_engine(tmp_path / "runtime.db")
    SystemConfig.__table__.create(engine)
    return SystemConfigRepository(
        session_factory=create_session_factory(engine),
    )


def test_config_bus_updates_only_whitelisted_keys(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    stored = repository.save(
        {
            "runtime": {"mode": "test", "workspaceRoot": str(tmp_path)},
            "paths": {
                "cacheDir": str(tmp_path / "cache"),
                "exportDir": str(tmp_path / "exports"),
                "logDir": str(tmp_path / "logs"),
            },
            "logging": {"level": "INFO"},
            "ai": {"provider": "legacy-provider"},
            "media": {"ffprobePath": "", "ffmpegPath": ""},
            "browser": {"executablePath": ""},
        }
    )
    service = ConfigBusService(repository)

    result = service.update(
        {
            "logging.level": "WARNING",
            "ui.theme": "dark",
            "runtime.taskTimeoutSeconds": 900,
        },
        expected_revision=stored.revision,
        request_id="req_config_test",
        operation_id="op_config_test",
    )

    assert result.revision == stored.revision + 1
    assert result.values["logging.level"] == "WARNING"
    assert result.values["ui.theme"] == "dark"
    assert result.values["runtime.taskTimeoutSeconds"] == 900
    persisted = repository.load()
    assert persisted is not None
    assert persisted.document["ai"] == {"provider": "legacy-provider"}
    assert "credential" not in result.values


def test_config_bus_rejects_unknown_key_without_partial_write(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    stored = repository.save({"logging": {"level": "INFO"}})
    service = ConfigBusService(repository)

    with pytest.raises(DomainError) as exc_info:
        service.update(
            {
                "logging.level": "ERROR",
                "provider.apiKey": "secret",
            },
            expected_revision=stored.revision,
            request_id="req_config_invalid",
            operation_id="op_config_invalid",
        )

    assert exc_info.value.error_code == "CONFIG_KEY_NOT_WRITABLE"
    unchanged = repository.load()
    assert unchanged is not None
    assert unchanged.revision == stored.revision
    assert unchanged.document["logging"]["level"] == "INFO"


def test_config_bus_revision_conflict_reports_current_revision(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    stored = repository.save({"logging": {"level": "INFO"}})
    service = ConfigBusService(repository)

    with pytest.raises(DomainError) as exc_info:
        service.update(
            {"logging.level": "DEBUG"},
            expected_revision=stored.revision - 1,
            request_id="req_config_conflict",
            operation_id="op_config_conflict",
        )

    assert exc_info.value.error_code == "CONFIG_REVISION_CONFLICT"
    assert exc_info.value.meta["currentRevision"] == stored.revision


def test_config_bus_rolls_back_document_when_event_write_fails(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    stored = repository.save({"logging": {"level": "INFO"}})
    service = ConfigBusService(
        repository,
        event_writer=_raise_config_event_error,
    )

    with pytest.raises(DomainError) as exc_info:
        service.update(
            {"logging.level": "ERROR"},
            expected_revision=stored.revision,
            request_id="req_config_event_failure",
            operation_id="op_config_event_failure",
        )

    assert exc_info.value.error_code == "INTERNAL_ERROR"
    unchanged = repository.load()
    assert unchanged is not None
    assert unchanged.revision == stored.revision
    assert unchanged.document["logging"]["level"] == "INFO"


def test_config_bus_reports_post_commit_refresh_failure_as_warning(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    stored = repository.save({"logging": {"level": "INFO"}})
    service = ConfigBusService(
        repository,
        on_updated=_raise_config_refresh_error,
    )

    result = service.update(
        {"logging.level": "WARNING"},
        expected_revision=stored.revision,
        request_id="req_config_refresh_failure",
        operation_id="op_config_refresh_failure",
    )

    assert result.revision == stored.revision + 1
    assert result.warnings == (
        "配置已保存，运行时刷新失败；请重启 Runtime 后生效",
    )
    persisted = repository.load()
    assert persisted is not None
    assert persisted.document["logging"]["level"] == "WARNING"


def test_every_writable_config_key_has_a_valid_default() -> None:
    assert set(WRITABLE_RULES) == set(DEFAULT_VALUES)
    assert all(
        rule.validator(DEFAULT_VALUES[key])
        for key, rule in WRITABLE_RULES.items()
    )


def test_diagnostic_log_excerpt_never_returns_traceback_or_context(
    tmp_path: Path,
) -> None:
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    private_path = r"C:\Users\Administrator\account-secret.json"
    (log_dir / "runtime.jsonl").write_text(
        json.dumps(
            {
                "timestamp": "2026-07-26T00:00:00Z",
                "level": "ERROR",
                "message": (
                    f"任务执行失败，文件={private_path}，"
                    "Authorization: Bearer api-secret，"
                    'Provider request body: {"prompt":"private-prompt"}'
                ),
                "request_id": "req_123",
                "operation_id": private_path,
                "log_id": "log_12345678",
                "error_code": "TASK_TIMEOUT",
                "stage": private_path,
                "context": {"credential": "secret-value"},
                "exception": (
                    "RuntimeError: private traceback "
                    "password=exception-secret"
                ),
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    runtime_config = _runtime_config(tmp_path)
    service = RuntimeDiagnosticsService(
        runtime_config=runtime_config,
        migration_report=MigrationReport(
            log_id="migration-log",
            schema_kind="versioned",
            previous_revision="0017",
            target_revision="0018",
            backup_database_id=None,
            duration_ms=1,
            table_count=1,
            changed=False,
        ),
        log_dir=log_dir,
    )

    excerpt = service.get_safe_log_excerpt("log_12345678")

    assert excerpt["errorCode"] == "TASK_TIMEOUT"
    assert excerpt["stage"] is None
    assert excerpt["operationId"] is None
    assert excerpt["requestId"] == "req_123"
    assert "[本地路径已隐藏]" in excerpt["summary"]
    assert "Authorization: Bearer [已脱敏]" in excerpt["summary"]
    assert "context" not in excerpt
    assert "exception" not in excerpt
    safe_excerpt = repr(excerpt)
    for private_value in (
        private_path,
        "api-secret",
        "private-prompt",
        "secret-value",
        "traceback",
        "exception-secret",
    ):
        assert private_value not in safe_excerpt


def _raise_config_event_error(*_args: object) -> None:
    raise RuntimeError("event write failed")


def _raise_config_refresh_error(*_args: object) -> None:
    raise RuntimeError("refresh failed")


def _runtime_config(tmp_path: Path) -> RuntimeConfig:
    database_path = tmp_path / "runtime.db"
    migration = MigrationConfig(
        backup_dir=tmp_path / "backups",
        backup_retention_count=3,
        lock_path=tmp_path / "migration.lock",
        lock_timeout_seconds=1.0,
    )
    return RuntimeConfig(
        version="test",
        mode="test",
        repo_root=tmp_path,
        data_dir=tmp_path,
        database_path=database_path,
        migration=migration,
        license_public_key_path=tmp_path / "license.pem",
        allowed_origins=("http://127.0.0.1:1420",),
    )
