from __future__ import annotations

from pathlib import Path

import pytest

from config.migration import (
    MigrationConfigurationError,
    resolve_migration_config,
)


def test_migration_config_uses_safe_data_directory_defaults(tmp_path: Path) -> None:
    database_path = (tmp_path / "runtime.db").resolve()

    config = resolve_migration_config(tmp_path, database_path, environ={})

    migration_root = tmp_path / ".runtime.db.migrations"
    assert config.backup_dir == (migration_root / "backups").resolve()
    assert config.lock_path == (migration_root / "database-migration.lock").resolve()
    assert config.backup_retention_count == 5
    assert config.lock_timeout_seconds == 30


def test_same_database_uses_same_default_lock_across_data_directories(
    tmp_path: Path,
) -> None:
    database_path = (tmp_path / "external" / "runtime.db").resolve()

    first = resolve_migration_config(tmp_path / "data-a", database_path, environ={})
    second = resolve_migration_config(tmp_path / "data-b", database_path, environ={})

    assert first.lock_path == second.lock_path
    assert first.backup_dir == second.backup_dir


def test_relative_migration_paths_are_anchored_to_database_migration_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = (tmp_path / "external" / "runtime.db").resolve()
    first_working_directory = tmp_path / "first-working-directory"
    second_working_directory = tmp_path / "second-working-directory"
    first_working_directory.mkdir()
    second_working_directory.mkdir()
    environment = {
        "TK_OPS_MIGRATION_BACKUP_DIR": "custom-backups",
        "TK_OPS_MIGRATION_LOCK_PATH": "custom.lock",
    }

    monkeypatch.chdir(first_working_directory)
    first = resolve_migration_config(tmp_path, database_path, environ=environment)
    monkeypatch.chdir(second_working_directory)
    second = resolve_migration_config(tmp_path, database_path, environ=environment)

    migration_root = database_path.parent / ".runtime.db.migrations"
    assert first == second
    assert first.backup_dir == (migration_root / "custom-backups").resolve()
    assert first.lock_path == (migration_root / "custom.lock").resolve()


def test_migration_config_rejects_lock_path_over_database(tmp_path: Path) -> None:
    database_path = (tmp_path / "runtime.db").resolve()

    with pytest.raises(MigrationConfigurationError, match="迁移锁不能覆盖"):
        resolve_migration_config(
            tmp_path,
            database_path,
            environ={"TK_OPS_MIGRATION_LOCK_PATH": str(database_path)},
        )


@pytest.mark.parametrize(
    ("variable_name", "value", "message"),
    [
        ("TK_OPS_MIGRATION_LOCK_TIMEOUT_SECONDS", "301", "0 到 300"),
        ("TK_OPS_MIGRATION_BACKUP_RETENTION", "0", "1 到 50"),
        ("TK_OPS_MIGRATION_BACKUP_RETENTION", "51", "1 到 50"),
    ],
)
def test_migration_config_rejects_out_of_range_values(
    variable_name: str,
    value: str,
    message: str,
    tmp_path: Path,
) -> None:
    with pytest.raises(MigrationConfigurationError, match=message):
        resolve_migration_config(
            tmp_path,
            tmp_path / "runtime.db",
            environ={variable_name: value},
        )
