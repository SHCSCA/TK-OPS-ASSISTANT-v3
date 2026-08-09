from __future__ import annotations

from fastapi import APIRouter, Request

from api.routes.ai_legacy_support import reject_legacy_ai_write
from schemas.envelope import ok_response
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
    request: Request,
) -> None:
    reject_legacy_ai_write(
        request,
        replacement="POST /api/v1/system/prompt-profiles",
    )


@router.put("/{template_id}")
def update_prompt_template(
    template_id: str,
    request: Request,
) -> None:
    del template_id
    reject_legacy_ai_write(
        request,
        replacement=(
            "POST /api/v1/system/prompt-profiles/"
            "{profile_key}/versions"
        ),
    )


@router.delete("/{template_id}")
def delete_prompt_template(
    template_id: str,
    request: Request,
) -> None:
    del template_id
    reject_legacy_ai_write(
        request,
        replacement="Prompt 版本不可删除；请创建并激活新版本",
    )
