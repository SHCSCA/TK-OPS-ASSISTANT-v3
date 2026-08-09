from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine


def freeze_browser_instances(engine: Engine) -> None:
    with engine.connect() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        connection.commit()
        try:
            with connection.begin():
                connection.execute(
                    text(
                        """
                        CREATE TEMP TABLE browser_instances_legacy_frozen AS
                        SELECT
                            id, workspace_id, name, profile_path, status,
                            process_id, debug_port, debug_host, runtime_mode,
                            executable_path, runtime_evidence_json,
                            last_checked_at, last_started_at, last_stopped_at,
                            error_code, error_message, created_at, updated_at
                        FROM browser_instances
                        """
                    )
                )
                connection.execute(text("DROP TABLE browser_instances"))
                connection.execute(
                    text(
                        """
                        CREATE TABLE browser_instances (
                            id VARCHAR NOT NULL,
                            workspace_id VARCHAR NOT NULL,
                            name TEXT NOT NULL,
                            profile_path TEXT NOT NULL,
                            status VARCHAR NOT NULL,
                            process_id INTEGER,
                            debug_port INTEGER,
                            debug_host VARCHAR,
                            runtime_mode VARCHAR,
                            executable_path TEXT,
                            runtime_evidence_json TEXT,
                            last_checked_at DATETIME,
                            last_started_at DATETIME,
                            last_stopped_at DATETIME,
                            error_code VARCHAR,
                            error_message TEXT,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                            PRIMARY KEY (id),
                            FOREIGN KEY(workspace_id)
                                REFERENCES device_workspaces (id) ON DELETE CASCADE,
                            UNIQUE (profile_path)
                        )
                        """
                    )
                )
                connection.execute(
                    text(
                        """
                        INSERT INTO browser_instances (
                            id, workspace_id, name, profile_path, status,
                            process_id, debug_port, debug_host, runtime_mode,
                            executable_path, runtime_evidence_json,
                            last_checked_at, last_started_at, last_stopped_at,
                            error_code, error_message, created_at, updated_at
                        )
                        SELECT * FROM browser_instances_legacy_frozen
                        """
                    )
                )
                connection.execute(text("DROP TABLE browser_instances_legacy_frozen"))
        finally:
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
            connection.commit()


def freeze_execution_bindings(engine: Engine) -> None:
    with engine.connect() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        connection.commit()
        try:
            with connection.begin():
                connection.execute(
                    text(
                        """
                        CREATE TEMP TABLE execution_bindings_legacy_frozen AS
                        SELECT id, account_id, device_workspace_id, status,
                               source, metadata_json, created_at, updated_at
                        FROM execution_bindings
                        """
                    )
                )
                connection.execute(text("DROP TABLE execution_bindings"))
                connection.execute(
                    text(
                        """
                        CREATE TABLE execution_bindings (
                            id VARCHAR NOT NULL,
                            account_id VARCHAR NOT NULL,
                            device_workspace_id VARCHAR NOT NULL,
                            status VARCHAR NOT NULL,
                            source VARCHAR,
                            metadata_json TEXT,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                            PRIMARY KEY (id),
                            FOREIGN KEY(account_id)
                                REFERENCES accounts (id) ON DELETE CASCADE,
                            FOREIGN KEY(device_workspace_id)
                                REFERENCES device_workspaces (id) ON DELETE CASCADE
                        )
                        """
                    )
                )
                connection.execute(
                    text(
                        """
                        INSERT INTO execution_bindings (
                            id, account_id, device_workspace_id, status,
                            source, metadata_json, created_at, updated_at
                        )
                        SELECT * FROM execution_bindings_legacy_frozen
                        """
                    )
                )
                connection.execute(text("DROP TABLE execution_bindings_legacy_frozen"))
        finally:
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
            connection.commit()


def freeze_system_config(engine: Engine) -> None:
    with engine.connect() as connection:
        with connection.begin():
            connection.execute(
                text(
                    """
                    CREATE TEMP TABLE system_config_legacy_frozen AS
                    SELECT id, document, revision, updated_at FROM system_config
                    """
                )
            )
            connection.execute(text("DROP TABLE system_config"))
            connection.execute(
                text(
                    """
                    CREATE TABLE system_config (
                        id INTEGER NOT NULL,
                        document TEXT NOT NULL,
                        revision INTEGER NOT NULL,
                        updated_at TEXT NOT NULL,
                        PRIMARY KEY (id),
                        CHECK (id = 1)
                    )
                    """
                )
            )
            connection.execute(
                text(
                    """
                    INSERT INTO system_config (
                        id, document, revision, updated_at
                    )
                    SELECT * FROM system_config_legacy_frozen
                    """
                )
            )
            connection.execute(text("DROP TABLE system_config_legacy_frozen"))
