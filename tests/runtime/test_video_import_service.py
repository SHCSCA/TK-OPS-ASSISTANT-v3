from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from domain.models import Base, Project
from persistence.engine import create_runtime_engine, create_session_factory
from repositories.imported_video_repository import ImportedVideoRepository
from services.video_import_service import VideoImportService

# 配置 pytest-asyncio
pytestmark = pytest.mark.asyncio


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


async def test_import_video_starts_async_task(tmp_path: Path) -> None:
    """
    验证导入视频会立即返回 'imported' 状态，并启动后台异步任务。
    """
    service = _make_service(tmp_path)
    fake_video = tmp_path / "clip.mp4"
    fake_video.write_bytes(b"\x00" * 1024)

    # Mock 异步任务处理器，确保它被调用
    with patch("services.video_import_service.process_video_import_task", new_callable=AsyncMock) as mock_task:
        # 在异步测试中运行同步方法
        video = service.import_video(project_id="project-1", file_path=str(fake_video))

        assert video["status"] == "imported"
        assert video["fileName"] == "clip.mp4"
        assert video["fileSizeBytes"] == 1024
        
        # 验证异步任务是否被派发
        # 我们给一点点时间让 create_task 运行到我们的 mock 上
        await asyncio.sleep(0.1)
        mock_task.assert_called_once()
        args, kwargs = mock_task.call_args
        assert kwargs["file_path"] == str(fake_video)
        assert kwargs["video_id"] == video["id"]


async def test_import_nonexistent_file_raises_http_error(tmp_path: Path) -> None:
    service = _make_service(tmp_path)

    with pytest.raises(HTTPException):
        service.import_video(project_id="project-1", file_path=str(tmp_path / "missing.mp4"))


async def test_list_videos_for_project(tmp_path: Path) -> None:
    service = _make_service(tmp_path)
    fake_video = tmp_path / "listed.mp4"
    fake_video.write_bytes(b"\x00" * 512)

    with patch("services.video_import_service.process_video_import_task", new_callable=AsyncMock):
        service.import_video(project_id="project-1", file_path=str(fake_video))

    videos = service.list_videos(project_id="project-1")

    assert len(videos) == 1
    assert videos[0]["fileName"] == "listed.mp4"
    assert videos[0]["status"] == "imported"
