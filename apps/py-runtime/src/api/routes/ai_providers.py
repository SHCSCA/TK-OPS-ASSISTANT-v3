from __future__ import annotations

from fastapi import APIRouter, Request

from schemas.envelope import ok_response
from services.ai_capability_service import AICapabilityService

router = APIRouter(prefix='/api/settings/ai-providers', tags=['ai-providers'])


def get_ai_capability_service(request: Request) -> AICapabilityService:
    service = request.app.state.ai_capability_service
    assert isinstance(service, AICapabilityService)
    return service


@router.get('/catalog')
def get_ai_provider_catalog(request: Request) -> dict[str, object]:
    catalog = get_ai_capability_service(request).get_provider_catalog()
    return ok_response([item.model_dump(mode='json') for item in catalog])


@router.get('/{provider_id}/models')
def get_ai_provider_models(provider_id: str, request: Request) -> dict[str, object]:
    models = get_ai_capability_service(request).get_provider_models(provider_id)
    return ok_response([item.model_dump(mode='json') for item in models])


@router.post('/{provider_id}/models/refresh')
def refresh_ai_provider_models(provider_id: str, request: Request) -> dict[str, object]:
    result = get_ai_capability_service(request).refresh_provider_models(provider_id)
    return ok_response(result.model_dump(mode='json'))
