from __future__ import annotations

from fastapi import APIRouter, Request

from schemas.envelope import ok_response
from schemas.storyboards import (
    StoryboardSaveInput,
    StoryboardShotInput,
    StoryboardShotUpdateInput,
)
from services.storyboard_service import StoryboardService

router = APIRouter(prefix='/api/storyboards', tags=['storyboards'])


def get_storyboard_service(request: Request) -> StoryboardService:
    service = request.app.state.storyboard_service
    assert isinstance(service, StoryboardService)
    return service


@router.get('/projects/{project_id}/document')
def get_storyboard_document(project_id: str, request: Request) -> dict[str, object]:
    document = get_storyboard_service(request).get_document(project_id)
    return ok_response(document.model_dump(mode='json'))


@router.get('/templates')
def list_storyboard_templates(request: Request) -> dict[str, object]:
    templates = get_storyboard_service(request).list_templates()
    return ok_response([item.model_dump(mode='json') for item in templates])


@router.put('/projects/{project_id}/document')
def save_storyboard_document(
    project_id: str,
    payload: StoryboardSaveInput,
    request: Request,
) -> dict[str, object]:
    document = get_storyboard_service(request).save_document(
        project_id,
        based_on_script_revision=payload.basedOnScriptRevision,
        scenes=[item.model_dump(mode='json') for item in payload.scenes],
        markdown=payload.markdown,
    )
    return ok_response(document.model_dump(mode='json'))


@router.post('/projects/{project_id}/generate')
def generate_storyboard(project_id: str, request: Request) -> dict[str, object]:
    document = get_storyboard_service(request).generate_with_service(
        project_id,
        ai_text_generation_service=request.app.state.ai_text_generation_service,
        request_id=getattr(request.state, 'request_id', None),
    )
    return ok_response(document.model_dump(mode='json'))


@router.post('/projects/{project_id}/sync-from-script')
def sync_storyboard_from_script(project_id: str, request: Request) -> dict[str, object]:
    document = get_storyboard_service(request).sync_from_script(project_id)
    return ok_response(document.model_dump(mode='json'))


@router.post('/projects/{project_id}/shots')
def create_storyboard_shot(
    project_id: str,
    payload: StoryboardShotInput,
    request: Request,
) -> dict[str, object]:
    document = get_storyboard_service(request).create_shot(project_id, payload)
    return ok_response(document.model_dump(mode='json'))


@router.patch('/projects/{project_id}/shots/{shot_id}')
def update_storyboard_shot(
    project_id: str,
    shot_id: str,
    payload: StoryboardShotUpdateInput,
    request: Request,
) -> dict[str, object]:
    document = get_storyboard_service(request).update_shot(project_id, shot_id, payload)
    return ok_response(document.model_dump(mode='json'))


@router.delete('/projects/{project_id}/shots/{shot_id}')
def delete_storyboard_shot(
    project_id: str,
    shot_id: str,
    request: Request,
) -> dict[str, object]:
    document = get_storyboard_service(request).delete_shot(project_id, shot_id)
    return ok_response(document.model_dump(mode='json'))
