from __future__ import annotations

import sqlite3
from pathlib import Path

from .migrations import apply_migrations


def connect_sqlite(database_path: Path) -> sqlite3.Connection:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA foreign_keys = ON')
    return connection


def initialize_schema(database_path: Path) -> None:
    with connect_sqlite(database_path) as connection:
        apply_migrations(connection)
        connection.commit()
