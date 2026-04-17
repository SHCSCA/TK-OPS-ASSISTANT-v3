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
