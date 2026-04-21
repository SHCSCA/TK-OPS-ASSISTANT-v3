from __future__ import annotations

from fastapi import APIRouter, Request

from schemas.envelope import ok_response
from schemas.scripts import (
    ScriptGenerateInput,
    ScriptRewriteInput,
    ScriptSaveInput,
    ScriptSegmentRewriteInput,
    ScriptTitleVariantsInput,
)
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


@router.get('/projects/{project_id}/versions')
def list_script_versions(project_id: str, request: Request) -> dict[str, object]:
    versions = get_script_service(request).list_versions(project_id)
    return ok_response([item.model_dump(mode='json') for item in versions])


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


@router.post('/projects/{project_id}/title-variants')
def generate_script_title_variants(
    project_id: str,
    payload: ScriptTitleVariantsInput,
    request: Request,
) -> dict[str, object]:
    variants = get_script_service(request).generate_title_variants(
        project_id,
        payload.topic,
        payload.count,
        ai_text_generation_service=request.app.state.ai_text_generation_service,
        request_id=getattr(request.state, 'request_id', None),
    )
    return ok_response([item.model_dump(mode='json') for item in variants])


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


@router.post('/projects/{project_id}/restore/{version_id}')
def restore_script_version(
    project_id: str,
    version_id: int,
    request: Request,
) -> dict[str, object]:
    document = get_script_service(request).restore_version(project_id, version_id)
    return ok_response(document.model_dump(mode='json'))


@router.post('/projects/{project_id}/segments/{segment_id}/rewrite')
def rewrite_script_segment(
    project_id: str,
    segment_id: str,
    payload: ScriptSegmentRewriteInput,
    request: Request,
) -> dict[str, object]:
    document = get_script_service(request).rewrite_segment(
        project_id,
        segment_id,
        payload,
        ai_text_generation_service=request.app.state.ai_text_generation_service,
        request_id=getattr(request.state, 'request_id', None),
    )
    return ok_response(document.model_dump(mode='json'))
