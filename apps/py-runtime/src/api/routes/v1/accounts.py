from __future__ import annotations

from typing import Annotated, Literal, cast

from fastapi import APIRouter, Depends, Query, Request, status

from api.dependencies.account_scope import (
    get_account_scope,
    get_account_scope_allow_archived,
)
from api.dependencies.license_guard import require_active_license
from api.dependencies.pagination import PaginationParams, get_pagination
from api.dependencies.request_context import (
    RequestContext,
    get_request_context,
)
from api.dependencies.revision import ExpectedRevision, get_expected_revision
from errors import DomainError, ErrorCode, FieldError
from schemas.v1.account_common import AccountStatusValue
from schemas.v1.accounts import (
    AccountCopyInput,
    AccountCreateInput,
    AccountPatchInput,
    ArchiveInput,
    CompleteWizardInput,
    HealthCheckInput,
)
from schemas.v1.envelope import ok_response
from services.accounts.commands import AccountCommandService
from services.accounts.copy_config import AccountConfigCopyService
from services.accounts.read_model import AccountReadModel
from services.accounts.results import AccountServiceResponse
from services.accounts.scope import AccountScope
from services.accounts.task_submission import AccountTaskSubmissionService
from services.accounts.workspace_activation import (
    AccountWorkspaceActivationService,
)

router = APIRouter(
    prefix="/api/v1/accounts",
    tags=["v1-accounts"],
    dependencies=[Depends(require_active_license)],
)

WorkspaceInclude = Literal["readiness", "taskSummary", "navigation"]


