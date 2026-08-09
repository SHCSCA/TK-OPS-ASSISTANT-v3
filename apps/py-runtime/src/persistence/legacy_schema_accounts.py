from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.engine import Engine

from persistence.legacy_schema_common import (
    ensure_table_columns,
    has_blocking_legacy_account_columns,
    has_blocking_legacy_device_workspace_columns,
    has_blocking_legacy_execution_binding_columns,
)
from persistence.legacy_schema_rebuilds import (
    rebuild_legacy_account_table,
    rebuild_legacy_device_workspace_table,
    rebuild_legacy_execution_binding_table,
)
from persistence.legacy_schema_p0_freeze import freeze_p0_legacy_extensions


def repair_legacy_account_schemas(engine: Engine) -> None:
    _repair_legacy_account_schema(engine)
    _repair_legacy_device_workspace_schema(engine)
    _repair_legacy_browser_instance_schema(engine)
    _repair_legacy_execution_binding_schema(engine)
    _repair_legacy_automation_schema(engine)
    _repair_magic_cut_suggestion_schema(engine)
    freeze_p0_legacy_extensions(engine)


def _repair_legacy_account_schema(engine: Engine) -> None:
    required_columns = {
        "name": "TEXT NOT NULL DEFAULT ''",
        "platform": "VARCHAR NOT NULL DEFAULT 'tiktok'",
        "username": "TEXT",
        "avatar_url": "TEXT",
        "status": "VARCHAR NOT NULL DEFAULT 'active'",
        "auth_expires_at": "TEXT",
        "follower_count": "INTEGER",
        "following_count": "INTEGER",
        "video_count": "INTEGER",
        "tags": "TEXT",
        "notes": "TEXT",
        "last_validated_at": "TEXT",
        "created_at": "TEXT NOT NULL DEFAULT ''",
        "updated_at": "TEXT NOT NULL DEFAULT ''",
    }

    fallback_time = datetime.now(UTC).isoformat()

    with engine.begin() as connection:
        columns = ensure_table_columns(
            connection,
            "accounts",
            required_columns,
        )
        if columns is None:
            return

        if "display_name" in columns and "name" in columns:
            connection.execute(
                text(
                    """
                    UPDATE accounts
                    SET name = COALESCE(NULLIF(display_name, ''), NULLIF(name, ''))
                    WHERE (name IS NULL OR name = '')
                    """
                )
            )
        if "handle" in columns and "username" in columns:
            connection.execute(
                text(
                    """
                    UPDATE accounts
                    SET username = NULLIF(handle, '')
                    WHERE username IS NULL OR username = ''
                    """
                )
            )
        if "name" in columns:
            connection.execute(
                text(
                    """
                    UPDATE accounts
                    SET name = id
                    WHERE name IS NULL OR name = ''
                    """
                )
            )
        if "created_at" in columns:
            connection.execute(
                text(
                    """
                    UPDATE accounts
                    SET created_at = :fallback_time
                    WHERE created_at IS NULL OR created_at = ''
                    """
                ),
                {"fallback_time": fallback_time},
            )
        if "updated_at" in columns:
            connection.execute(
                text(
                    """
                    UPDATE accounts
                    SET updated_at = COALESCE(NULLIF(created_at, ''), :fallback_time)
                    WHERE updated_at IS NULL OR updated_at = ''
                    """
                ),
                {"fallback_time": fallback_time},
            )
        if "platform" in columns:
            connection.execute(
                text(
                    """
                    UPDATE accounts
                    SET platform = 'tiktok'
                    WHERE platform IS NULL OR platform = ''
                    """
                )
            )
        if "status" in columns:
            connection.execute(
                text(
                    """
                    UPDATE accounts
                    SET status = 'active'
                    WHERE status IS NULL OR status = ''
                    """
                )
            )

        needs_rebuild = has_blocking_legacy_account_columns(connection)

    if needs_rebuild:
        rebuild_legacy_account_table(engine)


def _repair_legacy_device_workspace_schema(engine: Engine) -> None:
    required_columns = {
        "error_count": "INTEGER NOT NULL DEFAULT 0",
        "last_used_at": "DATETIME",
        "updated_at": "DATETIME",
    }

    fallback_time = datetime.now(UTC).isoformat()

    with engine.begin() as connection:
        columns = ensure_table_columns(connection, "device_workspaces", required_columns)
        if columns is None:
            return

        if "updated_at" in columns:
            connection.execute(
                text(
                    """
                    UPDATE device_workspaces
                    SET updated_at = :fallback_time
                    WHERE updated_at IS NULL OR updated_at = ''
                    """
                ),
                {"fallback_time": fallback_time},
            )

        needs_rebuild = has_blocking_legacy_device_workspace_columns(connection)

    if needs_rebuild:
        rebuild_legacy_device_workspace_table(engine)


def _repair_legacy_browser_instance_schema(engine: Engine) -> None:
    required_columns = {
        "process_id": "INTEGER",
        "debug_port": "INTEGER",
        "debug_host": "VARCHAR",
        "runtime_mode": "VARCHAR",
        "executable_path": "TEXT",
        "runtime_evidence_json": "TEXT",
    }

    with engine.begin() as connection:
        ensure_table_columns(connection, "browser_instances", required_columns)


def _repair_legacy_execution_binding_schema(engine: Engine) -> None:
    required_columns = {
        "source": "VARCHAR",
        "metadata_json": "TEXT",
        "updated_at": "DATETIME",
    }

    fallback_time = datetime.now(UTC).isoformat()

    with engine.begin() as connection:
        columns = ensure_table_columns(connection, "execution_bindings", required_columns)
        if columns is None:
            return

        if "updated_at" in columns:
            connection.execute(
                text(
                    """
                    UPDATE execution_bindings
                    SET updated_at = COALESCE(NULLIF(created_at, ''), :fallback_time)
                    WHERE updated_at IS NULL OR updated_at = ''
                    """
                ),
                {"fallback_time": fallback_time},
            )

        needs_rebuild = has_blocking_legacy_execution_binding_columns(connection)

    if needs_rebuild:
        rebuild_legacy_execution_binding_table(engine)


def _repair_legacy_automation_schema(engine: Engine) -> None:
    required_columns = {
        "name": "TEXT NOT NULL DEFAULT ''",
    }

    with engine.begin() as connection:
        if (
            ensure_table_columns(connection, "automation_tasks", required_columns)
            is None
        ):
            return


def _repair_magic_cut_suggestion_schema(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS magic_cut_suggestion_drafts (
                    id VARCHAR PRIMARY KEY,
                    project_id VARCHAR NOT NULL,
                    timeline_id VARCHAR NOT NULL,
                    ai_job_id VARCHAR,
                    status VARCHAR NOT NULL,
                    summary TEXT NOT NULL,
                    operations_json TEXT NOT NULL,
                    timeline_version_token TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    applied_at TEXT,
                    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
                    FOREIGN KEY(timeline_id) REFERENCES timelines(id) ON DELETE CASCADE,
                    FOREIGN KEY(ai_job_id) REFERENCES ai_job_records(id) ON DELETE SET NULL
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_magic_cut_suggestions_project_timeline
                ON magic_cut_suggestion_drafts(project_id, timeline_id, created_at)
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_magic_cut_suggestions_status
                ON magic_cut_suggestion_drafts(status)
                """
            )
        )
