from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from domain.models import Base


def create_runtime_engine(database_path: Path) -> Engine:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        f"sqlite:///{database_path}",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _connection_record):  # type: ignore[no-untyped-def]
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.close()

    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


def initialize_domain_schema(engine: Engine) -> None:
    Base.metadata.create_all(engine)
    _repair_legacy_asset_schema(engine)
    _repair_legacy_render_task_schema(engine)
    _repair_legacy_publish_plan_schema(engine)
    _repair_legacy_account_schema(engine)
    _repair_legacy_device_workspace_schema(engine)
    _repair_legacy_automation_schema(engine)


def _repair_legacy_asset_schema(engine: Engine) -> None:
    required_columns = {
        "name": "TEXT NOT NULL DEFAULT ''",
        "type": "VARCHAR NOT NULL DEFAULT 'other'",
        "source": "VARCHAR NOT NULL DEFAULT 'local'",
        "group_id": "VARCHAR",
        "file_path": "TEXT",
        "file_size_bytes": "INTEGER",
        "duration_ms": "INTEGER",
        "thumbnail_path": "TEXT",
        "thumbnail_generated_at": "TEXT",
        "tags": "TEXT",
        "project_id": "VARCHAR",
        "metadata_json": "TEXT",
        "created_at": "TEXT NOT NULL DEFAULT ''",
        "updated_at": "TEXT NOT NULL DEFAULT ''",
    }

    needs_rebuild = False

    with engine.begin() as connection:
        columns = _table_columns(connection, "assets")
        if not columns:
            return

        for column_name, column_sql in required_columns.items():
            if column_name in columns:
                continue
            connection.execute(
                text(f"ALTER TABLE assets ADD COLUMN {column_name} {column_sql}")
            )

        repaired_columns = _table_columns(connection, "assets")
        if "file_name" in repaired_columns:
            connection.execute(
                text(
                    """
                    UPDATE assets
                    SET name = file_name
                    WHERE name = '' AND file_name IS NOT NULL AND file_name != ''
                    """
                )
            )
        if "kind" in repaired_columns:
            connection.execute(
                text(
                    """
                    UPDATE assets
                    SET type = kind
                    WHERE kind IS NOT NULL AND kind != ''
                    """
                )
            )

        fallback_time = datetime.now(UTC).isoformat()
        connection.execute(
            text(
                """
                UPDATE assets
                SET name = id
                WHERE name = ''
                """
            )
        )
        connection.execute(
            text(
                """
                UPDATE assets
                SET created_at = :fallback_time
                WHERE created_at = ''
                """
            ),
            {"fallback_time": fallback_time},
        )
        connection.execute(
            text(
                """
                UPDATE assets
                SET updated_at = created_at
                WHERE updated_at = ''
                """
            )
        )

        needs_rebuild = _has_blocking_legacy_asset_columns(connection)

    if needs_rebuild:
        _rebuild_legacy_asset_table(engine)


def _repair_legacy_render_task_schema(engine: Engine) -> None:
    required_columns = {
        "project_name": "TEXT",
        "preset": "TEXT NOT NULL DEFAULT '1080p'",
        "format": "TEXT NOT NULL DEFAULT 'mp4'",
        "started_at": "DATETIME",
        "finished_at": "DATETIME",
        "error_message": "TEXT",
    }

    with engine.begin() as connection:
        columns = _table_columns(connection, "render_tasks")
        if not columns:
            return

        for column_name, column_sql in required_columns.items():
            if column_name in columns:
                continue
            connection.execute(
                text(f"ALTER TABLE render_tasks ADD COLUMN {column_name} {column_sql}")
            )


def _repair_legacy_publish_plan_schema(engine: Engine) -> None:
    required_columns = {
        "title": "TEXT NOT NULL DEFAULT ''",
        "account_name": "TEXT",
        "video_asset_id": "VARCHAR",
        "submitted_at": "DATETIME",
        "published_at": "DATETIME",
        "error_message": "TEXT",
        "precheck_result_json": "TEXT",
        "updated_at": "DATETIME",
    }

    with engine.begin() as connection:
        columns = _table_columns(connection, "publish_plans")
        if not columns:
            return
        table_info = _table_info(connection, "publish_plans")

        for column_name, column_sql in required_columns.items():
            if column_name in columns:
                continue
            connection.execute(
                text(f"ALTER TABLE publish_plans ADD COLUMN {column_name} {column_sql}")
            )

        datetime_columns = {"scheduled_at", "submitted_at", "published_at", "created_at", "updated_at"}
        for column_name in datetime_columns:
            if column_name not in _table_columns(connection, "publish_plans"):
                continue
            fallback = "NULL"
            notnull = table_info.get(column_name, {}).get("notnull", 0)
            if notnull == 1:
                fallback = "COALESCE(NULLIF(created_at, ''), datetime('now'))"
            connection.execute(
                text(
                    f"""
                    UPDATE publish_plans
                    SET {column_name} = {fallback}
                    WHERE {column_name} = '' OR {column_name} IS NULL
                    """
                )
            )


