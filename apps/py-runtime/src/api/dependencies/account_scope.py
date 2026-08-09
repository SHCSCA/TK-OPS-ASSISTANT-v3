from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Depends, Request

from api.dependencies.request_context import RequestContext, get_request_context
from app.logging import pop_log_context, push_log_context
from common.identifiers import is_stable_id
from errors import DomainError, ErrorCode, FieldError
from services.accounts.scope import AccountScope
from services.accounts.types import AccountStatus
from services.accounts.unit_of_work import AccountUnitOfWork


async def get_account_scope(
    account_id: str,
    request: Request,
    context: RequestContext = Depends(get_request_context),
) -> AsyncIterator[AccountScope]:
    async for scope in _resolve_account_scope(
        account_id,
        request,
        context,
        allow_archived=False,
    ):
        yield scope


async def get_account_scope_allow_archived(
    account_id: str,
    request: Request,
    context: RequestContext = Depends(get_request_context),
) -> AsyncIterator[AccountScope]:
    async for scope in _resolve_account_scope(
        account_id,
        request,
        context,
        allow_archived=True,
    ):
        yield scope


async def _resolve_account_scope(
    account_id: str,
    request: Request,
    context: RequestContext,
    *,
    allow_archived: bool,
) -> AsyncIterator[AccountScope]:
    if not is_stable_id(account_id):
        raise DomainError(
            ErrorCode.REQUEST_VALIDATION_FAILED,
            "账号 ID 格式无效",
            status_code=422,
            field_errors=[
                FieldError(
                    field="account_id",
                    code="invalid_stable_id",
                    message="必须为 1 至 128 位受控标识",
                )
            ],
        )

    log_token = push_log_context(
        account_id=account_id,
        resource_type="account",
        resource_id=account_id,
    )
    try:
        with _resolve_unit_of_work(request).read() as transaction:
            account = transaction.accounts.get(
                transaction.session,
                account_id,
            )
            if account is None:
                raise DomainError(
                    ErrorCode.ACCOUNT_NOT_FOUND,
                    "账号不存在或已移除",
                    status_code=404,
                )
            status = AccountStatus(account.status)
            if status is AccountStatus.ARCHIVED and not allow_archived:
                raise DomainError(
                    ErrorCode.ACCOUNT_ARCHIVED,
                    "账号已归档，请先恢复后再进入工作区",
                    status_code=409,
                    meta={"accountId": account_id},
                )
            scope = AccountScope(
                account_id=account_id,
                account_revision=int(account.revision),
                status=status,
                request_id=context.request_id,
            )
        yield scope
    finally:
        pop_log_context(log_token)


def _resolve_unit_of_work(request: Request) -> AccountUnitOfWork:
    unit_of_work = getattr(request.app.state, "account_unit_of_work", None)
    if isinstance(unit_of_work, AccountUnitOfWork):
        return unit_of_work

    container = getattr(request.app.state, "runtime_container", None)
    services = getattr(container, "services", None)
    account_runtime = getattr(services, "account_v1", None)
    if account_runtime is None:
        account_runtime = getattr(services, "account_runtime", None)
    unit_of_work = getattr(account_runtime, "unit_of_work", None)
    if isinstance(unit_of_work, AccountUnitOfWork):
        return unit_of_work

    raise DomainError(
        ErrorCode.RUNTIME_NOT_READY,
        "账号工作区服务尚未就绪",
        status_code=503,
        loggable=True,
        log_context={
            "operation": "account_scope.resolve_service",
            "serviceMissing": True,
        },
    )
