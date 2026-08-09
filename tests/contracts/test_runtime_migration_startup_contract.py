from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

import app.factory as runtime_factory
from app.logging import shutdown_logging
from app.pre_write_startup_recovery import (
    PRE_WRITE_STARTUP_FAILED,
    PreWriteStartupRecoveryError,
)
from config.database import DatabasePathConfigurationError
from persistence.migration import (
    MIGRATION_FAILED,
    MigrationReport,
    RuntimeMigrationError,
)


TARGET_REVISION = "0022_p0g_production_hardening"


def test_runtime_factory_finishes_alembic_before_building_container(runtime_app) -> None:
    database_path = runtime_app.state.runtime_config.database_path

    with sqlite3.connect(database_path) as connection:
        revision = connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone()
        tables = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }

    assert revision == (TARGET_REVISION,)
    assert "schema_meta" not in tables
    assert {
        "provider_profiles",
        "runtime_tasks",
        "runtime_events",
        "runtime_mutation_idempotency",
    }.issubset(tables)
    assert runtime_app.state.migration_report.target_revision == revision[0]


def test_migration_failure_stops_before_secrets_engine_and_repositories(
    runtime_data_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    failure = RuntimeMigrationError(
        "模拟迁移失败",
        error_code=MIGRATION_FAILED,
        log_id="migration-test-log",
    )

    def fail_migration(_: object) -> None:
        calls.append("migration")
        raise failure

    def unexpected_secret_store(_: object) -> None:
        calls.append("secret_store")
        raise AssertionError("迁移失败后不应创建安全存储")

    def unexpected_engine(_: object) -> None:
        calls.append("engine")
        raise AssertionError("迁移失败后不应创建数据库引擎")

    monkeypatch.setattr(runtime_factory, "prepare_runtime_database", fail_migration)
    monkeypatch.setattr(runtime_factory, "build_secret_store", unexpected_secret_store)
    monkeypatch.setattr(runtime_factory, "create_runtime_engine", unexpected_engine)

    with pytest.raises(RuntimeMigrationError) as captured:
        runtime_factory.create_app()

    assert captured.value is failure
    assert calls == ["migration"]


def test_factory_failure_after_engine_creation_disposes_engine_once(
    runtime_data_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    failure = RuntimeError("模拟容器构建失败")
    expected_migration_report = MigrationReport(
        log_id="migration-container-failure",
        schema_kind="versioned",
        previous_revision=TARGET_REVISION,
        target_revision=TARGET_REVISION,
        backup_database_id=None,
        duration_ms=1,
        table_count=1,
        changed=False,
        cutover_event_id="cutover-container-failure",
        pre_migration_fingerprint="a" * 64,
        post_migration_fingerprint="a" * 64,
        schema_read_min_revision="0017_p0_enforce_and_cutover",
        schema_read_max_revision=TARGET_REVISION,
    )
    expected_secret_store = object()

    class DisposableEngine:
        def dispose(self) -> None:
            calls.append("dispose")

    expected_engine = DisposableEngine()

    def successful_migration(_: object) -> object:
        calls.append("migration")
        return expected_migration_report

    def successful_secret_store(_: object) -> object:
        calls.append("secret_store")
        return expected_secret_store

    def successful_engine_creation(_: object) -> DisposableEngine:
        calls.append("engine")
        return expected_engine

    def fail_container(
        *,
        runtime_config: object,
        migration_report: object,
        secret_store: object,
        engine: object,
        dependency_overrides: object,
    ) -> None:
        assert runtime_config is not None
        assert migration_report is expected_migration_report
        assert secret_store is expected_secret_store
        assert engine is expected_engine
        assert dependency_overrides is None
        calls.append("container")
        raise failure

    monkeypatch.setattr(runtime_factory, "prepare_runtime_database", successful_migration)
    monkeypatch.setattr(runtime_factory, "build_secret_store", successful_secret_store)
    monkeypatch.setattr(runtime_factory, "create_runtime_engine", successful_engine_creation)
    monkeypatch.setattr(runtime_factory, "build_runtime_container", fail_container)

    with pytest.raises(PreWriteStartupRecoveryError) as captured:
        runtime_factory.create_app()

    assert captured.value.error_code == PRE_WRITE_STARTUP_FAILED
    assert captured.value.restored is False
    assert captured.value.__cause__ is failure
    assert calls == [
        "migration",
        "secret_store",
        "engine",
        "container",
        "dispose",
    ]
    assert calls.count("dispose") == 1


def test_database_path_conflict_is_written_to_bootstrap_log(
    runtime_data_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "TK_OPS_DATABASE_PATH",
        str(runtime_data_dir / "conflicting.db"),
    )

    try:
        with pytest.raises(DatabasePathConfigurationError):
            runtime_factory.create_app()
    finally:
        shutdown_logging()

    entries = [
        json.loads(line)
        for line in (runtime_data_dir / "logs" / "runtime.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    assert any(
        entry["logger"] == "config.database"
        and entry["message"] == "数据库路径配置解析失败"
        for entry in entries
    )
