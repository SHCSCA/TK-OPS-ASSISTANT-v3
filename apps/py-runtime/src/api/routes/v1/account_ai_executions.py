from __future__ import annotations

from typing import Annotated, cast

from fastapi import APIRouter, Depends, Query, Request, Response, status

from api.dependencies.account_scope import get_account_scope
from api.dependencies.license_guard import require_active_license
from api.dependencies.pagination import PaginationParams, get_pagination
from api.dependencies.request_context import RequestContext, get_request_context
from api.dependencies.resource_id import StablePathId
from api.dependencies.revision import ExpectedRevision, get_expected_revision
from errors import DomainError, ErrorCode, FieldError
from schemas.v1.ai_executions import (
    AIExecutionCreateInput,
    AIExecutionPreflightInput,
    AIExecutionRetryInput,
    ExecutionStatus,
)
from schemas.v1.envelope import ok_response
from services.accounts.scope import AccountScope
from services.ai_execution_v1.gateway import AIExecutionGateway

router = APIRouter(
    prefix="/api/v1/accounts/{account_id}/ai-executions",
    tags=["v1-account-ai-executions"],
    dependencies=[Depends(require_active_license)],
)


@router.post("/preflight")
def preflight_ai_execution(
    payload: AIExecutionPreflightInput,
    request: Request,
    scope: AccountScope = Depends(get_account_scope),
    revision: ExpectedRevision = Depends(get_expected_revision),
    _: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = _gateway(request).preflight(
        scope.account_id,
        payload,
        expected_revision=revision.value,
    )
    return ok_response(result.model_dump(mode="json"))


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def create_ai_execution(
    payload: AIExecutionCreateInput,
    request: Request,
    scope: AccountScope = Depends(get_account_scope),
    revision: ExpectedRevision = Depends(get_expected_revision),
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result, meta = _gateway(request).create(
        scope.account_id,
        payload,
        expected_revision=revision.value,
        idempotency_key=_require_idempotency_key(context),
        request_id=context.request_id,
        operation_id=context.operation_id,
    )
    return ok_response(result.model_dump(mode="json"), meta=meta)


@router.get("")
def list_ai_executions(
    request: Request,
    execution_statuses: Annotated[
        list[ExecutionStatus] | None,
        Query(alias="status"),
    ] = None,
    capability_key: Annotated[
        str | None,
        Query(alias="capabilityKey", min_length=1, max_length=128),
    ] = None,
    pagination: PaginationParams = Depends(get_pagination),
    scope: AccountScope = Depends(get_account_scope),
    _: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    filters: dict[str, object] = {
        "status": sorted(set(execution_statuses or [])),
        "capabilityKey": capability_key,
    }
    cursor = pagination.decode_cursor(
        scope=scope.account_id,
        resource_kind="ai.executions",
        filters=filters,
    )
    result, next_position = _gateway(request).list_page(
        scope.account_id,
        limit=pagination.limit,
        cursor=cursor,
        statuses=(
            tuple(sorted(set(execution_statuses)))
            if execution_statuses
            else None
        ),
        capability_key=capability_key,
    )
    next_cursor = pagination.encode_cursor(
        next_position,
        scope=scope.account_id,
        resource_kind="ai.executions",
        filters=filters,
    )
    return ok_response(
        result.model_dump(mode="json"),
        meta={"nextCursor": next_cursor},
    )


@router.get("/{execution_id}")
def get_ai_execution(
    request: Request,
    execution_id: StablePathId,
    scope: AccountScope = Depends(get_account_scope),
    _: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = _gateway(request).get_detail(scope.account_id, execution_id)
    return ok_response(result.model_dump(mode="json"))


@router.post("/{execution_id}/cancel")
async def cancel_ai_execution(
    request: Request,
    execution_id: StablePathId,
    scope: AccountScope = Depends(get_account_scope),
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = await _gateway(request).cancel(
        scope.account_id,
        execution_id,
        idempotency_key=_require_idempotency_key(context),
    )
    return ok_response(
        result.model_dump(mode="json"),
        meta={
            "revision": result.revision,
            "invalidations": [
                f"account:{scope.account_id}:ai-executions",
                f"account:{scope.account_id}:tasks",
            ],
        },
    )


@router.post(
    "/{execution_id}/retry",
    status_code=status.HTTP_202_ACCEPTED,
)
async def retry_ai_execution(
    payload: AIExecutionRetryInput,
    request: Request,
    execution_id: StablePathId,
    scope: AccountScope = Depends(get_account_scope),
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    del payload
    result, meta = _gateway(request).retry_same_snapshot(
        scope.account_id,
        execution_id,
        idempotency_key=_require_idempotency_key(context),
        request_id=context.request_id,
        operation_id=context.operation_id,
    )
    return ok_response(result.model_dump(mode="json"), meta=meta)


@router.get("/{execution_id}/outputs/{output_id}")
def get_ai_execution_output(
    request: Request,
    response: Response,
    execution_id: StablePathId,
    output_id: StablePathId,
    scope: AccountScope = Depends(get_account_scope),
    _: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = _gateway(request).get_output(
        scope.account_id,
        execution_id,
        output_id,
    )
    response.headers["Cache-Control"] = "private, no-store"
    return ok_response(result.model_dump(mode="json"))


@router.get("/{execution_id}/evidence")
def get_ai_execution_evidence(
    request: Request,
    execution_id: StablePathId,
    scope: AccountScope = Depends(get_account_scope),
    _: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = _gateway(request).get_evidence(
        scope.account_id,
        execution_id,
    )
    return ok_response(result.model_dump(mode="json"))


def _gateway(request: Request) -> AIExecutionGateway:
    direct = getattr(request.app.state, "ai_execution_gateway", None)
    if direct is not None:
        return cast(AIExecutionGateway, direct)
    container = getattr(request.app.state, "runtime_container", None)
    bundle = getattr(getattr(container, "services", None), "ai_execution", None)
    gateway = getattr(bundle, "gateway", None)
    if gateway is not None:
        return cast(AIExecutionGateway, gateway)
    raise DomainError(
        ErrorCode.RUNTIME_NOT_READY,
        "AI 执行服务尚未就绪",
        status_code=503,
        loggable=True,
        log_context={"operation": "ai.execution.route.resolve_service"},
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


__all__ = ["router"]
