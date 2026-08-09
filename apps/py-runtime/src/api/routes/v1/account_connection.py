from __future__ import annotations

from typing import cast

from fastapi import APIRouter, Depends, Request, status

from api.dependencies.account_scope import get_account_scope
from api.dependencies.license_guard import require_active_license
from api.dependencies.request_context import (
    RequestContext,
    get_request_context,
)
from api.dependencies.revision import ExpectedRevision, get_expected_revision
from errors import DomainError, ErrorCode, FieldError
from schemas.v1.accounts import ConnectionBindingInput, HealthCheckInput
from schemas.v1.envelope import ok_response
from services.accounts.connection import AccountConnectionService
from services.accounts.scope import AccountScope
from services.accounts.task_submission import AccountTaskSubmissionService

router = APIRouter(
    prefix="/api/v1/accounts/{account_id}/connection",
    tags=["v1-account-connection"],
    dependencies=[Depends(require_active_license)],
)


@router.get("")
def get_account_connection(
    request: Request,
    scope: AccountScope = Depends(get_account_scope),
    _: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = _connection(request).get(scope.account_id)
    return ok_response(result.model_dump(mode="json"))


@router.get("/candidates")
def list_account_connection_candidates(
    request: Request,
    scope: AccountScope = Depends(get_account_scope),
    _: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = _connection(request).list_candidates(scope.account_id)
    return ok_response(result.model_dump(mode="json"))


@router.put("/binding")
def bind_account_connection(
    payload: ConnectionBindingInput,
    request: Request,
    scope: AccountScope = Depends(get_account_scope),
    revision: ExpectedRevision = Depends(get_expected_revision),
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = _connection(request).bind(
        scope.account_id,
        payload,
        expected_revision=revision.value,
        idempotency_key=_require_idempotency_key(context),
    )
    return ok_response(result.data, meta=result.meta)


@router.delete("/binding")
def unbind_account_connection(
    request: Request,
    scope: AccountScope = Depends(get_account_scope),
    revision: ExpectedRevision = Depends(get_expected_revision),
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = _connection(request).unbind(
        scope.account_id,
        expected_revision=revision.value,
        idempotency_key=_require_idempotency_key(context),
    )
    return ok_response(result.data, meta=result.meta)


@router.post("/checks", status_code=status.HTTP_202_ACCEPTED)
async def submit_account_connection_checks(
    payload: HealthCheckInput,
    request: Request,
    scope: AccountScope = Depends(get_account_scope),
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    if payload.checks is not None and payload.checks != ["connection"]:
        raise DomainError(
            ErrorCode.REQUEST_VALIDATION_FAILED,
            "连接检查端点只接受 connection 检查项",
            status_code=422,
            field_errors=[
                FieldError(
                    field="checks",
                    code="connection_check_only",
                    message="请只提交 connection，或省略 checks",
                )
            ],
        )
    result = await _tasks(request).submit_connection_check(
        scope.account_id,
        idempotency_key=_require_idempotency_key(context),
        request_id=context.request_id,
        operation_id=context.operation_id,
    )
    return ok_response(
        result.model_dump(mode="json"),
        meta={
            "invalidations": [
                f"account:{scope.account_id}:tasks",
                f"account:{scope.account_id}:connection",
            ]
        },
    )


def _connection(request: Request) -> AccountConnectionService:
    return cast(
        AccountConnectionService,
        _resolve_service(
            request,
            bundle_name="connection",
            direct_name="account_connection_service",
        ),
    )


def _tasks(request: Request) -> AccountTaskSubmissionService:
    return cast(
        AccountTaskSubmissionService,
        _resolve_service(
            request,
            bundle_name="tasks",
            direct_name="account_task_submission_service",
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
        "账号连接服务尚未就绪",
        status_code=503,
        loggable=True,
        log_context={
            "operation": "account.connection.route.resolve_service",
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
