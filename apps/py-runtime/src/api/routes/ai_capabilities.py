from __future__ import annotations

from fastapi import APIRouter, Request

from schemas.ai_capabilities import (
    AICapabilityConfigListInput,
    AIProviderHealthCheckInput,
    AIProviderSecretInput,
)
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
    payload: AICapabilityConfigListInput,
    request: Request,
) -> dict[str, object]:
    settings = get_ai_capability_service(request).update_capabilities(payload.capabilities)
    return ok_response(settings.model_dump(mode='json'))


@router.put('/providers/{provider_id}/secret')
def set_provider_secret(
    provider_id: str,
    payload: AIProviderSecretInput,
    request: Request,
) -> dict[str, object]:
    status = get_ai_capability_service(request).set_provider_secret(
        provider_id,
        api_key=payload.apiKey,
        base_url=payload.baseUrl,
    )
    return ok_response(status.model_dump(mode='json'))


@router.post('/providers/{provider_id}/health-check')
def check_provider_health(
    provider_id: str,
    request: Request,
    payload: AIProviderHealthCheckInput | None = None,
) -> dict[str, object]:
    status = get_ai_capability_service(request).check_provider_health(
        provider_id,
        model=payload.model if payload else None,
    )
    return ok_response(status.model_dump(mode='json'))
