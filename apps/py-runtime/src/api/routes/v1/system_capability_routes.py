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
from api.dependencies.revision import (
    ExpectedRevision,
    get_expected_revision,
    get_expected_revision_allow_zero,
)
from api.routes.v1.ai_route_support import (
    StablePathId,
    PositiveVersionPath,
    mutation_response,
    page_response,
    payload_dict,
    require_idempotency_key,
    resolve_ai_service,
)
from common.pagination import CursorPosition
from schemas.v1.ai_common import (
    AISuccessEnvelopeWithMeta,
    ValidationStatusValue,
)
from schemas.v1.capability_routes import (
    CapabilityRouteDto,
    CapabilityRouteInput,
    CapabilityRoutePageDto,
    CapabilityRouteRevisionDto,
    CapabilityRouteRevisionInput,
    CapabilityRouteRevisionPageDto,
    CapabilityRouteValidationDto,
)

router = APIRouter(
    prefix="/api/v1/system/capability-routes",
    tags=["v1-system-capability-routes"],
    dependencies=[Depends(require_active_license)],
)


class CapabilityRoutesServiceProtocol(Protocol):
    def list_capability_routes(
        self,
        *,
        capability_key: str | None,
        validation_status: ValidationStatusValue | None,
        cursor: CursorPosition | None,
        limit: int,
    ) -> tuple[object, object | None]: ...

    def put_capability_route(
        self,
        capability_key: str,
        payload: Mapping[str, object],
        *,
        expected_revision: int,
        idempotency_key: str,
        request_id: str,
        operation_id: str,
    ) -> object: ...

    def validate_capability_route(
        self,
        capability_key: str,
        *,
        idempotency_key: str,
        request_id: str,
        operation_id: str,
    ) -> object: ...


class CapabilityRouteRevisionsServiceProtocol(Protocol):
    def list_revisions(
        self,
        capability_key: str,
        *,
        cursor: CursorPosition | None,
        limit: int,
    ) -> tuple[object, object | None]: ...

    def create_revision(
        self,
        capability_key: str,
        payload: Mapping[str, object],
        *,
        expected_revision: int,
        idempotency_key: str,
    ) -> object: ...

    def validate_revision(
        self,
        capability_key: str,
        revision: int,
        *,
        idempotency_key: str,
    ) -> object: ...

    def activate_revision(
        self,
        capability_key: str,
        revision: int,
        *,
        expected_revision: int,
        idempotency_key: str,
    ) -> object: ...