@router.get("")
def list_accounts(
    request: Request,
    q: Annotated[str | None, Query(max_length=128)] = None,
    account_status: Annotated[
        AccountStatusValue | None,
        Query(alias="status"),
    ] = None,
    pagination: PaginationParams = Depends(get_pagination),
    _: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    normalized_query = _normalize_account_query(q)
    filters: dict[str, object] = {
        "query": normalized_query,
        "status": account_status,
    }
    cursor = pagination.decode_cursor(
        scope="system",
        resource_kind="accounts.list",
        filters=filters,
    )
    result, next_position = _read_model(request).list_accounts(
        limit=pagination.limit,
        cursor=cursor,
        query=normalized_query,
        status=account_status,
    )
    next_cursor = pagination.encode_cursor(
        next_position,
        scope="system",
        resource_kind="accounts.list",
        filters=filters,
    )
    return ok_response(
        result.model_dump(mode="json"),
        meta={"nextCursor": next_cursor},
    )


@router.post("", status_code=status.HTTP_201_CREATED)
def create_account(
    payload: AccountCreateInput,
    request: Request,
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = _commands(request).create(
        payload,
        idempotency_key=_require_idempotency_key(context),
    )
    return _service_response(result)


@router.get("/{account_id}")
def get_account(
    request: Request,
    scope: AccountScope = Depends(get_account_scope_allow_archived),
    _: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = _read_model(request).get_account(
        scope.account_id,
        allow_archived=True,
    )
    return ok_response(result.model_dump(mode="json"))


@router.patch("/{account_id}")
def patch_account(
    payload: AccountPatchInput,
    request: Request,
    scope: AccountScope = Depends(get_account_scope),
    revision: ExpectedRevision = Depends(get_expected_revision),
    _: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = _commands(request).patch(
        scope.account_id,
        payload,
        expected_revision=revision.value,
    )
    return _service_response(result)


@router.get("/{account_id}/workspace-context")
def get_workspace_context(
    request: Request,
    include: Annotated[list[WorkspaceInclude] | None, Query()] = None,
    scope: AccountScope = Depends(get_account_scope),
    _: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    # P0-C 工作区上下文保持固定完整形状，include 仅作为前向兼容提示。
    del include
    result = _read_model(request).get_workspace_context(scope.account_id)
    return ok_response(result.model_dump(mode="json"))


@router.post("/{account_id}/workspace-activation")
def activate_account_workspace(
    request: Request,
    scope: AccountScope = Depends(get_account_scope),
    revision: ExpectedRevision = Depends(get_expected_revision),
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = _workspace_activation(request).activate(
        scope.account_id,
        expected_revision=revision.value,
        idempotency_key=_require_idempotency_key(context),
    )
    return _service_response(result)


@router.post("/{account_id}/complete-wizard")
def complete_account_wizard(
    payload: CompleteWizardInput,
    request: Request,
    scope: AccountScope = Depends(get_account_scope),
    revision: ExpectedRevision = Depends(get_expected_revision),
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = _commands(request).complete_wizard(
        scope.account_id,
        payload,
        expected_revision=revision.value,
        idempotency_key=_require_idempotency_key(context),
    )
    return _service_response(result)


@router.post("/{account_id}/copy-config")
def copy_account_config(
    payload: AccountCopyInput,
    request: Request,
    scope: AccountScope = Depends(get_account_scope),
    revision: ExpectedRevision = Depends(get_expected_revision),
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    execution = _copy_config(request).copy(
        scope.account_id,
        payload,
        expected_revision=revision.value,
        idempotency_key=_require_idempotency_key(context),
        operation_id=context.operation_id,
    )
    return _service_response(AccountServiceResponse.from_mutation(execution))


@router.post(
    "/{account_id}/archive",
    status_code=status.HTTP_202_ACCEPTED,
)
async def archive_account(
    payload: ArchiveInput,
    request: Request,
    scope: AccountScope = Depends(get_account_scope_allow_archived),
    revision: ExpectedRevision = Depends(get_expected_revision),
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = await _tasks(request).submit_archive_cleanup(
        scope.account_id,
        expected_revision=revision.value,
        reason_provided=payload.reason is not None,
        idempotency_key=_require_idempotency_key(context),
        request_id=context.request_id,
        operation_id=context.operation_id,
    )
    return ok_response(
        result.model_dump(mode="json"),
        meta={
            "invalidations": [
                "accounts:list",
                f"account:{scope.account_id}:tasks",
            ]
        },
    )


@router.post(
    "/{account_id}/restore",
    status_code=status.HTTP_202_ACCEPTED,
)
async def restore_account(
    payload: HealthCheckInput,
    request: Request,
    scope: AccountScope = Depends(get_account_scope_allow_archived),
    revision: ExpectedRevision = Depends(get_expected_revision),
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = await _tasks(request).submit_restore(
        scope.account_id,
        checks=payload.checks,
        expected_revision=revision.value,
        idempotency_key=_require_idempotency_key(context),
        request_id=context.request_id,
        operation_id=context.operation_id,
    )
    return ok_response(
        result.model_dump(mode="json"),
        meta={
            "invalidations": [
                "accounts:list",
                f"account:{scope.account_id}:tasks",
            ]
        },
    )


@router.get("/{account_id}/health")
def get_account_health(
    request: Request,
    scope: AccountScope = Depends(get_account_scope_allow_archived),
    _: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = _read_model(request).get_account(
        scope.account_id,
        allow_archived=True,
    )
    return ok_response(result.readiness.model_dump(mode="json"))


@router.post(
    "/{account_id}/health-checks",
    status_code=status.HTTP_202_ACCEPTED,
)
async def submit_account_health_checks(
    payload: HealthCheckInput,
    request: Request,
    scope: AccountScope = Depends(get_account_scope),
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = await _tasks(request).submit_health_checks(
        scope.account_id,
        checks=payload.checks,
        idempotency_key=_require_idempotency_key(context),
        request_id=context.request_id,
        operation_id=context.operation_id,
    )
    return ok_response(
        result.model_dump(mode="json"),
        meta={
            "invalidations": [
                f"account:{scope.account_id}:tasks",
                f"account:{scope.account_id}:readiness",
            ]
        },
    )


def _read_model(request: Request) -> AccountReadModel:
    return cast(
        AccountReadModel,
        _resolve_service(
            request,
            bundle_name="read_model",
            direct_names=("account_read_model",),
        ),
    )


def _commands(request: Request) -> AccountCommandService:
    return cast(
        AccountCommandService,
        _resolve_service(
            request,
            bundle_name="commands",
            direct_names=("account_command_service",),
        ),
    )


def _workspace_activation(
    request: Request,
) -> AccountWorkspaceActivationService:
    return cast(
        AccountWorkspaceActivationService,
        _resolve_service(
            request,
            bundle_name="workspace_activation",
            direct_names=("account_workspace_activation_service",),
        ),
    )


def _copy_config(request: Request) -> AccountConfigCopyService:
    return cast(
        AccountConfigCopyService,
        _resolve_service(
            request,
            bundle_name="copy_config",
            direct_names=("account_copy_service",),
        ),
    )


def _tasks(request: Request) -> AccountTaskSubmissionService:
    return cast(
        AccountTaskSubmissionService,
        _resolve_service(
            request,
            bundle_name="tasks",
            direct_names=("account_task_submission_service",),
        ),
    )


def _resolve_service(
    request: Request,
    *,
    bundle_name: str,
    direct_names: tuple[str, ...],
) -> object:
    for direct_name in direct_names:
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
        "账号工作区服务尚未就绪",
        status_code=503,
        loggable=True,
        log_context={
            "operation": "account.route.resolve_service",
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


def _normalize_account_query(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _service_response(
    result: AccountServiceResponse,
) -> dict[str, object]:
    return ok_response(result.data, meta=result.meta)
