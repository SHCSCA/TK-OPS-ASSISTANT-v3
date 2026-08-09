from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, cast

from fastapi import APIRouter, Depends, Request, status

from api.dependencies.account_scope import get_account_scope
from api.dependencies.license_guard import require_active_license
from api.dependencies.pagination import PaginationParams, get_pagination
from api.dependencies.request_context import (
    RequestContext,
    get_request_context,
)
from api.dependencies.revision import ExpectedRevision, get_expected_revision
from api.routes.v1.ai_route_support import (
    PositiveVersionPath,
    mutation_response,
    page_response,
    payload_dict,
    read_response,
    require_idempotency_key,
    resolve_ai_service,
)
from common.pagination import CursorPosition
from schemas.v1.account_ai_recipe import (
    AIRecipeDto,
    AIRecipeValidationDto,
    AIRecipeVersionDto,
    AIRecipeVersionPageDto,
    AccountAIRecipeVersionInput,
)
from schemas.v1.ai_common import (
    AISuccessEnvelope,
    AISuccessEnvelopeWithMeta,
)
from services.accounts.scope import AccountScope

router = APIRouter(
    prefix="/api/v1/accounts/{account_id}/ai-recipe",
    tags=["v1-account-ai-recipe"],
    dependencies=[Depends(require_active_license)],
)


class AccountAIRecipesServiceProtocol(Protocol):
    def get_account_ai_recipe(self, account_id: str) -> object: ...

    def list_account_ai_recipe_versions(
        self,
        account_id: str,
        *,
        cursor: CursorPosition | None,
        limit: int,
    ) -> tuple[object, object | None]: ...

    def create_account_ai_recipe_version(
        self,
        account_id: str,
        payload: Mapping[str, object],
        *,
        expected_revision: int,
        idempotency_key: str,
        request_id: str,
        operation_id: str,
    ) -> object: ...

    def validate_account_ai_recipe_version(
        self,
        account_id: str,
        version: int,
        *,
        idempotency_key: str,
        request_id: str,
        operation_id: str,
    ) -> object: ...

    def activate_account_ai_recipe_version(
        self,
        account_id: str,
        version: int,
        *,
        expected_revision: int,
        idempotency_key: str,
        request_id: str,
        operation_id: str,
    ) -> object: ...


@router.get(
    "",
    response_model=AISuccessEnvelope[AIRecipeDto],
)
def get_account_ai_recipe(
    request: Request,
    scope: AccountScope = Depends(get_account_scope),
    _: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    return read_response(
        _service(request).get_account_ai_recipe(scope.account_id),
        AIRecipeDto,
    )


@router.get(
    "/versions",
    response_model=AISuccessEnvelopeWithMeta[AIRecipeVersionPageDto],
    response_model_exclude_unset=True,
)
def list_account_ai_recipe_versions(
    request: Request,
    pagination: PaginationParams = Depends(get_pagination),
    scope: AccountScope = Depends(get_account_scope),
    _: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    filters: dict[str, object] = {}
    cursor = pagination.decode_cursor(
        scope=scope.account_id,
        resource_kind="ai-recipe.versions",
        filters=filters,
    )
    result = _service(request).list_account_ai_recipe_versions(
        scope.account_id,
        cursor=cursor,
        limit=pagination.limit,
    )
    return page_response(
        result,
        AIRecipeVersionPageDto,
        pagination=pagination,
        scope=scope.account_id,
        resource_kind="ai-recipe.versions",
        filters=filters,
    )


@router.post(
    "/versions",
    status_code=status.HTTP_201_CREATED,
    response_model=AISuccessEnvelopeWithMeta[AIRecipeVersionDto],
    response_model_exclude_unset=True,
)
def create_account_ai_recipe_version(
    payload: AccountAIRecipeVersionInput,
    request: Request,
    scope: AccountScope = Depends(get_account_scope),
    revision: ExpectedRevision = Depends(get_expected_revision),
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = _service(request).create_account_ai_recipe_version(
        scope.account_id,
        payload_dict(payload),
        expected_revision=revision.value,
        idempotency_key=require_idempotency_key(context),
        request_id=context.request_id,
        operation_id=context.operation_id,
    )
    return mutation_response(
        result,
        AIRecipeVersionDto,
        invalidations=(
            f"account:{scope.account_id}:ai-recipe",
            f"account:{scope.account_id}:readiness",
        ),
    )


@router.post(
    "/versions/{version}/validate",
    response_model=AISuccessEnvelopeWithMeta[AIRecipeValidationDto],
    response_model_exclude_unset=True,
)
def validate_account_ai_recipe_version(
    request: Request,
    version: PositiveVersionPath,
    scope: AccountScope = Depends(get_account_scope),
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = _service(request).validate_account_ai_recipe_version(
        scope.account_id,
        version,
        idempotency_key=require_idempotency_key(context),
        request_id=context.request_id,
        operation_id=context.operation_id,
    )
    return mutation_response(
        result,
        AIRecipeValidationDto,
        invalidations=(
            f"account:{scope.account_id}:ai-recipe",
            f"account:{scope.account_id}:readiness",
        ),
    )


@router.post(
    "/versions/{version}/activate",
    response_model=AISuccessEnvelopeWithMeta[AIRecipeDto],
    response_model_exclude_unset=True,
)
def activate_account_ai_recipe_version(
    request: Request,
    version: PositiveVersionPath,
    scope: AccountScope = Depends(get_account_scope),
    revision: ExpectedRevision = Depends(get_expected_revision),
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = _service(request).activate_account_ai_recipe_version(
        scope.account_id,
        version,
        expected_revision=revision.value,
        idempotency_key=require_idempotency_key(context),
        request_id=context.request_id,
        operation_id=context.operation_id,
    )
    return mutation_response(
        result,
        AIRecipeDto,
        invalidations=(
            f"account:{scope.account_id}:ai-recipe",
            f"account:{scope.account_id}:readiness",
            f"account:{scope.account_id}:workspace",
        ),
    )


def _service(request: Request) -> AccountAIRecipesServiceProtocol:
    return cast(
        AccountAIRecipesServiceProtocol,
        resolve_ai_service(request, "recipes"),
    )
