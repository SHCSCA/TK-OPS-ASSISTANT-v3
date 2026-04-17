from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from fastapi import HTTPException

from domain.models import ImportedVideo
from domain.models.base import generate_uuid
from repositories.imported_video_repository import ImportedVideoRepository
from repositories.video_deconstruction_repository import VideoDeconstructionRepository
from services.task_manager import TaskManager, task_manager as default_task_manager


class VideoImportService:
    def __init__(
        self,
        *,
        repository: ImportedVideoRepository,
        stage_repository: VideoDeconstructionRepository | None = None,
        task_manager: TaskManager | None = None,
    ) -> None:
        self._repository = repository
        self._stage_repository = stage_repository
        self._task_manager = task_manager or default_task_manager

    def import_video(self, *, project_id: str, file_path: str) -> dict[str, object]:
        path = Path(file_path)
        if not path.is_file():
            raise HTTPException(status_code=400, detail='视频文件不存在。')

        video_id = generate_uuid()
        saved_video = self._repository.create(
            ImportedVideo(
                id=video_id,
                project_id=project_id,
                file_path=str(path),
                file_name=path.name,
                file_size_bytes=path.stat().st_size,
                duration_seconds=None,
                width=None,
                height=None,
                frame_rate=None,
                codec=None,
                status='imported',
                error_message=None,
                created_at=_utc_now(),
            )
        )

        def create_import_task(progress_callback):
            from tasks.video_tasks import process_video_import_task

            return process_video_import_task(
                video_id=video_id,
                file_path=str(path),
                repository=self._repository,
                stage_repository=self._stage_repository,
                progress_callback=progress_callback,
            )

        try:
            self._task_manager.submit(
                task_type='video_import',
                coro_factory=create_import_task,
                project_id=project_id,
                task_id=video_id,
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

        return _to_dict(saved_video)

    def list_videos(self, *, project_id: str) -> list[dict[str, object]]:
        return [_to_dict(video) for video in self._repository.list_by_project(project_id)]

    def delete_video(self, *, video_id: str) -> None:
        if not self._repository.delete(video_id):
            raise HTTPException(status_code=404, detail='视频记录不存在。')


def _to_dict(video: ImportedVideo) -> dict[str, object]:
    return {
        'id': video.id,
        'projectId': video.project_id,
        'filePath': video.file_path,
        'fileName': video.file_name,
        'fileSizeBytes': video.file_size_bytes,
        'durationSeconds': video.duration_seconds,
        'width': video.width,
        'height': video.height,
        'frameRate': video.frame_rate,
        'codec': video.codec,
        'status': video.status,
        'errorMessage': video.error_message,
        'createdAt': video.created_at,
    }


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace('+00:00', 'Z')