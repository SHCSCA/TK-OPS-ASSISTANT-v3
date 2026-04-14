from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config


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
        "accounts",
        "device_workspaces",
        "execution_bindings",
        "automation_tasks",
        "publish_plans",
        "render_tasks",
    }.issubset(tables)
