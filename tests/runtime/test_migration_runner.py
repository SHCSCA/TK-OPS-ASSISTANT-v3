from __future__ import annotations

import hashlib
import os
import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config
import pytest

from config.migration import MigrationConfig
from persistence.engine import create_runtime_engine, initialize_domain_schema
from persistence.migration import (
    DATABASE_SCHEMA_UNSUPPORTED,
    MIGRATION_FAILED,
    DatabaseSchemaKind,
    RuntimeMigrationError,
    inspect_database_schema,
    run_startup_migrations,
)
import persistence.migration.runner as migration_runner

REVISION_0014 = "0014_magic_cut_suggestion_drafts"
REVISION_0022 = "0022_p0g_production_hardening"


def test_empty_database_is_initialized_and_second_run_is_read_only(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "runtime.db"
    config = _migration_config(tmp_path)

    first_report = run_startup_migrations(database_path, config)
    first_hash = _sha256(database_path)
    second_report = run_startup_migrations(database_path, config)

    assert first_report.previous_revision is None
    assert first_report.target_revision == REVISION_0022
    assert first_report.changed is True
    assert first_report.backup_database_id is None
    assert second_report.changed is False
    assert _sha256(database_path) == first_hash
    assert inspect_database_schema(database_path).revision == REVISION_0022


def test_read_only_head_validation_releases_database_handle(tmp_path: Path) -> None:
    database_path = tmp_path / "replaceable.db"
    replacement_path = tmp_path / "replaced.db"
    config = _migration_config(tmp_path)
    run_startup_migrations(database_path, config)

    report = run_startup_migrations(database_path, config)
    os.replace(database_path, replacement_path)

    assert report.changed is False
    assert replacement_path.is_file()
    assert not database_path.exists()


def test_unknown_schema_fails_closed_without_changing_database(tmp_path: Path) -> None:
    database_path = tmp_path / "unknown.db"
    with sqlite3.connect(database_path) as connection:
        connection.execute("CREATE TABLE unknown_data (id TEXT PRIMARY KEY)")
        connection.execute("INSERT INTO unknown_data (id) VALUES ('preserved')")
    before = _sha256(database_path)

    with pytest.raises(RuntimeMigrationError) as captured:
        run_startup_migrations(database_path, _migration_config(tmp_path))

    assert captured.value.error_code == DATABASE_SCHEMA_UNSUPPORTED
    assert captured.value.restored is False
    assert _sha256(database_path) == before
    assert "alembic_version" not in _tables(database_path)


def test_failed_upgrade_restores_versioned_database_backup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "versioned.db"
    command.upgrade(_alembic_config(database_path), REVISION_0014)

    def fail_after_partial_write(_: Config, __: str) -> None:
        with sqlite3.connect(database_path) as connection:
            connection.execute("CREATE TABLE migration_partial (id TEXT PRIMARY KEY)")
        raise RuntimeError("模拟迁移中断")

    monkeypatch.setattr(migration_runner.command, "upgrade", fail_after_partial_write)

    with pytest.raises(RuntimeMigrationError) as captured:
        run_startup_migrations(database_path, _migration_config(tmp_path))

    assert captured.value.error_code == MIGRATION_FAILED
    assert captured.value.restored is True
    assert inspect_database_schema(database_path).revision == REVISION_0014
    assert "migration_partial" not in _tables(database_path)
    assert any((_migration_config(tmp_path).backup_dir).iterdir())


def test_known_schema_v3_copy_is_stamped_backed_up_and_upgraded(
    tmp_path: Path,
) -> None:
    source = Path(__file__).resolve().parents[2] / ".runtime-data" / "runtime.db"
    if not source.is_file():
        pytest.skip("当前检出未包含冻结开发库，仅跳过 legacy 实物迁移")
    database_path = tmp_path / "legacy-v3.db"
    with sqlite3.connect(source) as source_connection:
        with sqlite3.connect(database_path) as destination_connection:
            source_connection.backup(destination_connection)

    report = run_startup_migrations(database_path, _migration_config(tmp_path))

    assert report.schema_kind == DatabaseSchemaKind.LEGACY_SCHEMA_V3.value
    assert report.previous_revision == "3"
    assert report.target_revision == REVISION_0022
    assert report.backup_database_id
    assert inspect_database_schema(database_path).revision == REVISION_0022


def test_old_factory_fresh_database_is_stamped_and_upgraded(tmp_path: Path) -> None:
    database_path = tmp_path / "fresh-runtime.db"
    engine = create_runtime_engine(database_path)
    initialize_domain_schema(engine)
    engine.dispose()
    assert (
        inspect_database_schema(database_path).kind
        is DatabaseSchemaKind.LEGACY_FRESH_RUNTIME
    )

    report = run_startup_migrations(database_path, _migration_config(tmp_path))

    assert report.schema_kind == DatabaseSchemaKind.LEGACY_FRESH_RUNTIME.value
    assert report.backup_database_id
    assert inspect_database_schema(database_path).revision == REVISION_0022


@pytest.mark.parametrize(
    "tamper_sql",
    [
        "DROP INDEX ix_runtime_tasks_status_updated",
        "DROP INDEX uq_runtime_tasks_system_idempotency",
        "DROP INDEX uq_runtime_mutation_system_idempotency",
        "DROP INDEX ix_knowledge_sources_account_mode_updated",
        "ALTER TABLE provider_profiles DROP COLUMN base_url",
        "ALTER TABLE knowledge_snapshots DROP COLUMN label",
        "DROP TABLE accounts",
        "DROP TRIGGER trg_knowledge_sources_account_base_insert",
        "DROP TRIGGER trg_account_connections_binding_insert",
        "CREATE VIEW unexpected_accounts_view AS SELECT id FROM accounts",
    ],
)
def test_versioned_head_with_incomplete_contract_fails_closed(
    tamper_sql: str,
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "tampered-head.db"
    command.upgrade(_alembic_config(database_path), "head")
    with sqlite3.connect(database_path) as connection:
        connection.execute(tamper_sql)
    before = _sha256(database_path)

    with pytest.raises(RuntimeMigrationError) as captured:
        run_startup_migrations(database_path, _migration_config(tmp_path))

    assert captured.value.error_code == DATABASE_SCHEMA_UNSUPPORTED
    assert _sha256(database_path) == before


def test_versioned_head_with_weakened_named_check_fails_closed(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "weakened-check-head.db"
    command.upgrade(_alembic_config(database_path), "head")
    expected_check = (
        "CONSTRAINT ck_runtime_tasks_account_scope "
        "CHECK ((scope = 'system' AND account_id IS NULL) OR "
        "(scope = 'account' AND account_id IS NOT NULL "
        "AND length(trim(account_id)) > 0))"
    )
    weakened_check = "CONSTRAINT ck_runtime_tasks_account_scope CHECK (1)"
    connection = sqlite3.connect(database_path)
    try:
        create_sql = str(
            connection.execute(
                "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'runtime_tasks'"
            ).fetchone()[0]
        )
        assert expected_check in create_sql
        connection.execute("PRAGMA writable_schema = ON")
        connection.execute(
            "UPDATE sqlite_master SET sql = ? WHERE type = 'table' AND name = 'runtime_tasks'",
            (create_sql.replace(expected_check, weakened_check),),
        )
        connection.execute("PRAGMA writable_schema = RESET")
        connection.commit()
    finally:
        connection.close()
    before = _sha256(database_path)

    with pytest.raises(RuntimeMigrationError) as captured:
        run_startup_migrations(database_path, _migration_config(tmp_path))

    assert captured.value.error_code == DATABASE_SCHEMA_UNSUPPORTED
    assert _sha256(database_path) == before


@pytest.mark.parametrize(
    ("object_type", "object_name", "needle", "replacement"),
    [
        (
            "trigger",
            "trg_knowledge_sources_account_base_insert",
            "WHEN NOT EXISTS (",
            "WHEN 0 AND NOT EXISTS (",
        ),
        (
            "index",
            "uq_runtime_mutation_system_idempotency",
            "WHERE scope = 'system' AND account_id IS NULL",
            "WHERE scope = 'system' AND account_id IS NULL AND 0",
        ),
    ],
)
def test_versioned_head_rejects_semantically_weakened_schema_sql(
    object_type: str,
    object_name: str,
    needle: str,
    replacement: str,
    tmp_path: Path,
) -> None:
    database_path = tmp_path / f"weakened-{object_type}-head.db"
    command.upgrade(_alembic_config(database_path), "head")
    connection = sqlite3.connect(database_path)
    try:
        row = connection.execute(
            """
            SELECT sql
            FROM sqlite_master
            WHERE type = ? AND name = ?
            """,
            (object_type, object_name),
        ).fetchone()
        assert row is not None
        create_sql = str(row[0])
        assert needle in create_sql
        connection.execute("PRAGMA writable_schema = ON")
        connection.execute(
            """
            UPDATE sqlite_master
            SET sql = ?
            WHERE type = ? AND name = ?
            """,
            (
                create_sql.replace(needle, replacement, 1),
                object_type,
                object_name,
            ),
        )
        connection.execute("PRAGMA writable_schema = RESET")
        connection.commit()
    finally:
        connection.close()
    before = _sha256(database_path)

    with pytest.raises(RuntimeMigrationError) as captured:
        run_startup_migrations(database_path, _migration_config(tmp_path))

    assert captured.value.error_code == DATABASE_SCHEMA_UNSUPPORTED
    assert _sha256(database_path) == before


def _migration_config(tmp_path: Path) -> MigrationConfig:
    return MigrationConfig(
        backup_dir=(tmp_path / "backups").resolve(),
        backup_retention_count=3,
        lock_path=(tmp_path / "migration.lock").resolve(),
        lock_timeout_seconds=1,
    )


def _alembic_config(database_path: Path) -> Config:
    runtime_root = Path(__file__).resolve().parents[2] / "apps" / "py-runtime"
    config = Config(str(runtime_root / "alembic.ini"))
    config.set_main_option("script_location", str(runtime_root / "alembic"))
    config.attributes["database_url"] = f"sqlite:///{database_path.as_posix()}"
    return config


def _tables(database_path: Path) -> set[str]:
    with sqlite3.connect(database_path) as connection:
        return {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }


def _sha256(database_path: Path) -> str:
    return hashlib.sha256(database_path.read_bytes()).hexdigest()
