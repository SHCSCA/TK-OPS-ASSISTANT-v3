from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config

from persistence.engine import create_runtime_engine, initialize_domain_schema


def test_alembic_upgrade_creates_core_operational_tables(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = tmp_path / "runtime.db"
    repo_root = Path(__file__).resolve().parents[2]
    runtime_root = repo_root / "apps" / "py-runtime"
    config = Config(str(runtime_root / "alembic.ini"))
    config.set_main_option("script_location", str(runtime_root / "alembic"))
    monkeypatch.setenv("TK_OPS_DATABASE_PATH", str(database_path))

    cwd = Path.cwd()
    os.chdir(runtime_root)
    try:
        command.upgrade(config, "head")
    finally:
        os.chdir(cwd)

    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "select name from sqlite_master where type='table'"
            ).fetchall()
        }

    assert {
        "timelines",
        "voice_tracks",
        "subtitle_tracks",
        "assets",
        "ai_provider_models",
        "ai_provider_health",
        "accounts",
        "browser_instances",
        "device_workspaces",
        "execution_bindings",
        "automation_tasks",
        "publish_plans",
        "render_tasks",
        "prompt_templates",
        "video_stage_runs",
    }.issubset(tables)


def test_initialize_domain_schema_repairs_legacy_projects_table_deleted_at_column(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "runtime.db"
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL,
                current_script_version INTEGER NOT NULL,
                current_storyboard_version INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_accessed_at TEXT NOT NULL
            )
            """
        )
        connection.commit()

    engine = create_runtime_engine(database_path)
    initialize_domain_schema(engine)

    with sqlite3.connect(database_path) as connection:
        columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(projects)").fetchall()
        }

    assert "deleted_at" in columns
