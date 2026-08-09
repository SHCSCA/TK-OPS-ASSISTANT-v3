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
from api.dependencies.revision import ExpectedRevision, get_expected_revision
from api.routes.v1.ai_route_support import (
    StablePathId,
    mutation_response,
    page_response,
    payload_dict,
    read_response,
    require_idempotency_key,
    resolve_ai_service,
)
from common.identifiers import STABLE_ID_PATTERN_TEXT
from common.pagination import CursorPosition
from schemas.v1.ai_common import (
    AISuccessEnvelope,
    AISuccessEnvelopeWithMeta,
)
from schemas.v1.model_profiles import (
    ModelCreateInput,
    ModelPageDto,
    ModelPatchInput,
    ModelProfileDto,
)

router = APIRouter(
    prefix="/api/v1/system/models",
    tags=["v1-system-models"],
    dependencies=[Depends(require_active_license)],
)


class ModelProfilesServiceProtocol(Protocol):
    def list_models(
        self,
        *,
        provider_id: str | None,
        enabled: bool | None,
        capability_key: str | None,
        cursor: CursorPosition | None,
        limit: int,
    ) -> tuple[object, object | None]: ...

    def create_model(
        self,
        payload: Mapping[str, object],
        *,
        idempotency_key: str,
        request_id: str,
        operation_id: str,
    ) -> object: ...

    def get_model(
        self,
        model_profile_id: str,
    ) -> object: ...

    def update_model(
        self,
        model_profile_id: str,
        payload: Mapping[str, object],
        *,
        expected_revision: int,
        request_id: str,
        operation_id: str,
    ) -> object: ...


@router.get(
    "",
    response_model=AISuccessEnvelopeWithMeta[ModelPageDto],
    response_model_exclude_unset=True,
)
def list_models(
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
    enabled: Annotated[bool | None, Query()] = None,
    capability_key: Annotated[
        str | None,
        Query(alias="capabilityKey", min_length=1, max_length=128),
    ] = None,
    pagination: PaginationParams = Depends(get_pagination),
    _: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    filters: dict[str, object] = {
        "providerId": provider_id,
        "enabled": enabled,
        "capabilityKey": capability_key,
    }
    cursor = pagination.decode_cursor(
        scope="system",
        resource_kind="models.list",
        filters=filters,
    )
    result = _service(request).list_models(
        provider_id=provider_id,
        enabled=enabled,
        capability_key=capability_key,
        cursor=cursor,
        limit=pagination.limit,
    )
    return page_response(
        result,
        ModelPageDto,
        pagination=pagination,
        scope="system",
        resource_kind="models.list",
        filters=filters,
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=AISuccessEnvelopeWithMeta[ModelProfileDto],
    response_model_exclude_unset=True,
)
def create_model(
    payload: ModelCreateInput,
    request: Request,
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = _service(request).create_model(
        payload_dict(payload),
        idempotency_key=require_idempotency_key(context),
        request_id=context.request_id,
        operation_id=context.operation_id,
    )
    return mutation_response(
        result,
        ModelProfileDto,
        invalidations=("models", "routes", "recipes"),
    )


@router.get(
    "/{model_profile_id}",
    response_model=AISuccessEnvelope[ModelProfileDto],
)
def get_model(
    request: Request,
    model_profile_id: StablePathId,
    _: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = _service(request).get_model(model_profile_id)
    return read_response(result, ModelProfileDto)


@router.patch(
    "/{model_profile_id}",
    response_model=AISuccessEnvelopeWithMeta[ModelProfileDto],
    response_model_exclude_unset=True,
)
def update_model(
    payload: ModelPatchInput,
    request: Request,
    model_profile_id: StablePathId,
    revision: ExpectedRevision = Depends(get_expected_revision),
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = _service(request).update_model(
        model_profile_id,
        payload_dict(payload),
        expected_revision=revision.value,
        request_id=context.request_id,
        operation_id=context.operation_id,
    )
    return mutation_response(
        result,
        ModelProfileDto,
        invalidations=("models", "routes", "recipes"),
    )


def _service(request: Request) -> ModelProfilesServiceProtocol:
    return cast(
        ModelProfilesServiceProtocol,
        resolve_ai_service(request, "models"),
    )
