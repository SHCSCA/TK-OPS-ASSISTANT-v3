from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.engine import Engine

from persistence.legacy_schema_common import (
    has_blocking_legacy_asset_columns,
    table_columns,
    table_info,
)
from persistence.legacy_schema_rebuilds import rebuild_legacy_asset_table


def repair_legacy_media_schemas(engine: Engine) -> None:
    _repair_legacy_script_version_schema(engine)
    _repair_legacy_project_schema(engine)
    _repair_legacy_voice_track_schema(engine)
    _repair_legacy_subtitle_track_schema(engine)
    _repair_legacy_asset_schema(engine)
    _repair_legacy_render_task_schema(engine)
    _repair_legacy_publish_plan_schema(engine)


def _repair_legacy_project_schema(engine: Engine) -> None:
    # B-01 软删除：为遗留 projects 表补齐 deleted_at 列
    required_columns = {
        "deleted_at": "TEXT",
    }

    with engine.begin() as connection:
        columns = table_columns(connection, "projects")
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
        columns = table_columns(connection, "script_versions")
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
        columns = table_columns(connection, "assets")
        if not columns:
            return

        for column_name, column_sql in required_columns.items():
            if column_name in columns:
                continue
            connection.execute(
                text(f"ALTER TABLE assets ADD COLUMN {column_name} {column_sql}")
            )

        repaired_columns = table_columns(connection, "assets")
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

        needs_rebuild = has_blocking_legacy_asset_columns(connection)

    if needs_rebuild:
        rebuild_legacy_asset_table(engine)


def _repair_legacy_voice_track_schema(engine: Engine) -> None:
    required_columns = {
        "version": "INTEGER NOT NULL DEFAULT 1",
        "config_json": "TEXT NOT NULL DEFAULT '{}'",
        "updated_at": "TEXT NOT NULL DEFAULT ''",
    }

    fallback_time = datetime.now(UTC).isoformat()

    with engine.begin() as connection:
        columns = table_columns(connection, "voice_tracks")
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
        columns = table_columns(connection, "subtitle_tracks")
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
        "timeline_id": "VARCHAR",
        "preset": "TEXT NOT NULL DEFAULT '1080p'",
        "format": "TEXT NOT NULL DEFAULT 'mp4'",
        "started_at": "DATETIME",
        "finished_at": "DATETIME",
        "error_code": "TEXT",
        "error_message": "TEXT",
    }

    with engine.begin() as connection:
        columns = table_columns(connection, "render_tasks")
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
        columns = table_columns(connection, "publish_plans")
        if not columns:
            return
        existing_table_info = table_info(connection, "publish_plans")

        for column_name, column_sql in required_columns.items():
            if column_name in columns:
                continue
            connection.execute(
                text(f"ALTER TABLE publish_plans ADD COLUMN {column_name} {column_sql}")
            )

        datetime_columns = {
            "scheduled_at",
            "submitted_at",
            "published_at",
            "created_at",
            "updated_at",
        }
        for column_name in datetime_columns:
            if column_name not in table_columns(connection, "publish_plans"):
                continue
            fallback = "NULL"
            notnull = existing_table_info.get(column_name, {}).get("notnull", 0)
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
