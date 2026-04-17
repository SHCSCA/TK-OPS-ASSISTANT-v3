from __future__ import annotations

from fastapi import APIRouter, Request

from schemas.envelope import ok_response
from schemas.prompt_templates import PromptTemplateInput, PromptTemplateUpdateInput
from services.prompt_template_service import PromptTemplateService

router = APIRouter(prefix="/api/prompt-templates", tags=["prompt-templates"])


def get_prompt_template_service(request: Request) -> PromptTemplateService:
    service = request.app.state.prompt_template_service
    assert isinstance(service, PromptTemplateService)
    return service


@router.get("")
def list_prompt_templates(request: Request, kind: str | None = None) -> dict[str, object]:
    templates = get_prompt_template_service(request).list_templates(kind)
    return ok_response([item.model_dump(mode="json") for item in templates])


@router.post("")
def create_prompt_template(
    payload: PromptTemplateInput,
    request: Request,
) -> dict[str, object]:
    template = get_prompt_template_service(request).create_template(payload)
    return ok_response(template.model_dump(mode="json"))


@router.put("/{template_id}")
def update_prompt_template(
    template_id: str,
    payload: PromptTemplateUpdateInput,
    request: Request,
) -> dict[str, object]:
    template = get_prompt_template_service(request).update_template(template_id, payload)
    return ok_response(template.model_dump(mode="json"))


@router.delete("/{template_id}")
def delete_prompt_template(template_id: str, request: Request) -> dict[str, object]:
    result = get_prompt_template_service(request).delete_template(template_id)
    return ok_response(result)
