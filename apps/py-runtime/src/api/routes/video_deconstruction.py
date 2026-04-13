from __future__ import annotations

from fastapi import APIRouter, Request

from schemas.envelope import ok_response
from schemas.video_deconstruction import ImportVideoInput, ImportedVideoDto
from services.video_import_service import VideoImportService

router = APIRouter(prefix="/api/video-deconstruction", tags=["video-deconstruction"])


def get_video_import_service(request: Request) -> VideoImportService:
    service = request.app.state.video_import_service
    assert isinstance(service, VideoImportService)
    return service


@router.post("/projects/{project_id}/import")
def import_video(
    project_id: str,
    payload: ImportVideoInput,
    request: Request,
) -> dict[str, object]:
    video = ImportedVideoDto.model_validate(
        get_video_import_service(request).import_video(
            project_id=project_id,
            file_path=payload.filePath,
        )
    )
    return ok_response(video.model_dump(mode="json"))


@router.get("/projects/{project_id}/videos")
def list_videos(project_id: str, request: Request) -> dict[str, object]:
    videos = [
        ImportedVideoDto.model_validate(video).model_dump(mode="json")
        for video in get_video_import_service(request).list_videos(project_id=project_id)
    ]
    return ok_response(videos)


@router.delete("/videos/{video_id}")
def delete_video(video_id: str, request: Request) -> dict[str, object]:
    get_video_import_service(request).delete_video(video_id=video_id)
    return ok_response(None)
