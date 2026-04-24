from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import text

SRC_DIR = Path(__file__).resolve().parents[2] / "apps" / "py-runtime" / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from persistence.engine import create_runtime_engine, initialize_domain_schema


def test_device_workspace_legacy_schema_repair_adds_last_used_at(tmp_path: Path) -> None:
    engine = create_runtime_engine(tmp_path / "runtime.db")
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE device_workspaces (
                    id VARCHAR PRIMARY KEY,
                    name TEXT NOT NULL,
                    device_type VARCHAR NOT NULL,
                    root_path TEXT NOT NULL UNIQUE,
                    browser_profile TEXT NOT NULL,
                    status VARCHAR NOT NULL DEFAULT 'offline',
                    health_json TEXT NOT NULL,
                    source VARCHAR NOT NULL,
                    error_count INTEGER NOT NULL DEFAULT 0,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME
                )
                """
            )
        )

    initialize_domain_schema(engine)

    with engine.begin() as connection:
        columns = {
            str(row["name"])
            for row in connection.execute(text("PRAGMA table_info(device_workspaces)")).mappings()
        }
        connection.execute(
            text(
                """
                INSERT INTO device_workspaces (id, name, root_path, status, error_count)
                VALUES ('workspace-1', 'Workspace 1', 'C:/tmp/workspace-1', 'offline', 0)
                """
            )
        )

    assert "last_used_at" in columns
    assert "device_type" not in columns
    assert "browser_profile" not in columns
    assert "health_json" not in columns
    assert "source" not in columns


def test_execution_binding_legacy_schema_repair_allows_nullable_metadata(
    tmp_path: Path,
) -> None:
    engine = create_runtime_engine(tmp_path / "runtime.db")
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE execution_bindings (
                    id VARCHAR PRIMARY KEY,
                    account_id VARCHAR NOT NULL,
                    device_workspace_id VARCHAR NOT NULL,
                    status VARCHAR NOT NULL,
                    source VARCHAR NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at DATETIME NOT NULL
                )
                """
            )
        )

    initialize_domain_schema(engine)

    with engine.begin() as connection:
        rows = connection.execute(text("PRAGMA table_info(execution_bindings)")).mappings().all()
    columns = {
        str(row["name"]): {
            "notnull": int(row["notnull"]),
            "default": row["dflt_value"],
        }
        for row in rows
    }

    assert "updated_at" in columns
    assert columns["source"]["notnull"] == 0
    assert columns["metadata_json"]["notnull"] == 0
    assert columns["created_at"]["default"] is not None
    assert columns["updated_at"]["default"] is not None