@router.get(
    "",
    response_model=AISuccessEnvelopeWithMeta[CapabilityRoutePageDto],
    response_model_exclude_unset=True,
)
def list_capability_routes(
    request: Request,
    capability_key: Annotated[
        str | None,
        Query(alias="capabilityKey", min_length=1, max_length=128),
    ] = None,
    validation_status: Annotated[
        ValidationStatusValue | None,
        Query(alias="validationStatus"),
    ] = None,
    pagination: PaginationParams = Depends(get_pagination),
    _: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    filters: dict[str, object] = {
        "capabilityKey": capability_key,
        "validationStatus": validation_status,
    }
    cursor = pagination.decode_cursor(
        scope="system",
        resource_kind="capability-routes.list",
        filters=filters,
    )
    result = _service(request).list_capability_routes(
        capability_key=capability_key,
        validation_status=validation_status,
        cursor=cursor,
        limit=pagination.limit,
    )
    return page_response(
        result,
        CapabilityRoutePageDto,
        pagination=pagination,
        scope="system",
        resource_kind="capability-routes.list",
        filters=filters,
    )


@router.get(
    "/{capability_key}/revisions",
    response_model=AISuccessEnvelopeWithMeta[CapabilityRouteRevisionPageDto],
    response_model_exclude_unset=True,
)
def list_capability_route_revisions(
    request: Request,
    capability_key: StablePathId,
    pagination: PaginationParams = Depends(get_pagination),
    _: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    filters: dict[str, object] = {"capabilityKey": capability_key}
    cursor = pagination.decode_cursor(
        scope="system",
        resource_kind="capability-route-revisions.list",
        filters=filters,
    )
    result = _revision_service(request).list_revisions(
        capability_key,
        cursor=cursor,
        limit=pagination.limit,
    )
    return page_response(
        result,
        CapabilityRouteRevisionPageDto,
        pagination=pagination,
        scope="system",
        resource_kind="capability-route-revisions.list",
        filters=filters,
    )


@router.post(
    "/{capability_key}/revisions",
    status_code=status.HTTP_201_CREATED,
    response_model=AISuccessEnvelopeWithMeta[CapabilityRouteRevisionDto],
    response_model_exclude_unset=True,
)
def create_capability_route_revision(
    payload: CapabilityRouteRevisionInput,
    request: Request,
    capability_key: StablePathId,
    revision: ExpectedRevision = Depends(get_expected_revision_allow_zero),
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = _revision_service(request).create_revision(
        capability_key,
        payload_dict(payload),
        expected_revision=revision.value,
        idempotency_key=require_idempotency_key(context),
    )
    return mutation_response(
        result,
        CapabilityRouteRevisionDto,
        invalidations=("routes", "recipes"),
    )


@router.post(
    "/{capability_key}/revisions/{route_revision}/validate",
    response_model=AISuccessEnvelopeWithMeta[CapabilityRouteValidationDto],
    response_model_exclude_unset=True,
)
def validate_capability_route_revision(
    request: Request,
    capability_key: StablePathId,
    route_revision: PositiveVersionPath,
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = _revision_service(request).validate_revision(
        capability_key,
        route_revision,
        idempotency_key=require_idempotency_key(context),
    )
    return mutation_response(
        result,
        CapabilityRouteValidationDto,
        invalidations=("routes", "recipes"),
    )


@router.post(
    "/{capability_key}/revisions/{route_revision}/activate",
    response_model=AISuccessEnvelopeWithMeta[CapabilityRouteDto],
    response_model_exclude_unset=True,
)
def activate_capability_route_revision(
    request: Request,
    capability_key: StablePathId,
    route_revision: PositiveVersionPath,
    revision: ExpectedRevision = Depends(get_expected_revision),
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = _revision_service(request).activate_revision(
        capability_key,
        route_revision,
        expected_revision=revision.value,
        idempotency_key=require_idempotency_key(context),
    )
    return mutation_response(
        result,
        CapabilityRouteDto,
        invalidations=("routes", "ai-summary", "recipes"),
    )


@router.put(
    "/{capability_key}",
    response_model=AISuccessEnvelopeWithMeta[CapabilityRouteDto],
    response_model_exclude_unset=True,
)
def put_capability_route(
    payload: CapabilityRouteInput,
    request: Request,
    capability_key: StablePathId,
    revision: ExpectedRevision = Depends(
        get_expected_revision_allow_zero
    ),
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = _service(request).put_capability_route(
        capability_key,
        payload_dict(payload),
        expected_revision=revision.value,
        idempotency_key=require_idempotency_key(context),
        request_id=context.request_id,
        operation_id=context.operation_id,
    )
    response = mutation_response(
        result,
        CapabilityRouteDto,
        invalidations=("routes", "ai-summary", "recipes"),
    )
    cast(dict[str, object], response["meta"])["compatibilityAdapter"] = True
    return response


@router.post(
    "/{capability_key}/validate",
    response_model=AISuccessEnvelopeWithMeta[CapabilityRouteValidationDto],
    response_model_exclude_unset=True,
)
def validate_capability_route(
    request: Request,
    capability_key: StablePathId,
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = _service(request).validate_capability_route(
        capability_key,
        idempotency_key=require_idempotency_key(context),
        request_id=context.request_id,
        operation_id=context.operation_id,
    )
    response = mutation_response(
        result,
        CapabilityRouteValidationDto,
        invalidations=("routes", "recipes"),
    )
    cast(dict[str, object], response["meta"])["compatibilityAdapter"] = True
    return response


def _service(request: Request) -> CapabilityRoutesServiceProtocol:
    return cast(
        CapabilityRoutesServiceProtocol,
        resolve_ai_service(request, "routes"),
    )


def _revision_service(
    request: Request,
) -> CapabilityRouteRevisionsServiceProtocol:
    return cast(
        CapabilityRouteRevisionsServiceProtocol,
        resolve_ai_service(request, "route_revisions"),
    )
