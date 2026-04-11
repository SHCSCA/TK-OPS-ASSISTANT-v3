from __future__ import annotations

from fastapi import APIRouter, Request

from schemas.envelope import ok_response
from schemas.scripts import ScriptGenerateInput, ScriptRewriteInput, ScriptSaveInput
from services.script_service import ScriptService

router = APIRouter(prefix='/api/scripts', tags=['scripts'])


def get_script_service(request: Request) -> ScriptService:
    service = request.app.state.script_service
    assert isinstance(service, ScriptService)
    return service


@router.get('/projects/{project_id}/document')
def get_script_document(project_id: str, request: Request) -> dict[str, object]:
    document = get_script_service(request).get_document(project_id)
    return ok_response(document.model_dump(mode='json'))


@router.put('/projects/{project_id}/document')
def save_script_document(
    project_id: str,
    payload: ScriptSaveInput,
    request: Request,
) -> dict[str, object]:
    document = get_script_service(request).save_document(project_id, payload.content)
    return ok_response(document.model_dump(mode='json'))


@router.post('/projects/{project_id}/generate')
def generate_script(
    project_id: str,
    payload: ScriptGenerateInput,
    request: Request,
) -> dict[str, object]:
    document = get_script_service(request).generate_with_service(
        project_id,
        payload.topic,
        ai_text_generation_service=request.app.state.ai_text_generation_service,
        request_id=getattr(request.state, 'request_id', None),
    )
    return ok_response(document.model_dump(mode='json'))


@router.post('/projects/{project_id}/rewrite')
def rewrite_script(
    project_id: str,
    payload: ScriptRewriteInput,
    request: Request,
) -> dict[str, object]:
    document = get_script_service(request).rewrite_with_service(
        project_id,
        payload.instructions,
        ai_text_generation_service=request.app.state.ai_text_generation_service,
        request_id=getattr(request.state, 'request_id', None),
    )
    return ok_response(document.model_dump(mode='json'))
