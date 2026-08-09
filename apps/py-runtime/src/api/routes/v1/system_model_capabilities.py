from __future__ import annotations

from collections.abc import Mapping
from typing import Annotated, Protocol, cast

from fastapi import APIRouter, Depends, Query, Request, status

from api.dependencies.license_guard import require_active_license
from api.dependencies.pagination import PaginationParams, get_pagination
from api.dependencies.request_context import (
    RequestContext,
    get_request_context,
)
from api.routes.v1.ai_route_support import (
    StablePathId,
    list_response,
    page_response,
    payload_dict,
    require_idempotency_key,
    resolve_ai_service,
    task_accepted_response,
)
from common.identifiers import STABLE_ID_PATTERN_TEXT
from common.pagination import CursorPosition
from schemas.v1.ai_common import (
    AISuccessEnvelope,
    AISuccessEnvelopeWithMeta,
)
from schemas.v1.model_profiles import (
    CapabilityCheckInput,
    ModelAvailability,
    ModelCapabilityDto,
    ModelCapabilityPageDto,
)
from schemas.v1.tasks import TaskAcceptedDto

router = APIRouter(
    tags=["v1-system-model-capabilities"],
    dependencies=[Depends(require_active_license)],
)


class ModelCapabilitiesServiceProtocol(Protocol):
    def list_model_capabilities(
        self,
        *,
        provider_id: str | None,
        model_profile_id: str | None,
        capability_key: str | None,
        availability: ModelAvailability | None,
        cursor: CursorPosition | None,
        limit: int,
    ) -> tuple[object, object | None]: ...

    def get_model_capabilities(
        self,
        model_profile_id: str,
    ) -> object: ...

    async def submit_capability_checks(
        self,
        model_profile_id: str,
        payload: Mapping[str, object],
        *,
        idempotency_key: str,
        request_id: str,
        operation_id: str,
    ) -> object: ...


@router.get(
    "/api/v1/system/model-capabilities",
    response_model=AISuccessEnvelopeWithMeta[ModelCapabilityPageDto],
    response_model_exclude_unset=True,
)
def list_model_capabilities(
    request: Request,
    provider_id: Annotated[
        str | None,
        Query(
            alias="providerId",
            min_length=1,
            max_length=128,
            pattern=STABLE_ID_PATTERN_TEXT,
        ),
    ] = None,
    model_profile_id: Annotated[
        str | None,
        Query(
            alias="modelProfileId",
            min_length=1,
            max_length=128,
            pattern=STABLE_ID_PATTERN_TEXT,
        ),
    ] = None,
    capability_key: Annotated[
        str | None,
        Query(alias="capabilityKey", min_length=1, max_length=128),
    ] = None,
    availability: Annotated[ModelAvailability | None, Query()] = None,
    pagination: PaginationParams = Depends(get_pagination),
    _: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    filters: dict[str, object] = {
        "providerId": provider_id,
        "modelProfileId": model_profile_id,
        "capabilityKey": capability_key,
        "availability": availability,
    }
    cursor = pagination.decode_cursor(
        scope="system",
        resource_kind="model-capabilities.list",
        filters=filters,
    )
    result = _service(request).list_model_capabilities(
        provider_id=provider_id,
        model_profile_id=model_profile_id,
        capability_key=capability_key,
        availability=availability,
        cursor=cursor,
        limit=pagination.limit,
    )
    return page_response(
        result,
        ModelCapabilityPageDto,
        pagination=pagination,
        scope="system",
        resource_kind="model-capabilities.list",
        filters=filters,
    )


@router.get(
    "/api/v1/system/models/{model_profile_id}/capabilities",
    response_model=AISuccessEnvelope[list[ModelCapabilityDto]],
)
def get_model_capabilities(
    request: Request,
    model_profile_id: StablePathId,
    _: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = _service(request).get_model_capabilities(model_profile_id)
    return list_response(result, ModelCapabilityDto)


@router.post(
    "/api/v1/system/models/{model_profile_id}/capability-checks",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=AISuccessEnvelopeWithMeta[TaskAcceptedDto],
    response_model_exclude_unset=True,
)
async def submit_model_capability_checks(
    payload: CapabilityCheckInput,
    request: Request,
    model_profile_id: StablePathId,
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = await _service(request).submit_capability_checks(
        model_profile_id,
        payload_dict(payload),
        idempotency_key=require_idempotency_key(context),
        request_id=context.request_id,
        operation_id=context.operation_id,
    )
    return task_accepted_response(
        result,
        invalidations=("system:tasks", "model-capabilities"),
    )


def _service(request: Request) -> ModelCapabilitiesServiceProtocol:
    return cast(
        ModelCapabilitiesServiceProtocol,
        resolve_ai_service(request, "models"),
    )
