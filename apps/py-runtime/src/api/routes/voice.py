from __future__ import annotations

from fastapi import APIRouter, Request, status

from schemas.envelope import ok_response
from schemas.voice import (
    VoiceProfileCreateInput,
    VoiceSegmentRegenerateInput,
    VoiceTrackGenerateInput,
)
from services.voice_service import VoiceService

router = APIRouter(prefix="/api/voice", tags=["voice"])


def _svc(request: Request) -> VoiceService:
    return request.app.state.voice_service  # type: ignore[no-any-return]


@router.get("/profiles")
def list_profiles(request: Request) -> dict[str, object]:
    profiles = _svc(request).list_profiles()
    return ok_response([profile.model_dump(mode="json") for profile in profiles])


@router.post("/profiles", status_code=status.HTTP_201_CREATED)
def create_profile(
    payload: VoiceProfileCreateInput,
    request: Request,
) -> dict[str, object]:
    profile = _svc(request).create_profile(payload)
    return ok_response(profile.model_dump(mode="json"))


@router.post("/providers/{provider_id}/profiles/refresh")
def refresh_provider_profiles(provider_id: str, request: Request) -> dict[str, object]:
    result = _svc(request).refresh_provider_profiles(provider_id)
    return ok_response(result.model_dump(mode="json"))


@router.get("/projects/{project_id}/tracks")
def list_project_tracks(project_id: str, request: Request) -> dict[str, object]:
    tracks = _svc(request).list_tracks(project_id)
    return ok_response([track.model_dump(mode="json") for track in tracks])


@router.post("/projects/{project_id}/tracks/generate")
async def generate_track(
    project_id: str,
    payload: VoiceTrackGenerateInput,
    request: Request,
) -> dict[str, object]:
    result = _svc(request).generate_track(project_id, payload)
    return ok_response(result.model_dump(mode="json"))


@router.post("/tracks/{track_id}/segments/{segment_id}/regenerate")
async def regenerate_segment(
    track_id: str,
    segment_id: str,
    payload: VoiceSegmentRegenerateInput,
    request: Request,
) -> dict[str, object]:
    result = await _svc(request).regenerate_segment(track_id, segment_id, payload)
    return ok_response(result.model_dump(mode="json"))


@router.get("/tracks/{track_id}/waveform")
def fetch_waveform(track_id: str, request: Request) -> dict[str, object]:
    waveform = _svc(request).fetch_waveform(track_id)
    return ok_response(waveform.model_dump(mode="json"))


@router.get("/tracks/{track_id}")
def get_track(track_id: str, request: Request) -> dict[str, object]:
    track = _svc(request).get_track(track_id)
    return ok_response(track.model_dump(mode="json"))


@router.delete("/tracks/{track_id}")
def delete_track(track_id: str, request: Request) -> dict[str, object]:
    _svc(request).delete_track(track_id)
    return ok_response(None)
