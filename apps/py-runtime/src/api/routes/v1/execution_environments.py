from __future__ import annotations

from typing import cast

from fastapi import APIRouter, Depends, Request, status

from api.dependencies.account_scope import get_account_scope
from api.dependencies.license_guard import require_active_license
from api.dependencies.request_context import RequestContext, get_request_context
from api.dependencies.resource_id import StablePathId
from api.dependencies.revision import ExpectedRevision, get_expected_revision
from errors import DomainError, ErrorCode, FieldError
from schemas.v1.envelope import ok_response
from schemas.v1.execution_environments import ExecutionEnvironmentCreateInput
from services.accounts.scope import AccountScope
from services.execution_environments import ExecutionEnvironmentService

router = APIRouter(
    prefix="/api/v1/accounts/{account_id}/execution-environments",
    tags=["v1-execution-environments"],
    dependencies=[Depends(require_active_license)],
)


@router.get("")
def list_execution_environments(
    request: Request,
    scope: AccountScope = Depends(get_account_scope),
    _: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = _service(request).list(scope.account_id)
    return ok_response(result.model_dump(mode="json"))


@router.get("/{environment_id}")
def get_execution_environment(
    environment_id: StablePathId,
    request: Request,
    scope: AccountScope = Depends(get_account_scope),
    _: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = _service(request).get(scope.account_id, environment_id)
    return ok_response(result.model_dump(mode="json"))


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def create_execution_environment(
    payload: ExecutionEnvironmentCreateInput,
    request: Request,
    scope: AccountScope = Depends(get_account_scope),
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = await _service(request).create(
        scope.account_id,
        payload,
        idempotency_key=_require_idempotency_key(context),
        request_id=context.request_id,
        operation_id=context.operation_id,
    )
    return ok_response(
        result.model_dump(mode="json"),
        meta={
            "invalidations": [
                f"account:{scope.account_id}:execution-environments",
                f"account:{scope.account_id}:tasks",
            ]
        },
    )


@router.post("/{environment_id}/start", status_code=status.HTTP_202_ACCEPTED)
async def start_execution_environment(
    environment_id: StablePathId,
    request: Request,
    scope: AccountScope = Depends(get_account_scope),
    context: RequestContext = Depends(get_request_context),
    revision: ExpectedRevision = Depends(get_expected_revision),
) -> dict[str, object]:
    result = await _service(request).start(
        scope.account_id,
        environment_id,
        expected_revision=revision.value,
        idempotency_key=_require_idempotency_key(context),
        request_id=context.request_id,
        operation_id=context.operation_id,
    )
    return _task_response(scope.account_id, result.model_dump(mode="json"))


@router.post("/{environment_id}/retry", status_code=status.HTTP_202_ACCEPTED)
async def retry_execution_environment(
    environment_id: StablePathId,
    request: Request,
    scope: AccountScope = Depends(get_account_scope),
    context: RequestContext = Depends(get_request_context),
    revision: ExpectedRevision = Depends(get_expected_revision),
) -> dict[str, object]:
    result = await _service(request).retry(
        scope.account_id,
        environment_id,
        expected_revision=revision.value,
        idempotency_key=_require_idempotency_key(context),
        request_id=context.request_id,
        operation_id=context.operation_id,
    )
    return _task_response(scope.account_id, result.model_dump(mode="json"))


@router.post("/{environment_id}/stop", status_code=status.HTTP_202_ACCEPTED)
async def stop_execution_environment(
    environment_id: StablePathId,
    request: Request,
    scope: AccountScope = Depends(get_account_scope),
    context: RequestContext = Depends(get_request_context),
    revision: ExpectedRevision = Depends(get_expected_revision),
) -> dict[str, object]:
    result = await _service(request).stop(
        scope.account_id,
        environment_id,
        expected_revision=revision.value,
        idempotency_key=_require_idempotency_key(context),
        request_id=context.request_id,
        operation_id=context.operation_id,
    )
    return _task_response(scope.account_id, result.model_dump(mode="json"))


@router.post("/{environment_id}/checks", status_code=status.HTTP_202_ACCEPTED)
async def check_execution_environment(
    environment_id: StablePathId,
    request: Request,
    scope: AccountScope = Depends(get_account_scope),
    context: RequestContext = Depends(get_request_context),
    revision: ExpectedRevision = Depends(get_expected_revision),
) -> dict[str, object]:
    result = await _service(request).check(
        scope.account_id,
        environment_id,
        expected_revision=revision.value,
        idempotency_key=_require_idempotency_key(context),
        request_id=context.request_id,
        operation_id=context.operation_id,
    )
    return _task_response(scope.account_id, result.model_dump(mode="json"))


@router.delete("/{environment_id}", status_code=status.HTTP_202_ACCEPTED)
async def delete_execution_environment(
    environment_id: StablePathId,
    request: Request,
    preserveUserFiles: bool = True,
    scope: AccountScope = Depends(get_account_scope),
    context: RequestContext = Depends(get_request_context),
    revision: ExpectedRevision = Depends(get_expected_revision),
) -> dict[str, object]:
    if not preserveUserFiles:
        raise DomainError(
            ErrorCode.REQUEST_VALIDATION_FAILED,
            "当前版本必须保留用户工作目录",
            status_code=422,
            field_errors=[
                FieldError(
                    field="preserveUserFiles",
                    code="must_be_true",
                    message="当前版本只支持保留用户文件",
                )
            ],
        )
    result = await _service(request).delete(
        scope.account_id,
        environment_id,
        expected_revision=revision.value,
        idempotency_key=_require_idempotency_key(context),
        request_id=context.request_id,
        operation_id=context.operation_id,
    )
    return _task_response(scope.account_id, result.model_dump(mode="json"))


def _service(request: Request) -> ExecutionEnvironmentService:
    container = getattr(request.app.state, "runtime_container", None)
    services = getattr(container, "services", None)
    service = getattr(services, "execution_environment", None)
    if service is None:
        raise DomainError(
            ErrorCode.RUNTIME_NOT_READY,
            "执行环境服务尚未就绪",
            status_code=503,
        )
    return cast(ExecutionEnvironmentService, service)


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


def _task_response(account_id: str, data: dict[str, object]) -> dict[str, object]:
    return ok_response(
        data,
        meta={
            "invalidations": [
                f"account:{account_id}:execution-environments",
                f"account:{account_id}:tasks",
                f"account:{account_id}:connection",
            ]
        },
    )
