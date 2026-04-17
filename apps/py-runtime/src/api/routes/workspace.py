from __future__ import annotations

from fastapi import APIRouter, Request, status

from schemas.envelope import ok_response
from schemas.workspace import (
    ClipMoveInput,
    ClipReplaceInput,
    ClipTrimInput,
    TimelineCreateInput,
    TimelineUpdateInput,
    WorkspaceAICommandInput,
)
from services.workspace_service import WorkspaceService

router = APIRouter(prefix="/api/workspace", tags=["workspace"])


def _svc(request: Request) -> WorkspaceService:
    return request.app.state.workspace_service  # type: ignore[no-any-return]


@router.get("/projects/{project_id}/timeline")
def get_project_timeline(project_id: str, request: Request) -> dict[str, object]:
    result = _svc(request).get_project_timeline(project_id)
    return ok_response(result.model_dump(mode="json"))


@router.post("/projects/{project_id}/timeline", status_code=status.HTTP_201_CREATED)
def create_project_timeline(
    project_id: str,
    payload: TimelineCreateInput,
    request: Request,
) -> dict[str, object]:
    result = _svc(request).create_project_timeline(project_id, payload)
    return ok_response(result.model_dump(mode="json"))


@router.patch("/timelines/{timeline_id}")
def update_timeline(
    timeline_id: str,
    payload: TimelineUpdateInput,
    request: Request,
) -> dict[str, object]:
    result = _svc(request).update_timeline(timeline_id, payload)
    return ok_response(result.model_dump(mode="json"))


@router.get("/clips/{clip_id}")
def get_clip(clip_id: str, request: Request) -> dict[str, object]:
    result = _svc(request).fetch_clip(clip_id)
    return ok_response(result.model_dump(mode="json"))


@router.post("/clips/{clip_id}/move")
def move_clip(
    clip_id: str,
    payload: ClipMoveInput,
    request: Request,
) -> dict[str, object]:
    result = _svc(request).move_clip(clip_id, payload)
    return ok_response(result.model_dump(mode="json"))


@router.post("/clips/{clip_id}/trim")
def trim_clip(
    clip_id: str,
    payload: ClipTrimInput,
    request: Request,
) -> dict[str, object]:
    result = _svc(request).trim_clip(clip_id, payload)
    return ok_response(result.model_dump(mode="json"))


@router.post("/clips/{clip_id}/replace")
def replace_clip(
    clip_id: str,
    payload: ClipReplaceInput,
    request: Request,
) -> dict[str, object]:
    result = _svc(request).replace_clip(clip_id, payload)
    return ok_response(result.model_dump(mode="json"))


@router.get("/timelines/{timeline_id}/preview")
def get_timeline_preview(timeline_id: str, request: Request) -> dict[str, object]:
    result = _svc(request).fetch_timeline_preview(timeline_id)
    return ok_response(result.model_dump(mode="json"))


@router.post("/timelines/{timeline_id}/precheck")
def precheck_timeline(timeline_id: str, request: Request) -> dict[str, object]:
    result = _svc(request).precheck_timeline(timeline_id)
    return ok_response(result.model_dump(mode="json"))


@router.post("/projects/{project_id}/ai-commands")
async def run_ai_command(
    project_id: str,
    payload: WorkspaceAICommandInput,
    request: Request,
) -> dict[str, object]:
    result = _svc(request).run_ai_command(project_id, payload)
    return ok_response(result.model_dump(mode="json"))
