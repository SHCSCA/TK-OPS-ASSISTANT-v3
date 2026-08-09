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
    PositiveVersionPath,
    StablePathId,
    mutation_response,
    page_response,
    payload_dict,
    read_response,
    require_idempotency_key,
    resolve_ai_service,
)
from common.pagination import CursorPosition
from schemas.v1.ai_common import (
    AISuccessEnvelope,
    AISuccessEnvelopeWithMeta,
    ProfileStatusValue,
)
from schemas.v1.prompt_profiles import (
    PromptProfileDto,
    PromptProfileInput,
    PromptProfilePageDto,
    PromptVersionDto,
    PromptVersionInput,
)

router = APIRouter(
    prefix="/api/v1/system/prompt-profiles",
    tags=["v1-system-prompt-profiles"],
    dependencies=[Depends(require_active_license)],
)


class PromptProfilesServiceProtocol(Protocol):
    def list_prompt_profiles(
        self,
        *,
        capability_key: str | None,
        status: ProfileStatusValue | None,
        cursor: CursorPosition | None,
        limit: int,
    ) -> tuple[object, object | None]: ...

    def create_prompt_profile(
        self,
        payload: Mapping[str, object],
        *,
        idempotency_key: str,
        request_id: str,
        operation_id: str,
    ) -> object: ...

    def get_prompt_profile(self, profile_key: str) -> object: ...

    def get_prompt_version(
        self,
        profile_key: str,
        version: int,
    ) -> object: ...

    def create_prompt_version(
        self,
        profile_key: str,
        payload: Mapping[str, object],
        *,
        expected_revision: int,
        idempotency_key: str,
        request_id: str,
        operation_id: str,
    ) -> object: ...

    def activate_prompt_version(
        self,
        profile_key: str,
        version: int,
        *,
        expected_revision: int,
        idempotency_key: str,
        request_id: str,
        operation_id: str,
    ) -> object: ...


@router.get(
    "",
    response_model=AISuccessEnvelopeWithMeta[PromptProfilePageDto],
    response_model_exclude_unset=True,
)
def list_prompt_profiles(
    request: Request,
    capability_key: Annotated[
        str | None,
        Query(alias="capabilityKey", min_length=1, max_length=128),
    ] = None,
    profile_status: Annotated[
        ProfileStatusValue | None,
        Query(alias="status"),
    ] = None,
    pagination: PaginationParams = Depends(get_pagination),
    _: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    filters: dict[str, object] = {
        "capabilityKey": capability_key,
        "status": profile_status,
    }
    cursor = pagination.decode_cursor(
        scope="system",
        resource_kind="prompt-profiles.list",
        filters=filters,
    )
    result = _service(request).list_prompt_profiles(
        capability_key=capability_key,
        status=profile_status,
        cursor=cursor,
        limit=pagination.limit,
    )
    return page_response(
        result,
        PromptProfilePageDto,
        pagination=pagination,
        scope="system",
        resource_kind="prompt-profiles.list",
        filters=filters,
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=AISuccessEnvelopeWithMeta[PromptProfileDto],
    response_model_exclude_unset=True,
)
def create_prompt_profile(
    payload: PromptProfileInput,
    request: Request,
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = _service(request).create_prompt_profile(
        payload_dict(payload),
        idempotency_key=require_idempotency_key(context),
        request_id=context.request_id,
        operation_id=context.operation_id,
    )
    return mutation_response(
        result,
        PromptProfileDto,
        invalidations=("prompts", "ai-summary"),
    )


@router.get(
    "/{profile_key}",
    response_model=AISuccessEnvelope[PromptProfileDto],
)
def get_prompt_profile(
    request: Request,
    profile_key: StablePathId,
    _: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    return read_response(
        _service(request).get_prompt_profile(profile_key),
        PromptProfileDto,
    )


@router.get(
    "/{profile_key}/versions/{version}",
    response_model=AISuccessEnvelope[PromptVersionDto],
)
def get_prompt_version(
    request: Request,
    profile_key: StablePathId,
    version: PositiveVersionPath,
    _: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    return read_response(
        _service(request).get_prompt_version(profile_key, version),
        PromptVersionDto,
    )


@router.post(
    "/{profile_key}/versions",
    status_code=status.HTTP_201_CREATED,
    response_model=AISuccessEnvelopeWithMeta[PromptVersionDto],
    response_model_exclude_unset=True,
)
def create_prompt_version(
    payload: PromptVersionInput,
    request: Request,
    profile_key: StablePathId,
    revision: ExpectedRevision = Depends(get_expected_revision),
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = _service(request).create_prompt_version(
        profile_key,
        payload_dict(payload),
        expected_revision=revision.value,
        idempotency_key=require_idempotency_key(context),
        request_id=context.request_id,
        operation_id=context.operation_id,
    )
    return mutation_response(
        result,
        PromptVersionDto,
        invalidations=("prompts",),
    )


@router.post(
    "/{profile_key}/versions/{version}/activate",
    response_model=AISuccessEnvelopeWithMeta[PromptProfileDto],
    response_model_exclude_unset=True,
)
def activate_prompt_version(
    request: Request,
    profile_key: StablePathId,
    version: PositiveVersionPath,
    revision: ExpectedRevision = Depends(get_expected_revision),
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = _service(request).activate_prompt_version(
        profile_key,
        version,
        expected_revision=revision.value,
        idempotency_key=require_idempotency_key(context),
        request_id=context.request_id,
        operation_id=context.operation_id,
    )
    return mutation_response(
        result,
        PromptProfileDto,
        invalidations=("prompts", "routes", "recipes"),
    )


def _service(request: Request) -> PromptProfilesServiceProtocol:
    return cast(
        PromptProfilesServiceProtocol,
        resolve_ai_service(request, "prompts"),
    )