def _repair_legacy_account_schema(engine: Engine) -> None:
    required_columns = {
        "name": "TEXT NOT NULL DEFAULT ''",
        "created_at": "TEXT NOT NULL DEFAULT ''",
        "updated_at": "TEXT NOT NULL DEFAULT ''",
    }

    fallback_time = datetime.now(UTC).isoformat()

    with engine.begin() as connection:
        columns = _ensure_table_columns(
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


def _repair_legacy_device_workspace_schema(engine: Engine) -> None:
    required_columns = {
        "error_count": "INTEGER NOT NULL DEFAULT 0",
        "updated_at": "DATETIME",
    }

    fallback_time = datetime.now(UTC).isoformat()

    with engine.begin() as connection:
        columns = _ensure_table_columns(connection, "device_workspaces", required_columns)
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


def _repair_legacy_automation_schema(engine: Engine) -> None:
    required_columns = {
        "name": "TEXT NOT NULL DEFAULT ''",
    }

    with engine.begin() as connection:
        if _ensure_table_columns(connection, "automation_tasks", required_columns) is None:
            return


def _ensure_table_columns(
    connection,
    table_name: str,
    required_columns: dict[str, str],
) -> set[str] | None:  # type: ignore[no-untyped-def]
    columns = _table_columns(connection, table_name)
    if not columns:
        return None

    for column_name, column_sql in required_columns.items():
        if column_name in columns:
            continue
        connection.execute(
            text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_sql}")
        )

    return _table_columns(connection, table_name)


def _table_info(connection, table_name: str) -> dict[str, dict[str, object]]:  # type: ignore[no-untyped-def]
    rows = connection.execute(text(f"PRAGMA table_info({table_name})")).mappings().all()
    return {
        str(row["name"]): {
            "notnull": int(row["notnull"]),
            "type": str(row["type"]),
        }
        for row in rows
    }


def _table_columns(connection, table_name: str) -> set[str]:  # type: ignore[no-untyped-def]
    rows = connection.execute(text(f"PRAGMA table_info({table_name})")).mappings().all()
    return {str(row["name"]) for row in rows}


def _has_blocking_legacy_asset_columns(connection) -> bool:  # type: ignore[no-untyped-def]
    rows = connection.execute(text("PRAGMA table_info(assets)")).mappings().all()
    legacy_columns = {"kind", "file_name", "mime_type"}
    return any(
        str(row["name"]) in legacy_columns and int(row["notnull"]) == 1
        for row in rows
    )


def _rebuild_legacy_asset_table(engine: Engine) -> None:
    fallback_time = datetime.now(UTC).isoformat()

    with engine.connect() as connection:
        columns = _table_columns(connection, "assets")
        kind_expr = "kind" if "kind" in columns else "NULL"
        file_name_expr = "file_name" if "file_name" in columns else "NULL"
        mime_type_expr = "mime_type" if "mime_type" in columns else "NULL"

        connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        connection.commit()

        try:
            with connection.begin():
                connection.execute(text("DROP TABLE IF EXISTS assets_repaired"))
                connection.execute(
                    text(
                        """
                        CREATE TABLE assets_repaired (
                            id VARCHAR PRIMARY KEY,
                            name TEXT NOT NULL,
                            type VARCHAR NOT NULL,
                            source VARCHAR NOT NULL,
                            group_id VARCHAR,
                            file_path TEXT,
                            file_size_bytes INTEGER,
                            duration_ms INTEGER,
                            thumbnail_path TEXT,
                            thumbnail_generated_at TEXT,
                            tags TEXT,
                            project_id VARCHAR,
                            metadata_json TEXT,
                            created_at TEXT NOT NULL,
                            updated_at TEXT NOT NULL,
                            kind VARCHAR,
                            file_name TEXT,
                            mime_type VARCHAR,
                            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE SET NULL
                        )
                        """
                    )
                )
                connection.execute(
                    text(
                        f"""
                        INSERT INTO assets_repaired (
                            id,
                            name,
                            type,
                            source,
                            group_id,
                            file_path,
                            file_size_bytes,
                            duration_ms,
                            thumbnail_path,
                            thumbnail_generated_at,
                            tags,
                            project_id,
                            metadata_json,
                            created_at,
                            updated_at,
                            kind,
                            file_name,
                            mime_type
                        )
                        SELECT
                            id,
                            COALESCE(NULLIF(name, ''), NULLIF({file_name_expr}, ''), id),
                            COALESCE(NULLIF(type, ''), NULLIF({kind_expr}, ''), 'other'),
                            COALESCE(NULLIF(source, ''), 'local'),
                            NULL,
                            file_path,
                            file_size_bytes,
                            duration_ms,
                            thumbnail_path,
                            NULL,
                            tags,
                            project_id,
                            metadata_json,
                            COALESCE(NULLIF(created_at, ''), :fallback_time),
                            COALESCE(NULLIF(updated_at, ''), NULLIF(created_at, ''), :fallback_time),
                            {kind_expr},
                            {file_name_expr},
                            {mime_type_expr}
                        FROM assets
                        """
                    ),
                    {"fallback_time": fallback_time},
                )
                connection.execute(text("DROP TABLE assets"))
                connection.execute(text("ALTER TABLE assets_repaired RENAME TO assets"))
        finally:
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
            connection.commit()
