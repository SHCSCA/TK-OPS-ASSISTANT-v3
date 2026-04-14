from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from domain.models import Base, Project
from persistence.engine import create_runtime_engine, create_session_factory
from repositories.imported_video_repository import ImportedVideoRepository
from services.ffprobe import FfprobeResult
from services.video_import_service import VideoImportService


def _make_service(tmp_path: Path) -> VideoImportService:
    engine = create_runtime_engine(tmp_path / "runtime.db")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)

    with session_factory() as session:
        session.add(
            Project(
                id="project-1",
                name="测试项目",
                description="",
                status="active",
                current_script_version=0,
                current_storyboard_version=0,
                created_at="2026-04-13T00:00:00Z",
                updated_at="2026-04-13T00:00:00Z",
                last_accessed_at="2026-04-13T00:00:00Z",
            )
        )
        session.commit()

    return VideoImportService(
        repository=ImportedVideoRepository(session_factory=session_factory)
    )


def test_import_video_with_ffprobe_available(tmp_path: Path) -> None:
    service = _make_service(tmp_path)
    fake_video = tmp_path / "clip.mp4"
    fake_video.write_bytes(b"\x00" * 1024)

    with patch(
        "services.video_import_service.probe_video",
        return_value=FfprobeResult(
            duration_seconds=60.0,
            width=1920,
            height=1080,
            frame_rate=30.0,
            codec="h264",
            file_size_bytes=1024,
        ),
    ):
        video = service.import_video(project_id="project-1", file_path=str(fake_video))

    assert video["status"] == "ready"
    assert video["fileName"] == "clip.mp4"
    assert video["width"] == 1920
    assert video["durationSeconds"] == 60.0


def test_import_video_without_ffprobe_falls_back_to_file_stat(tmp_path: Path) -> None:
    service = _make_service(tmp_path)
    fake_video = tmp_path / "fallback.mp4"
    fake_video.write_bytes(b"\x00" * 2048)

    with patch("services.video_import_service.probe_video", return_value=None):
        video = service.import_video(project_id="project-1", file_path=str(fake_video))

    assert video["status"] == "imported"
    assert video["fileSizeBytes"] == 2048
    assert video["width"] is None
    assert video["errorMessage"]


def test_import_nonexistent_file_raises_http_error(tmp_path: Path) -> None:
    service = _make_service(tmp_path)

    with pytest.raises(HTTPException):
        service.import_video(project_id="project-1", file_path=str(tmp_path / "missing.mp4"))


def test_list_videos_for_project(tmp_path: Path) -> None:
    service = _make_service(tmp_path)
    fake_video = tmp_path / "listed.mp4"
    fake_video.write_bytes(b"\x00" * 512)

    with patch("services.video_import_service.probe_video", return_value=None):
        service.import_video(project_id="project-1", file_path=str(fake_video))

    videos = service.list_videos(project_id="project-1")

    assert len(videos) == 1
    assert videos[0]["fileName"] == "listed.mp4"
