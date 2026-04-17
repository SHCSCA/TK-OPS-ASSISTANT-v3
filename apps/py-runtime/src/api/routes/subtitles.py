from __future__ import annotations

from fastapi import APIRouter, Request

from schemas.envelope import ok_response
from schemas.subtitles import (
    SubtitleExportInput,
    SubtitleTrackAlignInput,
    SubtitleTrackGenerateInput,
    SubtitleTrackUpdateInput,
)
from services.subtitle_service import SubtitleService

router = APIRouter(prefix="/api/subtitles", tags=["subtitles"])


def _svc(request: Request) -> SubtitleService:
    return request.app.state.subtitle_service  # type: ignore[no-any-return]


@router.get("/projects/{project_id}/tracks")
def list_project_tracks(project_id: str, request: Request) -> dict[str, object]:
    tracks = _svc(request).list_tracks(project_id)
    return ok_response([track.model_dump(mode="json") for track in tracks])


@router.post("/projects/{project_id}/tracks/generate")
def generate_track(
    project_id: str,
    payload: SubtitleTrackGenerateInput,
    request: Request,
) -> dict[str, object]:
    result = _svc(request).generate_track(project_id, payload)
    return ok_response(result.model_dump(mode="json"))


@router.get("/style-templates")
def list_style_templates(request: Request) -> dict[str, object]:
    templates = _svc(request).list_style_templates()
    return ok_response([template.model_dump(mode="json") for template in templates])


@router.post("/tracks/{track_id}/align")
def align_track(
    track_id: str,
    payload: SubtitleTrackAlignInput,
    request: Request,
) -> dict[str, object]:
    track = _svc(request).align_track(track_id, payload)
    return ok_response(track.model_dump(mode="json"))


@router.post("/tracks/{track_id}/export")
def export_track(
    track_id: str,
    payload: SubtitleExportInput,
    request: Request,
) -> dict[str, object]:
    export = _svc(request).export_track(track_id, payload)
    return ok_response(export.model_dump(mode="json"))


@router.get("/tracks/{track_id}")
def get_track(track_id: str, request: Request) -> dict[str, object]:
    track = _svc(request).get_track(track_id)
    return ok_response(track.model_dump(mode="json"))


@router.patch("/tracks/{track_id}")
def update_track(
    track_id: str,
    payload: SubtitleTrackUpdateInput,
    request: Request,
) -> dict[str, object]:
    track = _svc(request).update_track(track_id, payload)
    return ok_response(track.model_dump(mode="json"))


@router.delete("/tracks/{track_id}")
def delete_track(track_id: str, request: Request) -> dict[str, object]:
    _svc(request).delete_track(track_id)
    return ok_response(None)
