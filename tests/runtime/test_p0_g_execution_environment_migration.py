from __future__ import annotations

import sqlite3
from pathlib import Path

from alembic import command
import pytest

from persistence.migration.target_contract import validate_target_schema_contract
from tests.runtime.p0c_migration_test_support import (
    column_names,
    database_version,
    insert_account,
    insert_binding,
    insert_workspace_and_browser,
    migration_config,
    rows,
)

REVISION_0020 = "0020_p0e_ai_vertical_chain"
REVISION_0021 = "0021_p0g_execution_environment_closure"
REVISION_0022 = "0022_p0g_production_hardening"
REVISION_0023 = "0023_p0h_real_ai_execution"


def test_0021_backfills_legacy_objects_as_untrusted_and_inactive(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "p0g-backfill.db"
    config = migration_config(database_path)
    command.upgrade(config, REVISION_0020)
    with sqlite3.connect(database_path) as connection:
        insert_account(connection, "account-p0g", status="unbound")
        insert_workspace_and_browser(connection, "account-p0g")
        insert_binding(
            connection,
            binding_id="binding-account-p0g",
            account_id="account-p0g",
            workspace_id="workspace-account-p0g",
            browser_id="browser-account-p0g",
        )
        connection.commit()

    command.upgrade(config, REVISION_0021)

    assert database_version(database_path) == REVISION_0021
    assert rows(
        database_path,
        "SELECT ownership_state, root_ref FROM device_workspaces",
    ) == [("needs_reauthorization", None)]
    assert rows(
        database_path,
        "SELECT ownership_state FROM browser_instances",
    ) == [("needs_reauthorization",)]
    assert rows(
        database_path,
        "SELECT status FROM execution_bindings",
    ) == [("inactive",)]
    assert {
        "root_ref",
        "ownership_state",
        "revision",
        "error_code",
        "error_log_id",
    } <= column_names(database_path, "device_workspaces")
    assert "account_login_sessions" in _table_names(database_path)


def test_fresh_head_database_matches_runtime_target_contract(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "p0g-head.db"
    command.upgrade(migration_config(database_path), "head")

    inspection = validate_target_schema_contract(
        database_path,
        target_revision=REVISION_0023,
    )

    assert inspection.revision == REVISION_0023
    assert {
        "last_task_id",
        "last_retry_of_task_id",
    } <= column_names(database_path, "execution_bindings")
    indexes = {
        row[1]
        for row in rows(
            database_path,
            "PRAGMA index_list('account_login_sessions')",
        )
    }
    assert {
        "ix_account_login_sessions_account_updated",
        "uq_account_login_sessions_active",
    } <= indexes


def test_0022_refuses_downgrade_when_recovery_evidence_exists(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "p0g-hardening-guard.db"
    config = migration_config(database_path)
    command.upgrade(config, REVISION_0022)
    with sqlite3.connect(database_path) as connection:
        insert_account(connection, "account-hardening", status="unbound")
        insert_workspace_and_browser(connection, "account-hardening")
        insert_binding(
            connection,
            binding_id="binding-hardening",
            account_id="account-hardening",
            workspace_id="workspace-account-hardening",
            browser_id="browser-account-hardening",
        )
        connection.execute(
            "UPDATE execution_bindings SET last_task_id = 'task-hardening'"
        )
        connection.commit()

    with pytest.raises(
        RuntimeError,
        match="P0G_HARDENING_DOWNGRADE_REQUIRES_BACKUP",
    ):
        command.downgrade(config, REVISION_0021)

    assert database_version(database_path) == REVISION_0022


def test_0021_refuses_downgrade_when_real_environment_data_exists(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "p0g-downgrade-guard.db"
    config = migration_config(database_path)
    command.upgrade(config, REVISION_0020)
    with sqlite3.connect(database_path) as connection:
        insert_account(connection, "account-p0g-guard", status="unbound")
        insert_workspace_and_browser(connection, "account-p0g-guard")
        insert_binding(
            connection,
            binding_id="binding-account-p0g-guard",
            account_id="account-p0g-guard",
            workspace_id="workspace-account-p0g-guard",
            browser_id="browser-account-p0g-guard",
        )
        connection.commit()
    command.upgrade(config, REVISION_0021)
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "UPDATE device_workspaces SET ownership_state = 'owned', "
            "root_ref = 'wr_guard', revision = 2"
        )
        connection.commit()

    with pytest.raises(RuntimeError, match="P0G_DOWNGRADE_REQUIRES_BACKUP"):
        command.downgrade(config, REVISION_0020)

    assert database_version(database_path) == REVISION_0021
    assert rows(
        database_path,
        "SELECT root_ref, ownership_state FROM device_workspaces",
    ) == [("wr_guard", "owned")]


def _table_names(database_path: Path) -> set[str]:
    return {
        row[0]
        for row in rows(
            database_path,
            "SELECT name FROM sqlite_master WHERE type = 'table'",
        )
    }
