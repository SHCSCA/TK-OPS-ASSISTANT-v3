from __future__ import annotations

from fastapi import APIRouter, Request

from schemas.envelope import ok_response
from schemas.video_deconstruction import ImportVideoInput, ImportedVideoDto
from services.video_deconstruction_service import VideoDeconstructionService
from services.video_import_service import VideoImportService

router = APIRouter(prefix="/api/video-deconstruction", tags=["video-deconstruction"])


def get_video_import_service(request: Request) -> VideoImportService:
    service = request.app.state.video_import_service
    assert isinstance(service, VideoImportService)
    return service


def get_video_deconstruction_service(request: Request) -> VideoDeconstructionService:
    service = request.app.state.video_deconstruction_service
    assert isinstance(service, VideoDeconstructionService)
    return service


@router.post("/projects/{project_id}/import")
async def import_video(
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


@router.post("/videos/{video_id}/transcribe")
def start_transcription(video_id: str, request: Request) -> dict[str, object]:
    transcript = get_video_deconstruction_service(request).start_transcription(video_id)
    return ok_response(transcript.model_dump(mode="json"))


@router.get("/videos/{video_id}/transcript")
def get_transcript(video_id: str, request: Request) -> dict[str, object]:
    transcript = get_video_deconstruction_service(request).get_transcript(video_id)
    return ok_response(transcript.model_dump(mode="json"))


@router.post("/videos/{video_id}/segment")
def run_segmentation(video_id: str, request: Request) -> dict[str, object]:
    segments = get_video_deconstruction_service(request).run_segmentation(video_id)
    return ok_response([item.model_dump(mode="json") for item in segments])


@router.get("/videos/{video_id}/segments")
def list_segments(video_id: str, request: Request) -> dict[str, object]:
    segments = get_video_deconstruction_service(request).list_segments(video_id)
    return ok_response([item.model_dump(mode="json") for item in segments])


@router.post("/videos/{video_id}/extract-structure")
def extract_structure(video_id: str, request: Request) -> dict[str, object]:
    extraction = get_video_deconstruction_service(request).extract_structure(video_id)
    return ok_response(extraction.model_dump(mode="json"))


@router.get("/videos/{video_id}/structure")
def get_structure(video_id: str, request: Request) -> dict[str, object]:
    extraction = get_video_deconstruction_service(request).get_structure(video_id)
    return ok_response(extraction.model_dump(mode="json"))


@router.post("/extractions/{extraction_id}/apply-to-project")
def apply_to_project(extraction_id: str, request: Request) -> dict[str, object]:
    result = get_video_deconstruction_service(request).apply_to_project(extraction_id)
    return ok_response(result.model_dump(mode="json"))
