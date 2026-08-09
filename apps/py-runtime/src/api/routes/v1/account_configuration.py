from __future__ import annotations

from typing import Annotated, cast

from fastapi import APIRouter, Depends, Path, Request, status

from api.dependencies.account_scope import get_account_scope
from api.dependencies.license_guard import require_active_license
from api.dependencies.request_context import (
    RequestContext,
    get_request_context,
)
from api.dependencies.revision import ExpectedRevision, get_expected_revision
from errors import DomainError, ErrorCode, FieldError
from schemas.v1.account_configuration import (
    BrandKitVersionInput,
    PositioningVersionInput,
    PublishDefaultsInput,
)
from schemas.v1.envelope import ok_response
from services.accounts.branding import AccountBrandingService
from services.accounts.positioning import AccountPositioningService
from services.accounts.results import AccountServiceResponse
from services.accounts.scope import AccountScope
from services.accounts.unit_of_work import MutationExecution

router = APIRouter(
    prefix="/api/v1/accounts/{account_id}",
    tags=["v1-account-configuration"],
    dependencies=[Depends(require_active_license)],
)


@router.get("/positioning")
def get_account_positioning(
    request: Request,
    scope: AccountScope = Depends(get_account_scope),
    _: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = _positioning(request).get(scope.account_id)
    return ok_response(result.model_dump(mode="json"))


@router.get("/positioning/versions/{version}")
def get_account_positioning_version(
    request: Request,
    version: Annotated[int, Path(ge=1)],
    scope: AccountScope = Depends(get_account_scope),
    _: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = _positioning(request).get_version(
        scope.account_id,
        version,
    )
    return ok_response(result.model_dump(mode="json"))


@router.post(
    "/positioning/versions",
    status_code=status.HTTP_201_CREATED,
)
def create_account_positioning_version(
    payload: PositioningVersionInput,
    request: Request,
    scope: AccountScope = Depends(get_account_scope),
    revision: ExpectedRevision = Depends(get_expected_revision),
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    execution = _positioning(request).create_version(
        scope.account_id,
        payload,
        expected_revision=revision.value,
        idempotency_key=_require_idempotency_key(context),
    )
    return _mutation_response(execution)


@router.post("/positioning/versions/{version}/activate")
def activate_account_positioning_version(
    request: Request,
    version: Annotated[int, Path(ge=1)],
    scope: AccountScope = Depends(get_account_scope),
    revision: ExpectedRevision = Depends(get_expected_revision),
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    execution = _positioning(request).activate_version(
        scope.account_id,
        version,
        expected_revision=revision.value,
        idempotency_key=_require_idempotency_key(context),
    )
    return _mutation_response(execution)


@router.get("/brand-kit")
def get_account_brand_kit(
    request: Request,
    scope: AccountScope = Depends(get_account_scope),
    _: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = _branding(request).get_brand_kit(scope.account_id)
    return ok_response(result.model_dump(mode="json"))


@router.put("/brand-kit")
def put_account_brand_kit(
    payload: BrandKitVersionInput,
    request: Request,
    scope: AccountScope = Depends(get_account_scope),
    revision: ExpectedRevision = Depends(get_expected_revision),
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = _branding(request).put_brand_kit(
        scope.account_id,
        payload,
        expected_revision=revision.value,
        idempotency_key=_require_idempotency_key(context),
    )
    return ok_response(result.data, meta=result.meta)


@router.get("/publish-defaults")
def get_account_publish_defaults(
    request: Request,
    scope: AccountScope = Depends(get_account_scope),
    _: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = _branding(request).get_publish_defaults(scope.account_id)
    return ok_response(result.model_dump(mode="json"))


@router.put("/publish-defaults")
def put_account_publish_defaults(
    payload: PublishDefaultsInput,
    request: Request,
    scope: AccountScope = Depends(get_account_scope),
    revision: ExpectedRevision = Depends(get_expected_revision),
    _: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = _branding(request).put_publish_defaults(
        scope.account_id,
        payload,
        expected_revision=revision.value,
    )
    return ok_response(result.data, meta=result.meta)


def _positioning(request: Request) -> AccountPositioningService:
    return cast(
        AccountPositioningService,
        _resolve_service(
            request,
            bundle_name="positioning",
            direct_name="account_positioning_service",
        ),
    )


def _branding(request: Request) -> AccountBrandingService:
    return cast(
        AccountBrandingService,
        _resolve_service(
            request,
            bundle_name="branding",
            direct_name="account_branding_service",
        ),
    )


def _resolve_service(
    request: Request,
    *,
    bundle_name: str,
    direct_name: str,
) -> object:
    direct = getattr(request.app.state, direct_name, None)
    if direct is not None:
        return direct
    state_bundle = getattr(request.app.state, "account_v1_service", None)
    service = getattr(state_bundle, bundle_name, None)
    if service is not None:
        return service
    container = getattr(request.app.state, "runtime_container", None)
    services = getattr(container, "services", None)
    for bundle_key in ("account_v1", "account_runtime"):
        bundle = getattr(services, bundle_key, None)
        service = getattr(bundle, bundle_name, None)
        if service is not None:
            return service
    service = getattr(services, bundle_name, None)
    if service is not None:
        return service
    raise DomainError(
        ErrorCode.RUNTIME_NOT_READY,
        "账号配置服务尚未就绪",
        status_code=503,
        loggable=True,
        log_context={
            "operation": "account.configuration.route.resolve_service",
            "service": bundle_name,
        },
    )


def _require_idempotency_key(context: RequestContext) -> str:
    if context.idempotency_key is not None:
        return context.idempotency_key
    raise DomainError(
        ErrorCode.REQUEST_VALIDATION_FAILED,
        "写操作必须提供 Idempotency-Key",
        status_code=422,
        field_errors=[
            FieldError(
                field="Idempotency-Key",
                code="required",
                message="必须提供幂等键",
            )
        ],
    )


def _mutation_response(
    execution: MutationExecution,
) -> dict[str, object]:
    result = AccountServiceResponse.from_mutation(execution)
    return ok_response(result.data, meta=result.meta)
