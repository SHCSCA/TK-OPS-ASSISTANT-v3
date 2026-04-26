from __future__ import annotations

import json
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
    _repair_legacy_script_version_schema(engine)
    _repair_legacy_project_schema(engine)
    _repair_legacy_voice_track_schema(engine)
    _repair_legacy_subtitle_track_schema(engine)
    _repair_legacy_asset_schema(engine)
    _repair_legacy_render_task_schema(engine)
    _repair_legacy_publish_plan_schema(engine)
    _repair_legacy_account_schema(engine)
    _repair_legacy_device_workspace_schema(engine)
    _repair_legacy_execution_binding_schema(engine)
    _repair_legacy_automation_schema(engine)


def _repair_legacy_project_schema(engine: Engine) -> None:
    # B-01 软删除：为遗留 projects 表补齐 deleted_at 列
    required_columns = {
        "deleted_at": "TEXT",
    }

    with engine.begin() as connection:
        columns = _table_columns(connection, "projects")
        if not columns:
            return

        for column_name, column_sql in required_columns.items():
            if column_name in columns:
                continue
            connection.execute(
                text(f"ALTER TABLE projects ADD COLUMN {column_name} {column_sql}")
            )


def _repair_legacy_script_version_schema(engine: Engine) -> None:
    required_columns = {
        "format": "VARCHAR NOT NULL DEFAULT 'legacy_markdown'",
        "document_json": "TEXT",
    }

    with engine.begin() as connection:
        columns = _table_columns(connection, "script_versions")
        if not columns:
            return

        for column_name, column_sql in required_columns.items():
            if column_name in columns:
                continue
            connection.execute(
                text(f"ALTER TABLE script_versions ADD COLUMN {column_name} {column_sql}")
            )


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


def _repair_legacy_voice_track_schema(engine: Engine) -> None:
    required_columns = {
        "version": "INTEGER NOT NULL DEFAULT 1",
        "config_json": "TEXT NOT NULL DEFAULT '{}'",
        "updated_at": "TEXT NOT NULL DEFAULT ''",
    }

    fallback_time = datetime.now(UTC).isoformat()

    with engine.begin() as connection:
        columns = _table_columns(connection, "voice_tracks")
        if not columns:
            return

        for column_name, column_sql in required_columns.items():
            if column_name in columns:
                continue
            connection.execute(
                text(f"ALTER TABLE voice_tracks ADD COLUMN {column_name} {column_sql}")
            )

        rows = connection.execute(
            text(
                """
                SELECT
                    id,
                    source,
                    provider,
                    voice_name,
                    file_path,
                    status,
                    segments_json,
                    created_at,
                    updated_at,
                    version,
                    config_json
                FROM voice_tracks
                """
            )
        ).mappings().all()

        for row in rows:
            config_json = str(row.get("config_json") or "").strip()
            updated_at = str(row.get("updated_at") or "").strip()
            version = row.get("version")
            needs_update = False
            payload: dict[str, object] | None = None

            if config_json == "":
                segments_json = str(row.get("segments_json") or "[]")
                segment_count = 0
                try:
                    segments = json.loads(segments_json)
                except json.JSONDecodeError:
                    segments = []
                if isinstance(segments, list):
                    segment_count = len(segments)
                payload = {
                    "parameterSource": "legacy",
                    "profileId": None,
                    "provider": row.get("provider"),
                    "voiceId": None,
                    "voiceName": row.get("voice_name"),
                    "locale": None,
                    "model": None,
                    "speed": None,
                    "pitch": None,
                    "emotion": None,
                    "sourceText": None,
                    "sourceLineCount": segment_count or None,
                    "lastOperation": {
                        "kind": "legacy_backfill",
                        "status": row.get("status"),
                        "updatedAt": fallback_time,
                    },
                }
                needs_update = True

            if updated_at == "":
                updated_at = str(row.get("created_at") or fallback_time)
                needs_update = True

            if version is None or int(version) <= 0:
                version = 1
                needs_update = True

            if payload is not None:
                connection.execute(
                    text(
                        """
                        UPDATE voice_tracks
                        SET config_json = :config_json,
                            version = :version,
                            updated_at = :updated_at
                        WHERE id = :track_id
                        """
                    ),
                    {
                        "track_id": row["id"],
                        "config_json": json.dumps(payload, ensure_ascii=False),
                        "version": int(version),
                        "updated_at": updated_at,
                    },
                )
                continue

            if needs_update:
                connection.execute(
                    text(
                        """
                        UPDATE voice_tracks
                        SET version = :version,
                            updated_at = :updated_at
                        WHERE id = :track_id
                        """
                    ),
                    {
                        "track_id": row["id"],
                        "version": int(version),
                        "updated_at": updated_at,
                    },
                )


