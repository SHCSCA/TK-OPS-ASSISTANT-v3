from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from domain.models import Base, ImportedVideo, Project
from persistence.engine import create_runtime_engine, create_session_factory
from repositories.imported_video_repository import ImportedVideoRepository
from runtime_tasks.video_tasks import process_video_import_task
from services.video_import_service import VideoImportService


class RecordingTaskManager:
    def __init__(self) -> None:
        self.submissions: list[dict[str, object]] = []

    def submit(self, **kwargs):
        self.submissions.append(kwargs)


def _make_repository(tmp_path: Path) -> ImportedVideoRepository:
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

    return ImportedVideoRepository(session_factory=session_factory)


def _make_service(
    tmp_path: Path,
    *,
    task_manager: RecordingTaskManager | None = None,
) -> VideoImportService:
    return VideoImportService(
        repository=_make_repository(tmp_path),
        task_manager=task_manager,
    )


def test_import_video_starts_async_task(tmp_path: Path) -> None:
    task_manager = RecordingTaskManager()
    service = _make_service(tmp_path, task_manager=task_manager)
    fake_video = tmp_path / "clip.mp4"
    fake_video.write_bytes(b"\x00" * 1024)

    video = service.import_video(project_id="project-1", file_path=str(fake_video))

    assert video["status"] == "imported"
    assert video["fileName"] == "clip.mp4"
    assert video["fileSizeBytes"] == 1024
    assert set(video) == {
        "id",
        "projectId",
        "filePath",
        "fileName",
        "fileSizeBytes",
        "durationSeconds",
        "width",
        "height",
        "frameRate",
        "codec",
        "status",
        "errorMessage",
        "createdAt",
    }

    assert len(task_manager.submissions) == 1
    submission = task_manager.submissions[0]
    assert submission["task_type"] == "video_import"
    assert submission["project_id"] == "project-1"
    assert submission["task_id"] == video["id"]


def test_import_nonexistent_file_raises_http_error(tmp_path: Path) -> None:
    service = _make_service(tmp_path)

    with pytest.raises(HTTPException):
        service.import_video(project_id="project-1", file_path=str(tmp_path / "missing.mp4"))


def test_list_videos_for_project(tmp_path: Path) -> None:
    task_manager = RecordingTaskManager()
    service = _make_service(tmp_path, task_manager=task_manager)
    fake_video = tmp_path / "listed.mp4"
    fake_video.write_bytes(b"\x00" * 512)

    service.import_video(project_id="project-1", file_path=str(fake_video))

    videos = service.list_videos(project_id="project-1")

    assert len(videos) == 1
    assert videos[0]["fileName"] == "listed.mp4"
    assert videos[0]["status"] == "imported"


def test_process_video_import_task_reports_progress_when_ffprobe_unavailable(
    tmp_path: Path,
) -> None:
    repository = _make_repository(tmp_path)
    fake_video = tmp_path / "progress.mp4"
    fake_video.write_bytes(b"\x00" * 1024)
    video = ImportedVideo(
        id="video-progress",
        project_id="project-1",
        file_path=str(fake_video),
        file_name="progress.mp4",
        file_size_bytes=1024,
        duration_seconds=None,
        width=None,
        height=None,
        frame_rate=None,
        codec=None,
        status="imported",
        error_message=None,
        created_at="2026-04-13T00:00:00Z",
    )
    repository.create(video)
    progress_events: list[tuple[int, str]] = []

    async def progress_callback(progress: int, message: str) -> None:
        progress_events.append((progress, message))

    with patch("runtime_tasks.video_tasks.probe_video", return_value=None):
        asyncio.run(
            process_video_import_task(
                video_id="video-progress",
                file_path=str(fake_video),
                repository=repository,
                progress_callback=progress_callback,
            )
        )

    updated = repository.get("video-progress")
    assert updated is not None
    assert updated.status == "imported"
    assert updated.error_message == "FFprobe 不可用，已仅记录文件路径和大小。"
    assert progress_events == [
        (10, "正在读取视频文件"),
        (40, "正在解析视频元信息"),
        (80, "正在保存解析结果"),
    ]


def test_process_video_import_task_marks_error_and_reraises(
    tmp_path: Path,
) -> None:
    repository = _make_repository(tmp_path)
    fake_video = tmp_path / "broken.mp4"
    fake_video.write_bytes(b"\x00" * 1024)
    video = ImportedVideo(
        id="video-error",
        project_id="project-1",
        file_path=str(fake_video),
        file_name="broken.mp4",
        file_size_bytes=1024,
        duration_seconds=None,
        width=None,
        height=None,
        frame_rate=None,
        codec=None,
        status="imported",
        error_message=None,
        created_at="2026-04-13T00:00:00Z",
    )
    repository.create(video)

    with patch("runtime_tasks.video_tasks.probe_video", side_effect=RuntimeError("ffprobe failed")):
        with pytest.raises(RuntimeError, match="ffprobe failed"):
            asyncio.run(
                process_video_import_task(
                    video_id="video-error",
                    file_path=str(fake_video),
                    repository=repository,
                )
            )

    updated = repository.get("video-error")
    assert updated is not None
    assert updated.status == "error"
    assert updated.error_message == "解析失败: ffprobe failed"
