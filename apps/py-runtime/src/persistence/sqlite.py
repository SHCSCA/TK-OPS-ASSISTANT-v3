from __future__ import annotations

import sqlite3
from pathlib import Path


def connect_sqlite(database_path: Path) -> sqlite3.Connection:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_schema(database_path: Path) -> None:
    with connect_sqlite(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS system_config (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                document TEXT NOT NULL,
                revision INTEGER NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
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
            """
        )
        connection.commit()
