from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable

from fastapi import HTTPException

from domain.models import ImportedVideo
from domain.models.base import generate_uuid
from repositories.imported_video_repository import ImportedVideoRepository
from tasks.video_tasks import process_video_import_task


class VideoImportService:
    def __init__(self, *, repository: ImportedVideoRepository) -> None:
        self._repository = repository

    def import_video(self, *, project_id: str, file_path: str) -> dict[str, object]:
        """
        同步入口：快速保存记录并启动后台异步任务。
        """
        path = Path(file_path)
        if not path.is_file():
            raise HTTPException(status_code=400, detail="视频文件不存在。")

        file_size = path.stat().st_size
        video_id = generate_uuid()
        
        # 初始状态设为 'imported' (表示已导入但元信息未解析)
        video = ImportedVideo(
            id=video_id,
            project_id=project_id,
            file_path=str(path),
            file_name=path.name,
            file_size_bytes=file_size,
            duration_seconds=None,
            width=None,
            height=None,
            frame_rate=None,
            codec=None,
            status="imported",
            error_message=None,
            created_at=_utc_now(),
        )

        saved_video = self._repository.create(video)
        
        # --- 异步任务派发 ---
        # 使用 asyncio.create_task 在后台运行解析任务
        # 注意：在 FastAPI 环境下，这将在当前进程的事件循环中异步执行
        asyncio.create_task(
            process_video_import_task(
                video_id=video_id,
                file_path=str(path),
                repository=self._repository,
            )
        )

        return _to_dict(saved_video)

    def list_videos(self, *, project_id: str) -> list[dict[str, object]]:
        return [_to_dict(video) for video in self._repository.list_by_project(project_id)]

    def delete_video(self, *, video_id: str) -> None:
        if not self._repository.delete(video_id):
            raise HTTPException(status_code=404, detail="视频记录不存在。")


def _to_dict(video: ImportedVideo) -> dict[str, object]:
    return {
        "id": video.id,
        "projectId": video.project_id,
        "filePath": video.file_path,
        "fileName": video.file_name,
        "fileSizeBytes": video.file_size_bytes,
        "durationSeconds": video.duration_seconds,
        "width": video.width,
        "height": video.height,
        "frameRate": video.frame_rate,
        "codec": video.codec,
        "status": video.status,
        "errorMessage": video.error_message,
        "createdAt": video.created_at,
    }


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
