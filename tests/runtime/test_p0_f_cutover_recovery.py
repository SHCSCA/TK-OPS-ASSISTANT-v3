from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from config.migration import MigrationConfig
from persistence.migration import (
    MIGRATION_FAILED,
    RuntimeMigrationError,
    inspect_database_schema,
    run_startup_migrations,
)
import persistence.migration.runner as migration_runner

REVISION_0017 = "0017_p0_enforce_and_cutover"


def test_successful_cutover_records_pre_post_and_completion_evidence(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "runtime.db"
    report = run_startup_migrations(
        database_path,
        _migration_config(tmp_path),
    )

    assert report.cutover_event_id.startswith("cut_")
    assert report.pre_migration_fingerprint
    assert report.post_migration_fingerprint
    assert report.schema_read_min_revision == REVISION_0017
    assert report.schema_read_max_revision == report.target_revision
    assert "cutoverJournalPath" not in report.to_log_context()
    assert "compatibilityEvidencePath" not in report.to_log_context()

    stages = _cutover_stages(
        Path(report.cutover_journal_path),
        report.cutover_event_id,
    )
    assert stages[0] == "migration_started"
    assert "pre_migration_validated" in stages
    assert "post_migration_validated" in stages
    assert stages[-1] == "migration_completed"


def test_failed_pre_write_migration_restores_and_records_fingerprint_match(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "runtime.db"
    command.upgrade(_alembic_config(database_path), REVISION_0017)
    original_fingerprint = inspect_database_schema(database_path).fingerprint

    def fail_after_partial_write(_: Config, __: str) -> None:
        with sqlite3.connect(database_path) as connection:
            connection.execute(
                "CREATE TABLE p0f_partial_write (id TEXT PRIMARY KEY)"
            )
        raise RuntimeError("模拟 P0-F 迁移中断")

    monkeypatch.setattr(
        migration_runner.command,
        "upgrade",
        fail_after_partial_write,
    )

    with pytest.raises(RuntimeMigrationError) as captured:
        run_startup_migrations(
            database_path,
            _migration_config(tmp_path),
        )

    assert captured.value.error_code == MIGRATION_FAILED
    assert captured.value.restored is True
    assert captured.value.cutover_event_id
    assert inspect_database_schema(database_path).fingerprint == original_fingerprint
    stages = _cutover_stages(
        tmp_path / "cutover-journal.json",
        captured.value.cutover_event_id,
    )
    assert "migration_failed" in stages
    assert "restore_started" in stages
    assert stages[-1] == "restore_validated"


def _migration_config(tmp_path: Path) -> MigrationConfig:
    return MigrationConfig(
        backup_dir=(tmp_path / "backups").resolve(),
        backup_retention_count=3,
        lock_path=(tmp_path / "migration.lock").resolve(),
        lock_timeout_seconds=1,
        cutover_journal_path=(tmp_path / "cutover-journal.json").resolve(),
        compatibility_evidence_path=(
            tmp_path / "runtime-schema-compatibility.json"
        ).resolve(),
    )


def _alembic_config(database_path: Path) -> Config:
    runtime_root = Path(__file__).resolve().parents[2] / "apps" / "py-runtime"
    config = Config(str(runtime_root / "alembic.ini"))
    config.set_main_option("script_location", str(runtime_root / "alembic"))
    config.attributes["database_url"] = f"sqlite:///{database_path.as_posix()}"
    return config


def _cutover_stages(path: Path, cutover_event_id: str) -> list[str]:
    document = json.loads(path.read_text(encoding="utf-8"))
    return [
        str(item["stage"])
        for item in document["events"]
        if item["cutoverEventId"] == cutover_event_id
    ]
