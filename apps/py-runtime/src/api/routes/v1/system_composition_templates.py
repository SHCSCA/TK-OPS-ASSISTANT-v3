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
from schemas.v1.composition_templates import (
    CompositionTemplateDto,
    CompositionTemplateInput,
    CompositionTemplatePageDto,
    CompositionTemplateType,
    CompositionTemplateValidationDto,
    CompositionTemplateVersionDto,
    CompositionTemplateVersionInput,
)

router = APIRouter(
    prefix="/api/v1/system/composition-templates",
    tags=["v1-system-composition-templates"],
    dependencies=[Depends(require_active_license)],
)


class CompositionTemplatesServiceProtocol(Protocol):
    def list_composition_templates(
        self,
        *,
        template_type: CompositionTemplateType | None,
        status: ProfileStatusValue | None,
        cursor: CursorPosition | None,
        limit: int,
    ) -> tuple[object, object | None]: ...

    def create_composition_template(
        self,
        payload: Mapping[str, object],
        *,
        idempotency_key: str,
        request_id: str,
        operation_id: str,
    ) -> object: ...

    def get_composition_template(self, template_key: str) -> object: ...

    def get_composition_template_version(
        self,
        template_key: str,
        version: int,
    ) -> object: ...

    def create_composition_template_version(
        self,
        template_key: str,
        payload: Mapping[str, object],
        *,
        expected_revision: int,
        idempotency_key: str,
        request_id: str,
        operation_id: str,
    ) -> object: ...

    def validate_composition_template_version(
        self,
        template_key: str,
        version: int,
        *,
        idempotency_key: str,
        request_id: str,
        operation_id: str,
    ) -> object: ...

    def activate_composition_template_version(
        self,
        template_key: str,
        version: int,
        *,
        expected_revision: int,
        idempotency_key: str,
        request_id: str,
        operation_id: str,
    ) -> object: ...


@router.get(
    "",
    response_model=AISuccessEnvelopeWithMeta[CompositionTemplatePageDto],
    response_model_exclude_unset=True,
)
def list_composition_templates(
    request: Request,
    template_type: Annotated[
        CompositionTemplateType | None,
        Query(alias="templateType"),
    ] = None,
    template_status: Annotated[
        ProfileStatusValue | None,
        Query(alias="status"),
    ] = None,
    pagination: PaginationParams = Depends(get_pagination),
    _: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    filters: dict[str, object] = {
        "templateType": template_type,
        "status": template_status,
    }
    cursor = pagination.decode_cursor(
        scope="system",
        resource_kind="composition-templates.list",
        filters=filters,
    )
    result = _service(request).list_composition_templates(
        template_type=template_type,
        status=template_status,
        cursor=cursor,
        limit=pagination.limit,
    )
    return page_response(
        result,
        CompositionTemplatePageDto,
        pagination=pagination,
        scope="system",
        resource_kind="composition-templates.list",
        filters=filters,
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=AISuccessEnvelopeWithMeta[CompositionTemplateDto],
    response_model_exclude_unset=True,
)
def create_composition_template(
    payload: CompositionTemplateInput,
    request: Request,
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = _service(request).create_composition_template(
        payload_dict(payload),
        idempotency_key=require_idempotency_key(context),
        request_id=context.request_id,
        operation_id=context.operation_id,
    )
    return mutation_response(
        result,
        CompositionTemplateDto,
        invalidations=("composition-templates",),
    )


@router.get(
    "/{template_key}",
    response_model=AISuccessEnvelope[CompositionTemplateDto],
)
def get_composition_template(
    request: Request,
    template_key: StablePathId,
    _: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    return read_response(
        _service(request).get_composition_template(template_key),
        CompositionTemplateDto,
    )


@router.get(
    "/{template_key}/versions/{version}",
    response_model=AISuccessEnvelope[CompositionTemplateVersionDto],
)
def get_composition_template_version(
    request: Request,
    template_key: StablePathId,
    version: PositiveVersionPath,
    _: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    return read_response(
        _service(request).get_composition_template_version(
            template_key,
            version,
        ),
        CompositionTemplateVersionDto,
    )


@router.post(
    "/{template_key}/versions",
    status_code=status.HTTP_201_CREATED,
    response_model=AISuccessEnvelopeWithMeta[CompositionTemplateVersionDto],
    response_model_exclude_unset=True,
)
def create_composition_template_version(
    payload: CompositionTemplateVersionInput,
    request: Request,
    template_key: StablePathId,
    revision: ExpectedRevision = Depends(get_expected_revision),
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = _service(request).create_composition_template_version(
        template_key,
        payload_dict(payload),
        expected_revision=revision.value,
        idempotency_key=require_idempotency_key(context),
        request_id=context.request_id,
        operation_id=context.operation_id,
    )
    return mutation_response(
        result,
        CompositionTemplateVersionDto,
        invalidations=("composition-templates",),
    )


@router.post(
    "/{template_key}/versions/{version}/validate",
    response_model=AISuccessEnvelopeWithMeta[
        CompositionTemplateValidationDto
    ],
    response_model_exclude_unset=True,
)
def validate_composition_template_version(
    request: Request,
    template_key: StablePathId,
    version: PositiveVersionPath,
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = _service(request).validate_composition_template_version(
        template_key,
        version,
        idempotency_key=require_idempotency_key(context),
        request_id=context.request_id,
        operation_id=context.operation_id,
    )
    return mutation_response(
        result,
        CompositionTemplateValidationDto,
        invalidations=("composition-templates", "recipes"),
    )


@router.post(
    "/{template_key}/versions/{version}/activate",
    response_model=AISuccessEnvelopeWithMeta[CompositionTemplateDto],
    response_model_exclude_unset=True,
)
def activate_composition_template_version(
    request: Request,
    template_key: StablePathId,
    version: PositiveVersionPath,
    revision: ExpectedRevision = Depends(get_expected_revision),
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = _service(request).activate_composition_template_version(
        template_key,
        version,
        expected_revision=revision.value,
        idempotency_key=require_idempotency_key(context),
        request_id=context.request_id,
        operation_id=context.operation_id,
    )
    return mutation_response(
        result,
        CompositionTemplateDto,
        invalidations=("composition-templates", "recipes"),
    )


def _service(request: Request) -> CompositionTemplatesServiceProtocol:
    return cast(
        CompositionTemplatesServiceProtocol,
        resolve_ai_service(request, "templates"),
    )
