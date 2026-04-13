from __future__ import annotations

import sqlite3
from typing import Callable

# Historical reference for the pre-SQLAlchemy bootstrap path. New schema work
# should use the Alembic migrations under apps/py-runtime/alembic/.
Migration = Callable[[sqlite3.Connection], None]
SCHEMA_VERSION = 3


def apply_migrations(connection: sqlite3.Connection) -> None:
    connection.execute(
        '''
        CREATE TABLE IF NOT EXISTS schema_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        '''
    )

    current_version = _get_current_version(connection)
    for version, migration in enumerate(_migrations(), start=1):
        if version <= current_version:
            continue

        migration(connection)
        connection.execute(
            '''
            INSERT INTO schema_meta (key, value)
            VALUES ('schema_version', ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            ''',
            (str(version),),
        )


def _get_current_version(connection: sqlite3.Connection) -> int:
    row = connection.execute(
        "SELECT value FROM schema_meta WHERE key = 'schema_version'"
    ).fetchone()
    return int(row['value']) if row is not None else 0


def _migrations() -> list[Migration]:
    return [_migration_1, _migration_2, _migration_3]


def _migration_1(connection: sqlite3.Connection) -> None:
    connection.execute(
        '''
        CREATE TABLE IF NOT EXISTS system_config (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            document TEXT NOT NULL,
            revision INTEGER NOT NULL,
            updated_at TEXT NOT NULL
        )
        '''
    )
    connection.execute(
        '''
        CREATE TABLE IF NOT EXISTS license_grant (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            active INTEGER NOT NULL,
            restricted_mode INTEGER NOT NULL,
            machine_id TEXT NOT NULL,
            machine_bound INTEGER NOT NULL,
            activation_mode TEXT NOT NULL,
            masked_code TEXT NOT NULL,
            activated_at TEXT
        )
        '''
    )


def _migration_2(connection: sqlite3.Connection) -> None:
    connection.execute(
        '''
        CREATE TABLE IF NOT EXISTS session_context (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            current_project_id TEXT,
            updated_at TEXT NOT NULL
        )
        '''
    )
    connection.execute(
        '''
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT NOT NULL,
            current_script_version INTEGER NOT NULL,
            current_storyboard_version INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_accessed_at TEXT NOT NULL
        )
        '''
    )
    connection.execute(
        '''
        CREATE TABLE IF NOT EXISTS ai_capability_configs (
            capability_id TEXT PRIMARY KEY,
            enabled INTEGER NOT NULL,
            provider TEXT NOT NULL,
            model TEXT NOT NULL,
            agent_role TEXT NOT NULL,
            system_prompt TEXT NOT NULL,
            user_prompt_template TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        '''
    )
    connection.execute(
        '''
        CREATE TABLE IF NOT EXISTS ai_provider_settings (
            provider_id TEXT PRIMARY KEY,
            base_url TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        '''
    )
    connection.execute(
        '''
        CREATE TABLE IF NOT EXISTS ai_job_records (
            id TEXT PRIMARY KEY,
            project_id TEXT,
            capability_id TEXT NOT NULL,
            provider TEXT NOT NULL,
            model TEXT NOT NULL,
            status TEXT NOT NULL,
            error TEXT,
            duration_ms INTEGER,
            provider_request_id TEXT,
            created_at TEXT NOT NULL,
            completed_at TEXT,
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
        )
        '''
    )
    connection.execute(
        '''
        CREATE TABLE IF NOT EXISTS script_versions (
            project_id TEXT NOT NULL,
            revision INTEGER NOT NULL,
            source TEXT NOT NULL,
            content TEXT NOT NULL,
            provider TEXT,
            model TEXT,
            ai_job_id TEXT,
            created_at TEXT NOT NULL,
            PRIMARY KEY (project_id, revision),
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
            FOREIGN KEY(ai_job_id) REFERENCES ai_job_records(id) ON DELETE SET NULL
        )
        '''
    )
    connection.execute(
        '''
        CREATE TABLE IF NOT EXISTS storyboard_versions (
            project_id TEXT NOT NULL,
            revision INTEGER NOT NULL,
            based_on_script_revision INTEGER NOT NULL,
            source TEXT NOT NULL,
            scenes_json TEXT NOT NULL,
            provider TEXT,
            model TEXT,
            ai_job_id TEXT,
            created_at TEXT NOT NULL,
            PRIMARY KEY (project_id, revision),
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
            FOREIGN KEY(ai_job_id) REFERENCES ai_job_records(id) ON DELETE SET NULL
        )
        '''
    )


def _migration_3(connection: sqlite3.Connection) -> None:
    _add_column_if_missing(connection, "license_grant", "machine_code", "TEXT NOT NULL DEFAULT ''")
    _add_column_if_missing(connection, "license_grant", "license_type", "TEXT NOT NULL DEFAULT 'perpetual'")
    _add_column_if_missing(connection, "license_grant", "signed_payload", "TEXT NOT NULL DEFAULT ''")
    connection.execute(
        """
        UPDATE license_grant
        SET machine_code = machine_id
        WHERE machine_code = ''
        """
    )
    connection.execute(
        """
        UPDATE license_grant
        SET license_type = 'perpetual'
        WHERE license_type = ''
        """
    )


def _add_column_if_missing(
    connection: sqlite3.Connection,
    table_name: str,
    column_name: str,
    column_sql: str,
) -> None:
    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    existing_columns = {str(row["name"]) for row in rows}
    if column_name in existing_columns:
        return

    connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_sql}")
