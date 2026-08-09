from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.engine import Engine

from persistence.legacy_schema_common import table_columns
from persistence.legacy_schema_p0_freeze_runtime import (
    freeze_browser_instances,
    freeze_execution_bindings,
    freeze_system_config,
)

log = logging.getLogger(__name__)


def freeze_p0_legacy_extensions(engine: Engine) -> None:
    """将当前 ORM 扩展字段收回到冻结的 pre-P0 legacy cohort。"""

    try:
        if _has_any_column(
            engine,
            "accounts",
            {
                "platform_account_id",
                "wizard_completed_at",
                "status_reason_code",
                "last_used_at",
                "last_health_checked_at",
                "archived_at",
                "revision",
            },
        ):
            _freeze_accounts(engine)
        if _has_any_column(engine, "device_workspaces", {"account_id"}):
            _freeze_device_workspaces(engine)
        if _has_any_column(engine, "browser_instances", {"account_id"}):
            freeze_browser_instances(engine)
        if _has_any_column(engine, "execution_bindings", {"browser_instance_id"}):
            freeze_execution_bindings(engine)
        if _has_any_column(engine, "system_config", {"ai_config_revision"}):
            freeze_system_config(engine)
    except Exception as exc:
        log.exception("冻结 pre-P0 legacy 结构失败")
        raise RuntimeError("冻结 pre-P0 legacy 结构失败") from exc


def _has_any_column(
    engine: Engine,
    table_name: str,
    column_names: set[str],
) -> bool:
    with engine.connect() as connection:
        return bool(table_columns(connection, table_name) & column_names)


def _freeze_accounts(engine: Engine) -> None:
    fallback_time = datetime.now(UTC).isoformat()
    with engine.connect() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        connection.commit()
        try:
            with connection.begin():
                connection.execute(
                    text(
                        """
                        CREATE TEMP TABLE accounts_legacy_frozen AS
                        SELECT
                            id,
                            COALESCE(NULLIF(name, ''), id) AS name,
                            COALESCE(NULLIF(platform, ''), 'tiktok') AS platform,
                            username,
                            avatar_url,
                            COALESCE(NULLIF(status, ''), 'active') AS status,
                            auth_expires_at,
                            follower_count,
                            following_count,
                            video_count,
                            tags,
                            notes,
                            last_validated_at,
                            COALESCE(NULLIF(created_at, ''), :fallback_time) AS created_at,
                            COALESCE(NULLIF(updated_at, ''), NULLIF(created_at, ''), :fallback_time)
                                AS updated_at
                        FROM accounts
                        """
                    ),
                    {"fallback_time": fallback_time},
                )
                connection.execute(text("DROP TABLE accounts"))
                connection.execute(
                    text(
                        """
                        CREATE TABLE accounts (
                            id VARCHAR NOT NULL,
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
                            updated_at TEXT NOT NULL,
                            PRIMARY KEY (id)
                        )
                        """
                    )
                )
                connection.execute(
                    text(
                        """
                        INSERT INTO accounts (
                            id, name, platform, username, avatar_url, status,
                            auth_expires_at, follower_count, following_count,
                            video_count, tags, notes, last_validated_at,
                            created_at, updated_at
                        )
                        SELECT * FROM accounts_legacy_frozen
                        """
                    )
                )
                connection.execute(text("DROP TABLE accounts_legacy_frozen"))
        finally:
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
            connection.commit()


def _freeze_device_workspaces(engine: Engine) -> None:
    with engine.connect() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        connection.commit()
        try:
            with connection.begin():
                connection.execute(
                    text(
                        """
                        CREATE TEMP TABLE device_workspaces_legacy_frozen AS
                        SELECT id, name, root_path, status, error_count,
                               last_used_at, created_at, updated_at
                        FROM device_workspaces
                        """
                    )
                )
                connection.execute(text("DROP TABLE device_workspaces"))
                connection.execute(
                    text(
                        """
                        CREATE TABLE device_workspaces (
                            id VARCHAR NOT NULL,
                            name TEXT NOT NULL,
                            root_path TEXT NOT NULL,
                            status VARCHAR NOT NULL,
                            error_count INTEGER NOT NULL,
                            last_used_at DATETIME,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                            PRIMARY KEY (id),
                            UNIQUE (root_path)
                        )
                        """
                    )
                )
                connection.execute(
                    text(
                        """
                        INSERT INTO device_workspaces (
                            id, name, root_path, status, error_count,
                            last_used_at, created_at, updated_at
                        )
                        SELECT * FROM device_workspaces_legacy_frozen
                        """
                    )
                )
                connection.execute(text("DROP TABLE device_workspaces_legacy_frozen"))
        finally:
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
            connection.commit()
