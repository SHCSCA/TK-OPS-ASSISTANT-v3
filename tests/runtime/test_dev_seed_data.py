from __future__ import annotations

import sqlite3
import json
from pathlib import Path

from devtools.seed_data import (
    DEV_SEED_SOURCE,
    SeedOptions,
    scan_local_assets,
    seed_dev_data,
)


def test_scan_local_assets_filters_limits_and_keeps_source_paths(tmp_path: Path) -> None:
    videos = tmp_path / "Videos"
    pictures = tmp_path / "Pictures"
    documents = tmp_path / "Documents"
    for directory in (videos, pictures, documents):
        directory.mkdir()

    first_video = videos / "clip-a.mp4"
    second_video = documents / "clip-b.mov"
    image = pictures / "cover.png"
    doc = documents / "brief.md"
    ignored = documents / "archive.zip"
    first_video.write_bytes(b"video-a")
    second_video.write_bytes(b"video-b")
    image.write_bytes(b"image")
    doc.write_text("script", encoding="utf-8")
    ignored.write_bytes(b"ignored")

    assets = scan_local_assets(
        roots=(videos, pictures, documents),
        video_limit=1,
        image_limit=1,
        document_limit=1,
    )

    assert [asset.kind for asset in assets] == ["video", "image", "document"]
    assert {asset.path for asset in assets}.issubset({first_video, second_video, image, doc})
    assert ignored not in {asset.path for asset in assets}
    assert all(asset.path.exists() for asset in assets)


def test_seed_dev_data_is_repeatable_and_preserves_non_seed_rows(tmp_path: Path) -> None:
    videos = tmp_path / "Videos"
    pictures = tmp_path / "Pictures"
    documents = tmp_path / "Documents"
    for directory in (videos, pictures, documents):
        directory.mkdir()
    (videos / "demo.mp4").write_bytes(b"video")
    (pictures / "cover.jpg").write_bytes(b"image")
    (documents / "brief.txt").write_text("doc", encoding="utf-8")

    database_path = tmp_path / "runtime.db"
    first = seed_dev_data(
        SeedOptions(
            database_path=database_path,
            asset_roots=(videos, pictures, documents),
            reset_dev_seed=True,
            video_limit=12,
            image_limit=24,
            document_limit=12,
        )
    )
    second = seed_dev_data(
        SeedOptions(
            database_path=database_path,
            asset_roots=(videos, pictures, documents),
            reset_dev_seed=True,
            video_limit=12,
            image_limit=24,
            document_limit=12,
        )
    )

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "insert into projects (id, name, description, status, current_script_version, "
            "current_storyboard_version, created_at, updated_at, last_accessed_at) "
            "values (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "manual-project",
                "手工项目",
                "",
                "active",
                0,
                0,
                "2026-04-14T00:00:00Z",
                "2026-04-14T00:00:00Z",
                "2026-04-14T00:00:00Z",
            ),
        )
        connection.commit()

    third = seed_dev_data(
        SeedOptions(
            database_path=database_path,
            asset_roots=(videos, pictures, documents),
            reset_dev_seed=True,
            video_limit=12,
            image_limit=24,
            document_limit=12,
        )
    )

    with sqlite3.connect(database_path) as connection:
        project_count = connection.execute(
            "select count(*) from projects where id like 'dev-seed-%'"
        ).fetchone()[0]
        manual_project = connection.execute(
            "select name from projects where id = 'manual-project'"
        ).fetchone()
        sources = {
            row[0]
            for row in connection.execute(
                "select distinct source from assets where id like 'dev-seed-%'"
            ).fetchall()
        }
        required_counts = {
            table: connection.execute(f"select count(*) from {table}").fetchone()[0]
            for table in (
                "script_versions",
                "storyboard_versions",
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
                "ai_job_records",
            )
        }

    assert first.seeded_assets == 3
    assert second.seeded_assets == 3
    assert third.seeded_assets == 3
    assert project_count == 2
    assert manual_project == ("手工项目",)
    assert sources == {DEV_SEED_SOURCE}
    assert all(count >= 1 for count in required_counts.values())


def test_root_package_exposes_runtime_seed_command() -> None:
    package_json = Path(__file__).resolve().parents[2] / "package.json"
    document = json.loads(package_json.read_text(encoding="utf-8"))

    assert (
        document["scripts"]["runtime:seed-dev"]
        == "node scripts/seed-runtime-dev.mjs --reset-dev-seed"
    )
