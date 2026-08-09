from __future__ import annotations

from typing import cast

from fastapi import APIRouter, Depends, Request, status

from api.dependencies.account_scope import get_account_scope
from api.dependencies.license_guard import require_active_license
from api.dependencies.request_context import RequestContext, get_request_context
from errors import DomainError, ErrorCode, FieldError
from schemas.v1.account_login_sessions import (
    LoginSessionCreateInput,
    LoginSessionProbeInput,
)
from schemas.v1.envelope import ok_response
from services.accounts.login_sessions import AccountLoginSessionService
from services.accounts.scope import AccountScope

router = APIRouter(
    prefix="/api/v1/accounts/{account_id}/connection",
    tags=["v1-account-login-sessions"],
    dependencies=[Depends(require_active_license)],
)


@router.post("/login-sessions", status_code=status.HTTP_202_ACCEPTED)
async def create_login_session(
    payload: LoginSessionCreateInput,
    request: Request,
    scope: AccountScope = Depends(get_account_scope),
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = await _service(request).create(
        scope.account_id,
        environment_id=payload.environmentId,
        idempotency_key=_require_idempotency_key(context),
        request_id=context.request_id,
        operation_id=context.operation_id,
    )
    return ok_response(
        result.model_dump(mode="json"),
        meta={"invalidations": _invalidations(scope.account_id)},
    )


@router.get("/login-sessions/{session_id}")
def get_login_session(
    session_id: str,
    request: Request,
    scope: AccountScope = Depends(get_account_scope),
    _: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = _service(request).get(scope.account_id, session_id)
    return ok_response(result.model_dump(mode="json"))


@router.post("/login-sessions/{session_id}/probe", status_code=status.HTTP_202_ACCEPTED)
async def probe_login_session(
    session_id: str,
    payload: LoginSessionProbeInput,
    request: Request,
    scope: AccountScope = Depends(get_account_scope),
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = await _service(request).probe(
        scope.account_id,
        session_id,
        expected_revision=payload.revision,
        idempotency_key=_require_idempotency_key(context),
        request_id=context.request_id,
        operation_id=context.operation_id,
    )
    return ok_response(
        result.model_dump(mode="json"),
        meta={"invalidations": _invalidations(scope.account_id)},
    )


@router.delete("/login-sessions/{session_id}")
async def cancel_login_session(
    session_id: str,
    request: Request,
    scope: AccountScope = Depends(get_account_scope),
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = await _service(request).cancel(
        scope.account_id,
        session_id,
        idempotency_key=_require_idempotency_key(context),
    )
    return ok_response(
        result.model_dump(mode="json"),
        meta={"invalidations": _invalidations(scope.account_id)},
    )


@router.delete("/session", status_code=status.HTTP_202_ACCEPTED)
async def logout_account_session(
    request: Request,
    scope: AccountScope = Depends(get_account_scope),
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = await _service(request).logout(
        scope.account_id,
        idempotency_key=_require_idempotency_key(context),
        request_id=context.request_id,
        operation_id=context.operation_id,
    )
    return ok_response(
        result.model_dump(mode="json"),
        meta={"invalidations": _invalidations(scope.account_id)},
    )


def _service(request: Request) -> AccountLoginSessionService:
    container = getattr(request.app.state, "runtime_container", None)
    services = getattr(container, "services", None)
    bundle = getattr(services, "account_v1", None)
    service = getattr(bundle, "login_sessions", None)
    if service is None:
        state_bundle = getattr(request.app.state, "account_v1_service", None)
        service = getattr(state_bundle, "login_sessions", None)
    if service is None:
        raise DomainError(
            ErrorCode.RUNTIME_NOT_READY,
            "账号登录服务尚未就绪",
            status_code=503,
        )
    return cast(AccountLoginSessionService, service)


def _require_idempotency_key(context: RequestContext) -> str:
    if context.idempotency_key:
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


def _invalidations(account_id: str) -> list[str]:
    return [
        f"account:{account_id}:connection",
        f"account:{account_id}:login-session",
        f"account:{account_id}:tasks",
        f"account:{account_id}:readiness",
    ]
