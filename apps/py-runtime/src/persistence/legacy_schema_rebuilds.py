from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.engine import Engine

from persistence.legacy_schema_common import (
    column_expr,
    nullif_text_column_expr,
    table_columns,
)


def rebuild_legacy_account_table(engine: Engine) -> None:
    fallback_time = datetime.now(UTC).isoformat()

    with engine.connect() as connection:
        columns = table_columns(connection, "accounts")
        if not columns:
            return

        display_name_expr = nullif_text_column_expr(columns, "display_name")
        handle_expr = nullif_text_column_expr(columns, "handle")
        username_expr = nullif_text_column_expr(columns, "username")
        avatar_expr = nullif_text_column_expr(columns, "avatar_url")
        auth_expires_expr = nullif_text_column_expr(columns, "auth_expires_at")
        follower_count_expr = column_expr(columns, "follower_count")
        following_count_expr = column_expr(columns, "following_count")
        video_count_expr = column_expr(columns, "video_count")
        tags_expr = nullif_text_column_expr(columns, "tags")
        notes_expr = nullif_text_column_expr(columns, "notes")
        last_validated_expr = nullif_text_column_expr(columns, "last_validated_at")

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


def rebuild_legacy_device_workspace_table(engine: Engine) -> None:
    fallback_time = datetime.now(UTC).isoformat()

    with engine.connect() as connection:
        columns = table_columns(connection, "device_workspaces")
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


def rebuild_legacy_execution_binding_table(engine: Engine) -> None:
    fallback_time = datetime.now(UTC).isoformat()

    with engine.connect() as connection:
        columns = table_columns(connection, "execution_bindings")
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


def rebuild_legacy_asset_table(engine: Engine) -> None:
    fallback_time = datetime.now(UTC).isoformat()

    with engine.connect() as connection:
        columns = table_columns(connection, "assets")
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
