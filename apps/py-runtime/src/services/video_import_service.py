from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from fastapi import HTTPException

from domain.models import ImportedVideo
from domain.models.base import generate_uuid
from repositories.imported_video_repository import ImportedVideoRepository
from services.ffprobe import probe_video


class VideoImportService:
    def __init__(self, *, repository: ImportedVideoRepository) -> None:
        self._repository = repository

    def import_video(self, *, project_id: str, file_path: str) -> dict[str, object]:
        path = Path(file_path)
        if not path.is_file():
            raise HTTPException(status_code=400, detail="视频文件不存在。")

        file_size = path.stat().st_size
        probe_result = probe_video(path)
        video = ImportedVideo(
            id=generate_uuid(),
            project_id=project_id,
            file_path=str(path),
            file_name=path.name,
            file_size_bytes=probe_result.file_size_bytes if probe_result else file_size,
            duration_seconds=probe_result.duration_seconds if probe_result else None,
            width=probe_result.width if probe_result else None,
            height=probe_result.height if probe_result else None,
            frame_rate=probe_result.frame_rate if probe_result else None,
            codec=probe_result.codec if probe_result else None,
            status="ready" if probe_result else "imported",
            error_message=None if probe_result else "FFprobe 不可用，已仅记录文件路径和大小。",
            created_at=_utc_now(),
        )

        return _to_dict(self._repository.create(video))

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
