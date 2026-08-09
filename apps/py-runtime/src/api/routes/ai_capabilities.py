from __future__ import annotations

from fastapi import APIRouter, Request

from api.routes.ai_legacy_support import reject_legacy_ai_write
from schemas.envelope import ok_response
from services.ai_capability_service import AICapabilityService

router = APIRouter(prefix='/api/settings/ai-capabilities', tags=['ai-capabilities'])


def get_ai_capability_service(request: Request) -> AICapabilityService:
    service = request.app.state.ai_capability_service
    assert isinstance(service, AICapabilityService)
    return service


@router.get('')
def get_ai_capability_settings(request: Request) -> dict[str, object]:
    settings = get_ai_capability_service(request).get_settings()
    return ok_response(settings.model_dump(mode='json'))


@router.get('/support-matrix')
def get_ai_capability_support_matrix(request: Request) -> dict[str, object]:
    matrix = get_ai_capability_service(request).get_capability_support_matrix()
    return ok_response(matrix.model_dump(mode='json'))


@router.put('')
def update_ai_capability_settings(
    request: Request,
) -> None:
    reject_legacy_ai_write(
        request,
        replacement=(
            "PUT /api/v1/system/capability-routes/{capability_key}"
        ),
    )


@router.put('/providers/{provider_id}/secret')
def set_provider_secret(
    provider_id: str,
    request: Request,
) -> None:
    del provider_id
    reject_legacy_ai_write(
        request,
        replacement=(
            "PUT /api/v1/system/providers/{provider_id}/credential"
        ),
    )


@router.post('/providers/{provider_id}/health-check')
def check_provider_health(
    provider_id: str,
    request: Request,
) -> None:
    del provider_id
    reject_legacy_ai_write(
        request,
        replacement=(
            "POST /api/v1/system/providers/{provider_id}/checks"
        ),
    )
