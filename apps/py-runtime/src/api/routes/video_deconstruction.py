from __future__ import annotations

from fastapi import APIRouter, Request

from schemas.envelope import ok_response
from schemas.video_deconstruction import (
    ApplyVideoExtractionResultDto,
    ImportVideoInput,
    ImportedVideoDto,
    VideoSegmentDto,
    VideoStageDto,
    VideoStructureExtractionDto,
    VideoTranscriptDto,
)
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
    assert isinstance(transcript, VideoTranscriptDto)
    return ok_response(transcript.model_dump(mode="json"))


@router.get("/videos/{video_id}/transcript")
def get_transcript(video_id: str, request: Request) -> dict[str, object]:
    transcript = get_video_deconstruction_service(request).get_transcript(video_id)
    assert isinstance(transcript, VideoTranscriptDto)
    return ok_response(transcript.model_dump(mode="json"))


@router.post("/videos/{video_id}/segment")
def run_segmentation(video_id: str, request: Request) -> dict[str, object]:
    segments = get_video_deconstruction_service(request).run_segmentation(video_id)
    return ok_response([VideoSegmentDto.model_validate(item).model_dump(mode="json") for item in segments])


@router.get("/videos/{video_id}/segments")
def get_segments(video_id: str, request: Request) -> dict[str, object]:
    segments = get_video_deconstruction_service(request).get_segments(video_id)
    return ok_response([VideoSegmentDto.model_validate(item).model_dump(mode="json") for item in segments])


@router.post("/videos/{video_id}/extract-structure")
def extract_structure(video_id: str, request: Request) -> dict[str, object]:
    extraction = get_video_deconstruction_service(request).extract_structure(video_id)
    assert isinstance(extraction, VideoStructureExtractionDto)
    return ok_response(extraction.model_dump(mode="json"))


@router.get("/videos/{video_id}/structure")
def get_structure(video_id: str, request: Request) -> dict[str, object]:
    extraction = get_video_deconstruction_service(request).get_structure(video_id)
    assert isinstance(extraction, VideoStructureExtractionDto)
    return ok_response(extraction.model_dump(mode="json"))


@router.post("/extractions/{extraction_id}/apply-to-project")
def apply_extraction_to_project(extraction_id: str, request: Request) -> dict[str, object]:
    result = get_video_deconstruction_service(request).apply_extraction_to_project(
        extraction_id,
        dashboard_service=request.app.state.dashboard_service,
        script_repository=request.app.state.script_repository,
        storyboard_repository=request.app.state.storyboard_repository,
    )
    assert isinstance(result, ApplyVideoExtractionResultDto)
    return ok_response(result.model_dump(mode="json"))


@router.get("/videos/{video_id}/stages")
def list_video_stages(video_id: str, request: Request) -> dict[str, object]:
    stages = get_video_deconstruction_service(request).get_stages(video_id)
    return ok_response([stage.model_dump(mode="json") for stage in stages])


@router.post("/videos/{video_id}/stages/{stage_id}/rerun")
async def rerun_video_stage(video_id: str, stage_id: str, request: Request) -> dict[str, object]:
    task = get_video_deconstruction_service(request).rerun_stage(
        video_id,
        stage_id,
        request_id=getattr(request.state, "request_id", None),
    )
    return ok_response(_task_to_payload(task))


def _task_to_payload(task) -> dict[str, object]:
    return {
        "id": task.id,
        "taskType": task.task_type,
        "projectId": task.project_id,
        "status": task.status,
        "progress": task.progress,
        "message": task.message,
        "createdAt": task.created_at,
        "updatedAt": task.updated_at,
    }