def _repair_legacy_subtitle_track_schema(engine: Engine) -> None:
    required_columns = {
        "metadata_json": "TEXT NOT NULL DEFAULT '{}'",
        "updated_at": "TEXT NOT NULL DEFAULT ''",
    }

    fallback_time = datetime.now(UTC).isoformat()

    with engine.begin() as connection:
        columns = _table_columns(connection, "subtitle_tracks")
        if not columns:
            return

        for column_name, column_sql in required_columns.items():
            if column_name in columns:
                continue
            connection.execute(
                text(f"ALTER TABLE subtitle_tracks ADD COLUMN {column_name} {column_sql}")
            )

        rows = connection.execute(
            text(
                """
                SELECT
                    id,
                    status,
                    segments_json,
                    created_at,
                    updated_at,
                    metadata_json
                FROM subtitle_tracks
                """
            )
        ).mappings().all()

        for row in rows:
            metadata_json = str(row.get("metadata_json") or "").strip()
            updated_at = str(row.get("updated_at") or "").strip()
            needs_update = False

            if updated_at == "":
                updated_at = str(row.get("created_at") or fallback_time)
                needs_update = True

            if metadata_json == "":
                segments_json = str(row.get("segments_json") or "[]")
                try:
                    segments = json.loads(segments_json)
                except json.JSONDecodeError:
                    segments = []
                has_valid_timecodes = False
                if isinstance(segments, list):
                    has_valid_timecodes = all(
                        isinstance(item, dict)
                        and item.get("startMs") is not None
                        and item.get("endMs") is not None
                        and int(item.get("endMs")) > int(item.get("startMs"))
                        for item in segments
                    )
                payload = {
                    "sourceVoice": None,
                    "alignment": {
                        "status": "aligned" if has_valid_timecodes else "needs_alignment",
                        "diffSummary": None,
                        "errorCode": None if has_valid_timecodes else "subtitle.timecode_incomplete",
                        "errorMessage": None if has_valid_timecodes else "字幕片段缺少有效时间码，无法完成对齐或导出。",
                        "nextAction": (
                            "可继续导出字幕，或回到字幕编辑中微调文案。"
                            if has_valid_timecodes
                            else "请重新执行字幕对齐，补齐字幕时间码。"
                        ),
                        "updatedAt": updated_at,
                    },
                }
                connection.execute(
                    text(
                        """
                        UPDATE subtitle_tracks
                        SET metadata_json = :metadata_json,
                            updated_at = :updated_at
                        WHERE id = :track_id
                        """
                    ),
                    {
                        "track_id": row["id"],
                        "metadata_json": json.dumps(payload, ensure_ascii=False),
                        "updated_at": updated_at,
                    },
                )
                continue

            if needs_update:
                connection.execute(
                    text(
                        """
                        UPDATE subtitle_tracks
                        SET updated_at = :updated_at
                        WHERE id = :track_id
                        """
                    ),
                    {
                        "track_id": row["id"],
                        "updated_at": updated_at,
                    },
                )


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

        needs_rebuild = _has_blocking_legacy_account_columns(connection)

    if needs_rebuild:
        _rebuild_legacy_account_table(engine)


