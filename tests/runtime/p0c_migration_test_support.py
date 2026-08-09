from __future__ import annotations

import sqlite3
from pathlib import Path

from alembic.config import Config

HASH_A = "a" * 64
HASH_B = "b" * 64


def migration_config(database_path: Path) -> Config:
    runtime_root = Path(__file__).resolve().parents[2] / "apps" / "py-runtime"
    config = Config(str(runtime_root / "alembic.ini"))
    config.set_main_option("script_location", str(runtime_root / "alembic"))
    config.attributes["database_url"] = f"sqlite:///{database_path.as_posix()}"
    return config


def insert_account(
    connection: sqlite3.Connection,
    account_id: str,
    *,
    status: str,
    wizard_completed_at: str | None = None,
) -> None:
    connection.execute(
        """
        INSERT INTO accounts (
            id, name, platform, status, created_at, updated_at,
            wizard_completed_at, revision
        ) VALUES (?, ?, 'tiktok', ?, '2026-01-01', '2026-01-01', ?, 1)
        """,
        (account_id, account_id, status, wizard_completed_at),
    )


def insert_workspace_and_browser(
    connection: sqlite3.Connection,
    account_id: str,
) -> None:
    connection.execute(
        """
        INSERT INTO device_workspaces (
            id, name, root_path, status, error_count,
            created_at, updated_at, account_id
        ) VALUES (?, ?, ?, 'online', 0, '2026-01-01', '2026-01-01', ?)
        """,
        (
            f"workspace-{account_id}",
            account_id,
            f"C:/{account_id}",
            account_id,
        ),
    )
    connection.execute(
        """
        INSERT INTO browser_instances (
            id, workspace_id, name, profile_path, status,
            created_at, updated_at, account_id
        ) VALUES (?, ?, ?, ?, 'stopped', '2026-01-01', '2026-01-01', ?)
        """,
        (
            f"browser-{account_id}",
            f"workspace-{account_id}",
            account_id,
            f"C:/profile-{account_id}",
            account_id,
        ),
    )


def insert_real_binding_chain(
    connection: sqlite3.Connection,
    account_id: str,
) -> None:
    insert_workspace_and_browser(connection, account_id)
    insert_binding(
        connection,
        binding_id=f"binding-{account_id}",
        account_id=account_id,
        workspace_id=f"workspace-{account_id}",
        browser_id=f"browser-{account_id}",
    )
    insert_connection(
        connection,
        account_id=account_id,
        binding_id=f"binding-{account_id}",
    )


def insert_binding(
    connection: sqlite3.Connection,
    *,
    binding_id: str,
    account_id: str,
    workspace_id: str,
    browser_id: str,
) -> None:
    connection.execute(
        """
        INSERT INTO execution_bindings (
            id, account_id, device_workspace_id, status,
            created_at, updated_at, browser_instance_id
        ) VALUES (?, ?, ?, 'active', '2026-01-01', '2026-01-01', ?)
        """,
        (binding_id, account_id, workspace_id, browser_id),
    )


def insert_connection(
    connection: sqlite3.Connection,
    *,
    account_id: str,
    binding_id: str,
) -> None:
    connection.execute(
        """
        INSERT INTO account_connections (
            id, account_id, auth_status, health_status,
            active_execution_binding_id, revision, created_at, updated_at
        ) VALUES (?, ?, 'valid', 'ready', ?, 1, '2026-01-01', '2026-01-01')
        """,
        (f"connection-{account_id}", account_id, binding_id),
    )


def insert_knowledge_base(
    connection: sqlite3.Connection,
    account_id: str,
) -> None:
    connection.execute(
        """
        INSERT INTO account_knowledge_bases (
            id, account_id, status, rules_json, rules_version,
            index_revision, revision, created_at, updated_at
        ) VALUES (?, ?, 'empty', '{}', 0, 0, 1, '2026-01-01', '2026-01-01')
        """,
        (f"base-{account_id}", account_id),
    )


def insert_legacy_source(
    connection: sqlite3.Connection,
    *,
    source_id: str,
    account_id: str,
    kind: str,
    source_ref: str,
) -> None:
    connection.execute(
        """
        INSERT INTO knowledge_sources (
            id, account_id, knowledge_base_id, kind, name, source_ref,
            status, metadata_json, revision, created_at, updated_at
        ) VALUES (?, ?, ?, ?, '来源', ?, 'pending', '{}', 1,
                  '2026-01-01', '2026-01-01')
        """,
        (
            source_id,
            account_id,
            f"base-{account_id}",
            kind,
            source_ref,
        ),
    )


def insert_head_source(
    connection: sqlite3.Connection,
    *,
    source_id: str,
    account_id: str,
    source_mode: str,
    source_url: str | None,
) -> None:
    connection.execute(
        """
        INSERT INTO knowledge_sources (
            id, account_id, knowledge_base_id, kind, name, source_ref,
            status, metadata_json, revision, created_at, updated_at,
            source_mode, source_url
        ) VALUES (?, ?, ?, 'text', '来源', 'source:test', 'pending', '{}', 1,
                  '2026-01-01', '2026-01-01', ?, ?)
        """,
        (
            source_id,
            account_id,
            f"base-{account_id}",
            source_mode,
            source_url,
        ),
    )


def insert_snapshot(
    connection: sqlite3.Connection,
    *,
    snapshot_id: str,
    account_id: str,
    knowledge_base_id: str,
    positioning_profile_id: str | None = None,
    label: str | None = None,
) -> None:
    connection.execute(
        """
        INSERT INTO knowledge_snapshots (
            id, account_id, knowledge_base_id, snapshot_version,
            positioning_profile_id, rules_version, index_revision,
            source_manifest_json, content_hash, created_at, label
        ) VALUES (?, ?, ?, 1, ?, 0, 0, '[]', ?, '2026-01-01', ?)
        """,
        (
            snapshot_id,
            account_id,
            knowledge_base_id,
            positioning_profile_id,
            HASH_A,
            label,
        ),
    )


def insert_mutation(
    connection: sqlite3.Connection,
    *,
    record_id: str,
    scope: str,
    account_id: str | None,
    key_hash: str = HASH_A,
    request_hash: str = HASH_B,
) -> None:
    connection.execute(
        """
        INSERT INTO runtime_mutation_idempotency (
            id, scope, account_id, operation_name,
            idempotency_key_hash, request_hash, response_json,
            created_at, expires_at
        ) VALUES (?, ?, ?, 'accounts.create', ?, ?, '{}',
                  '2026-01-01T00:00:00Z', '2026-01-02T00:00:00Z')
        """,
        (record_id, scope, account_id, key_hash, request_hash),
    )


def table_names(database_path: Path) -> set[str]:
    with sqlite3.connect(database_path) as connection:
        return {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }


def column_names(database_path: Path, table_name: str) -> set[str]:
    with sqlite3.connect(database_path) as connection:
        return {
            str(row[1])
            for row in connection.execute(f'PRAGMA table_info("{table_name}")')
        }


def trigger_names(database_path: Path) -> set[str]:
    with sqlite3.connect(database_path) as connection:
        return {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'trigger'"
            )
        }


def database_version(database_path: Path) -> str:
    with sqlite3.connect(database_path) as connection:
        row = connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone()
    assert row is not None
    return str(row[0])


def rows(
    database_path: Path,
    query: str,
) -> list[tuple[object, ...]]:
    with sqlite3.connect(database_path) as connection:
        return [tuple(row) for row in connection.execute(query).fetchall()]
