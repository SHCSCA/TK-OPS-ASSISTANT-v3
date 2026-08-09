from __future__ import annotations

from typing import cast

from fastapi import APIRouter, Depends, Query, Request

from api.dependencies.account_scope import (
    get_account_scope,
    get_account_scope_allow_archived,
)
from api.dependencies.license_guard import require_active_license
from api.dependencies.request_context import RequestContext, get_request_context
from api.dependencies.resource_id import StablePathId
from errors import DomainError, ErrorCode
from schemas.v1.envelope import ok_response
from schemas.v1.tasks import TaskDto, TaskListDto
from services.accounts.scope import AccountScope
from services.tasks.coordinator import TaskCoordinator

router = APIRouter(
    prefix="/api/v1",
    tags=["v1-tasks"],
    dependencies=[Depends(require_active_license)],
)


def _coordinator(request: Request) -> TaskCoordinator:
    coordinator = getattr(request.app.state, "task_coordinator", None)
    if coordinator is not None:
        return cast(TaskCoordinator, coordinator)
    container = getattr(request.app.state, "runtime_container", None)
    services = getattr(container, "services", None)
    coordinator = getattr(services, "task_coordinator", None)
    if coordinator is None:
        coordinator = getattr(services, "tasks", None)
    if coordinator is not None:
        return cast(TaskCoordinator, coordinator)
    raise DomainError(
        ErrorCode.RUNTIME_NOT_READY,
        "持久任务服务尚未就绪",
        status_code=503,
        loggable=True,
        log_context={"operation": "task.resolve_coordinator"},
    )


@router.get("/system/tasks/{task_id}")
async def get_system_task(
    task_id: StablePathId,
    request: Request,
    _: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    record = await _coordinator(request).get_system_task(task_id)
    return ok_response(TaskDto.from_record(record).model_dump(mode="json"))


@router.get("/system/tasks")
async def list_system_tasks(
    request: Request,
    limit: int = Query(default=50, ge=1, le=200),
    _: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    records = await _coordinator(request).list_system_tasks(limit=limit)
    result = TaskListDto(items=[TaskDto.from_record(item) for item in records])
    return ok_response(result.model_dump(mode="json"))


@router.post("/system/tasks/{task_id}/cancel")
async def cancel_system_task(
    task_id: StablePathId,
    request: Request,
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    record = await _coordinator(request).cancel_system_task(
        task_id,
        idempotency_key=context.idempotency_key or "",
    )
    return ok_response(
        TaskDto.from_record(record).model_dump(mode="json"),
        meta={
            "revision": record.revision,
            "invalidations": ["system:tasks"],
        },
    )


@router.get("/accounts/{account_id}/tasks/{task_id}")
async def get_account_task(
    task_id: StablePathId,
    request: Request,
    scope: AccountScope = Depends(get_account_scope_allow_archived),
    _: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    record = await _coordinator(request).get_account_task(
        scope.account_id,
        task_id,
    )
    return ok_response(TaskDto.from_record(record).model_dump(mode="json"))


@router.get("/accounts/{account_id}/tasks")
async def list_account_tasks(
    request: Request,
    limit: int = Query(default=50, ge=1, le=200),
    scope: AccountScope = Depends(get_account_scope_allow_archived),
    _: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    records = await _coordinator(request).list_account_tasks(
        scope.account_id,
        limit=limit,
    )
    result = TaskListDto(items=[TaskDto.from_record(item) for item in records])
    return ok_response(result.model_dump(mode="json"))


@router.post("/accounts/{account_id}/tasks/{task_id}/cancel")
async def cancel_account_task(
    task_id: StablePathId,
    request: Request,
    scope: AccountScope = Depends(get_account_scope),
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    record = await _coordinator(request).cancel_account_task(
        scope.account_id,
        task_id,
        idempotency_key=context.idempotency_key or "",
    )
    return ok_response(
        TaskDto.from_record(record).model_dump(mode="json"),
        meta={
            "revision": record.revision,
            "invalidations": [f"account:{scope.account_id}:tasks"],
        },
    )
