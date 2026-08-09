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
    task_accepted_response,
)
from common.pagination import CursorPosition
from schemas.v1.ai_common import (
    AISuccessEnvelope,
    AISuccessEnvelopeWithMeta,
)
from schemas.v1.provider_profiles import (
    CredentialSummaryDto,
    ModelDiscoveryInput,
    ProviderCheckInput,
    ProviderCreateInput,
    ProviderDto,
    ProviderHealthStatus,
    ProviderPageDto,
    ProviderPatchInput,
    ProviderCredentialInput,
)
from schemas.v1.tasks import TaskAcceptedDto

router = APIRouter(
    prefix="/api/v1/system/providers",
    tags=["v1-system-providers"],
    dependencies=[Depends(require_active_license)],
)


class ProviderProfilesServiceProtocol(Protocol):
    def list_providers(
        self,
        *,
        enabled: bool | None,
        health_status: ProviderHealthStatus | None,
        cursor: CursorPosition | None,
        limit: int,
    ) -> tuple[object, object | None]: ...

    def create_provider(
        self,
        payload: Mapping[str, object],
        *,
        idempotency_key: str,
        request_id: str,
        operation_id: str,
    ) -> object: ...

    def get_provider(
        self,
        provider_id: str,
    ) -> object: ...

    def update_provider(
        self,
        provider_id: str,
        payload: Mapping[str, object],
        *,
        expected_revision: int,
        request_id: str,
        operation_id: str,
    ) -> object: ...

    def update_credential(
        self,
        provider_id: str,
        payload: Mapping[str, object],
        *,
        expected_revision: int,
        request_id: str,
        operation_id: str,
    ) -> object: ...

    async def submit_provider_check(
        self,
        provider_id: str,
        payload: Mapping[str, object],
        *,
        idempotency_key: str,
        request_id: str,
        operation_id: str,
    ) -> object: ...

    async def submit_model_discovery(
        self,
        provider_id: str,
        payload: Mapping[str, object],
        *,
        idempotency_key: str,
        request_id: str,
        operation_id: str,
    ) -> object: ...


@router.get(
    "",
    response_model=AISuccessEnvelopeWithMeta[ProviderPageDto],
    response_model_exclude_unset=True,
)
def list_providers(
    request: Request,
    enabled: Annotated[bool | None, Query()] = None,
    health_status: Annotated[
        ProviderHealthStatus | None,
        Query(alias="healthStatus"),
    ] = None,
    pagination: PaginationParams = Depends(get_pagination),
    _: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    filters: dict[str, object] = {
        "enabled": enabled,
        "healthStatus": health_status,
    }
    cursor = pagination.decode_cursor(
        scope="system",
        resource_kind="providers.list",
        filters=filters,
    )
    result = _service(request).list_providers(
        enabled=enabled,
        health_status=health_status,
        cursor=cursor,
        limit=pagination.limit,
    )
    return page_response(
        result,
        ProviderPageDto,
        pagination=pagination,
        scope="system",
        resource_kind="providers.list",
        filters=filters,
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=AISuccessEnvelopeWithMeta[ProviderDto],
    response_model_exclude_unset=True,
)
def create_provider(
    payload: ProviderCreateInput,
    request: Request,
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = _service(request).create_provider(
        payload_dict(payload),
        idempotency_key=require_idempotency_key(context),
        request_id=context.request_id,
        operation_id=context.operation_id,
    )
    return mutation_response(
        result,
        ProviderDto,
        invalidations=("providers", "ai-summary"),
    )


@router.get(
    "/{provider_id}",
    response_model=AISuccessEnvelope[ProviderDto],
)
def get_provider(
    request: Request,
    provider_id: StablePathId,
    _: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = _service(request).get_provider(provider_id)
    return read_response(result, ProviderDto)


@router.patch(
    "/{provider_id}",
    response_model=AISuccessEnvelopeWithMeta[ProviderDto],
    response_model_exclude_unset=True,
)
def update_provider(
    payload: ProviderPatchInput,
    request: Request,
    provider_id: StablePathId,
    revision: ExpectedRevision = Depends(get_expected_revision),
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = _service(request).update_provider(
        provider_id,
        payload_dict(payload),
        expected_revision=revision.value,
        request_id=context.request_id,
        operation_id=context.operation_id,
    )
    return mutation_response(
        result,
        ProviderDto,
        invalidations=("providers", "models", "routes", "recipes"),
    )


@router.put(
    "/{provider_id}/credential",
    response_model=AISuccessEnvelopeWithMeta[CredentialSummaryDto],
    response_model_exclude_unset=True,
)
def update_provider_credential(
    payload: ProviderCredentialInput,
    request: Request,
    provider_id: StablePathId,
    revision: ExpectedRevision = Depends(get_expected_revision),
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = _service(request).update_credential(
        provider_id,
        payload_dict(payload),
        expected_revision=revision.value,
        request_id=context.request_id,
        operation_id=context.operation_id,
    )
    return mutation_response(
        result,
        CredentialSummaryDto,
        invalidations=("provider", "ai-summary"),
    )


@router.post(
    "/{provider_id}/checks",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=AISuccessEnvelopeWithMeta[TaskAcceptedDto],
    response_model_exclude_unset=True,
)
async def submit_provider_check(
    payload: ProviderCheckInput,
    request: Request,
    provider_id: StablePathId,
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = await _service(request).submit_provider_check(
        provider_id,
        payload_dict(payload),
        idempotency_key=require_idempotency_key(context),
        request_id=context.request_id,
        operation_id=context.operation_id,
    )
    return task_accepted_response(
        result,
        invalidations=("system:tasks", "provider"),
    )


@router.post(
    "/{provider_id}/model-discovery",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=AISuccessEnvelopeWithMeta[TaskAcceptedDto],
    response_model_exclude_unset=True,
)
async def submit_model_discovery(
    payload: ModelDiscoveryInput,
    request: Request,
    provider_id: StablePathId,
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = await _service(request).submit_model_discovery(
        provider_id,
        payload_dict(payload),
        idempotency_key=require_idempotency_key(context),
        request_id=context.request_id,
        operation_id=context.operation_id,
    )
    return task_accepted_response(
        result,
        invalidations=("system:tasks", "models"),
    )


def _service(request: Request) -> ProviderProfilesServiceProtocol:
    return cast(
        ProviderProfilesServiceProtocol,
        resolve_ai_service(request, "providers"),
    )