def _repair_legacy_device_workspace_schema(engine: Engine) -> None:
    required_columns = {
        "error_count": "INTEGER NOT NULL DEFAULT 0",
        "last_used_at": "DATETIME",
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

        needs_rebuild = _has_blocking_legacy_device_workspace_columns(connection)

    if needs_rebuild:
        _rebuild_legacy_device_workspace_table(engine)


def _repair_legacy_execution_binding_schema(engine: Engine) -> None:
    required_columns = {
        "source": "VARCHAR",
        "metadata_json": "TEXT",
        "updated_at": "DATETIME",
    }

    fallback_time = datetime.now(UTC).isoformat()

    with engine.begin() as connection:
        columns = _ensure_table_columns(connection, "execution_bindings", required_columns)
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

        needs_rebuild = _has_blocking_legacy_execution_binding_columns(connection)

    if needs_rebuild:
        _rebuild_legacy_execution_binding_table(engine)


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


def _column_expr(columns: set[str], column_name: str) -> str:
    return column_name if column_name in columns else "NULL"


def _nullif_text_column_expr(columns: set[str], column_name: str) -> str:
    return f"NULLIF({column_name}, '')" if column_name in columns else "NULL"


def _has_blocking_legacy_asset_columns(connection) -> bool:  # type: ignore[no-untyped-def]
    rows = connection.execute(text("PRAGMA table_info(assets)")).mappings().all()
    legacy_columns = {"kind", "file_name", "mime_type"}
    return any(
        str(row["name"]) in legacy_columns and int(row["notnull"]) == 1
        for row in rows
    )


def _has_blocking_legacy_account_columns(connection) -> bool:  # type: ignore[no-untyped-def]
    rows = connection.execute(text("PRAGMA table_info(accounts)")).mappings().all()
    legacy_columns = {"handle", "display_name", "group_name", "source", "metadata_json"}
    for row in rows:
        column_name = str(row["name"])
        if column_name in legacy_columns and int(row["notnull"]) == 1:
            if row["dflt_value"] in (None, ""):
                return True
    return False


def _has_blocking_legacy_device_workspace_columns(connection) -> bool:  # type: ignore[no-untyped-def]
    rows = connection.execute(text("PRAGMA table_info(device_workspaces)")).mappings().all()
    legacy_columns = {"device_type", "browser_profile", "health_json", "source"}
    for row in rows:
        column_name = str(row["name"])
        if column_name in legacy_columns and int(row["notnull"]) == 1:
            return True
        if column_name in {"created_at", "updated_at"} and int(row["notnull"]) == 1:
            if row["dflt_value"] in (None, ""):
                return True
    return False


def _has_blocking_legacy_execution_binding_columns(connection) -> bool:  # type: ignore[no-untyped-def]
    rows = connection.execute(text("PRAGMA table_info(execution_bindings)")).mappings().all()
    nullable_columns = {"source", "metadata_json"}
    for row in rows:
        column_name = str(row["name"])
        if column_name in nullable_columns and int(row["notnull"]) == 1:
            return True
        if column_name in {"created_at", "updated_at"} and int(row["notnull"]) == 1:
            if row["dflt_value"] in (None, ""):
                return True
    return False


def _rebuild_legacy_account_table(engine: Engine) -> None:
    fallback_time = datetime.now(UTC).isoformat()

    with engine.connect() as connection:
        columns = _table_columns(connection, "accounts")
        if not columns:
            return

        display_name_expr = _nullif_text_column_expr(columns, "display_name")
        handle_expr = _nullif_text_column_expr(columns, "handle")
        username_expr = _nullif_text_column_expr(columns, "username")
        avatar_expr = _nullif_text_column_expr(columns, "avatar_url")
        auth_expires_expr = _nullif_text_column_expr(columns, "auth_expires_at")
        follower_count_expr = _column_expr(columns, "follower_count")
        following_count_expr = _column_expr(columns, "following_count")
        video_count_expr = _column_expr(columns, "video_count")
        tags_expr = _nullif_text_column_expr(columns, "tags")
        notes_expr = _nullif_text_column_expr(columns, "notes")
        last_validated_expr = _nullif_text_column_expr(columns, "last_validated_at")

        connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        connection.commit()

        try:
            with connection.begin():
                connection.execute(text("DROP TABLE IF EXISTS accounts_repaired"))
                connection.execute(
                    text(
                        """
                        CREATE TABLE accounts_repaired (
                            id VARCHAR PRIMARY KEY,
                            name TEXT NOT NULL,
                            platform VARCHAR NOT NULL,
                            username TEXT,
                            avatar_url TEXT,
                            status VARCHAR NOT NULL,
                            auth_expires_at TEXT,
                            follower_count INTEGER,
                            following_count INTEGER,
                            video_count INTEGER,
                            tags TEXT,
                            notes TEXT,
                            last_validated_at TEXT,
                            created_at TEXT NOT NULL,
                            updated_at TEXT NOT NULL
                        )
                        """
                    )
                )
                connection.execute(
                    text(
                        f"""
                        INSERT INTO accounts_repaired (
                            id,
                            name,
                            platform,
                            username,
                            avatar_url,
                            status,
                            auth_expires_at,
                            follower_count,
                            following_count,
                            video_count,
                            tags,
                            notes,
                            last_validated_at,
                            created_at,
                            updated_at
                        )
                        SELECT
                            id,
                            COALESCE(NULLIF(name, ''), {display_name_expr}, {handle_expr}, id),
                            COALESCE(NULLIF(platform, ''), 'tiktok'),
                            COALESCE({username_expr}, {handle_expr}),
                            {avatar_expr},
                            COALESCE(NULLIF(status, ''), 'active'),
                            {auth_expires_expr},
                            {follower_count_expr},
                            {following_count_expr},
                            {video_count_expr},
                            {tags_expr},
                            {notes_expr},
                            {last_validated_expr},
                            COALESCE(NULLIF(created_at, ''), :fallback_time),
                            COALESCE(NULLIF(updated_at, ''), NULLIF(created_at, ''), :fallback_time)
                        FROM accounts
                        """
                    ),
                    {"fallback_time": fallback_time},
                )
                connection.execute(text("DROP TABLE accounts"))
                connection.execute(text("ALTER TABLE accounts_repaired RENAME TO accounts"))
        finally:
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
            connection.commit()


def _rebuild_legacy_device_workspace_table(engine: Engine) -> None:
    fallback_time = datetime.now(UTC).isoformat()

    with engine.connect() as connection:
        columns = _table_columns(connection, "device_workspaces")
        if not columns:
            return

        last_used_expr = "last_used_at" if "last_used_at" in columns else "NULL"
        error_count_expr = "error_count" if "error_count" in columns else "0"
        updated_at_expr = "updated_at" if "updated_at" in columns else "NULL"

        connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        connection.commit()

        try:
            with connection.begin():
                connection.execute(text("DROP TABLE IF EXISTS device_workspaces_repaired"))
                connection.execute(
                    text(
                        """
                        CREATE TABLE device_workspaces_repaired (
                            id VARCHAR PRIMARY KEY,
                            name TEXT NOT NULL,
                            root_path TEXT NOT NULL UNIQUE,
                            status VARCHAR NOT NULL,
                            error_count INTEGER NOT NULL DEFAULT 0,
                            last_used_at DATETIME,
                            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                        )
                        """
                    )
                )
                connection.execute(
                    text(
                        f"""
                        INSERT INTO device_workspaces_repaired (
                            id,
                            name,
                            root_path,
                            status,
                            error_count,
                            last_used_at,
                            created_at,
                            updated_at
                        )
                        SELECT
                            id,
                            COALESCE(NULLIF(name, ''), id),
                            COALESCE(NULLIF(root_path, ''), id),
                            COALESCE(NULLIF(status, ''), 'offline'),
                            COALESCE({error_count_expr}, 0),
                            {last_used_expr},
                            COALESCE(NULLIF(created_at, ''), :fallback_time),
                            COALESCE(NULLIF({updated_at_expr}, ''), NULLIF(created_at, ''), :fallback_time)
                        FROM device_workspaces
                        """
                    ),
                    {"fallback_time": fallback_time},
                )
                connection.execute(text("DROP TABLE device_workspaces"))
                connection.execute(
                    text("ALTER TABLE device_workspaces_repaired RENAME TO device_workspaces")
                )
        finally:
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
            connection.commit()


def _rebuild_legacy_execution_binding_table(engine: Engine) -> None:
    fallback_time = datetime.now(UTC).isoformat()

    with engine.connect() as connection:
        columns = _table_columns(connection, "execution_bindings")
        if not columns:
            return

        source_expr = "source" if "source" in columns else "NULL"
        metadata_expr = "metadata_json" if "metadata_json" in columns else "NULL"
        updated_at_expr = "updated_at" if "updated_at" in columns else "NULL"

        connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        connection.commit()

        try:
            with connection.begin():
                connection.execute(text("DROP TABLE IF EXISTS execution_bindings_repaired"))
                connection.execute(
                    text(
                        """
                        CREATE TABLE execution_bindings_repaired (
                            id VARCHAR PRIMARY KEY,
                            account_id VARCHAR NOT NULL,
                            device_workspace_id VARCHAR NOT NULL,
                            status VARCHAR NOT NULL,
                            source VARCHAR,
                            metadata_json TEXT,
                            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE CASCADE,
                            FOREIGN KEY(device_workspace_id) REFERENCES device_workspaces(id) ON DELETE CASCADE
                        )
                        """
                    )
                )
                connection.execute(
                    text(
                        f"""
                        INSERT INTO execution_bindings_repaired (
                            id,
                            account_id,
                            device_workspace_id,
                            status,
                            source,
                            metadata_json,
                            created_at,
                            updated_at
                        )
                        SELECT
                            id,
                            account_id,
                            device_workspace_id,
                            COALESCE(NULLIF(status, ''), 'active'),
                            NULLIF({source_expr}, ''),
                            NULLIF({metadata_expr}, ''),
                            COALESCE(NULLIF(created_at, ''), :fallback_time),
                            COALESCE(NULLIF({updated_at_expr}, ''), NULLIF(created_at, ''), :fallback_time)
                        FROM execution_bindings
                        """
                    ),
                    {"fallback_time": fallback_time},
                )
                connection.execute(text("DROP TABLE execution_bindings"))
                connection.execute(
                    text("ALTER TABLE execution_bindings_repaired RENAME TO execution_bindings")
                )
        finally:
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
            connection.commit()


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
