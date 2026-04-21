from __future__ import annotations

from fastapi import APIRouter, Request

from schemas.ai_capabilities import AIProviderModelUpsertInput
from schemas.envelope import ok_response
from services.ai_capability_service import AICapabilityService

router = APIRouter(prefix="/api/ai-providers", tags=["ai-provider-runtime"])


def _svc(request: Request) -> AICapabilityService:
    service = request.app.state.ai_capability_service
    assert isinstance(service, AICapabilityService)
    return service


@router.get("/health")
def get_ai_provider_health(request: Request) -> dict[str, object]:
    overview = _svc(request).get_provider_health_overview()
    return ok_response(overview.model_dump(mode="json"))


@router.post("/health/refresh")
def refresh_ai_provider_health(request: Request) -> dict[str, object]:
    overview = _svc(request).refresh_provider_health()
    return ok_response(overview.model_dump(mode="json"))


@router.put("/{provider_id}/models/{model_id}")
def upsert_ai_provider_model(
    provider_id: str,
    model_id: str,
    payload: AIProviderModelUpsertInput,
    request: Request,
) -> dict[str, object]:
    result = _svc(request).upsert_provider_model(provider_id, model_id, payload)
    return ok_response(result.model_dump(mode="json"))
