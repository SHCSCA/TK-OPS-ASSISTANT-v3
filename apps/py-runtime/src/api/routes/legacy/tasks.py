from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from api.dependencies.license_guard import require_active_license
from api.dependencies.request_context import RequestContext, get_request_context
from api.routes.legacy.access import (
    record_legacy_api_use,
    require_legacy_access,
)
from errors import DomainError, ErrorCode
from schemas.envelope import ok_response
from services.tasks.coordinator import TaskCoordinator
from services.tasks.types import (
    RuntimeTaskRecord,
    TaskCompletionKind,
    TaskScope,
    TaskStatus,
)

router = APIRouter(
    prefix="/api/tasks",
    tags=["legacy-tasks"],
    dependencies=[
        Depends(require_legacy_access),
        Depends(require_active_license),
    ],
)


@router.get("")
async def list_tasks(
    request: Request,
    limit: int = Query(default=200, ge=1, le=200),
) -> dict[str, object]:
    record_legacy_api_use(
        request,
        replacement="/api/v1/system/tasks/{task_id}",
    )
    records = await _coordinator(request).list_system_tasks(limit=limit)
    active_records = [
        record
        for record in records
        if record.scope is TaskScope.SYSTEM
        and record.account_id is None
        and record.status
        in {
            TaskStatus.QUEUED,
            TaskStatus.RUNNING,
            TaskStatus.CANCELLING,
        }
    ]
    return ok_response([_legacy_task(record) for record in active_records])


@router.get("/{task_id}")
async def get_task(
    task_id: str,
    request: Request,
) -> dict[str, object]:
    record_legacy_api_use(
        request,
        replacement="/api/v1/system/tasks/{task_id}",
    )
    record = await _coordinator(request).get_system_task(task_id)
    return ok_response(_legacy_task(record))


@router.post("/{task_id}/cancel")
async def cancel_task(
    task_id: str,
    request: Request,
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    record_legacy_api_use(
        request,
        replacement="/api/v1/system/tasks/{task_id}/cancel",
    )
    record = await _coordinator(request).cancel_system_task(
        task_id,
        idempotency_key=(
            context.idempotency_key
            or f"legacy:cancel:{task_id}"
        ),
    )
    return ok_response(_legacy_task(record))


def _coordinator(request: Request) -> TaskCoordinator:
    service = getattr(request.app.state, "task_coordinator", None)
    if isinstance(service, TaskCoordinator):
        return service
    container = getattr(request.app.state, "runtime_container", None)
    service = getattr(
        getattr(container, "services", None),
        "task_coordinator",
        None,
    )
    if isinstance(service, TaskCoordinator):
        return service
    raise DomainError(
        ErrorCode.RUNTIME_NOT_READY,
        "持久任务服务尚未就绪",
        status_code=503,
        loggable=True,
        log_context={"service": "task_coordinator"},
    )


def _legacy_task(record: RuntimeTaskRecord) -> dict[str, object]:
    return {
        "id": record.id,
        "task_type": record.task_type,
        "project_id": None,
        "status": _legacy_status(record),
        "progress": round(record.progress * 100),
        "message": _legacy_message(record),
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }


def _legacy_status(record: RuntimeTaskRecord) -> str:
    if record.status is not TaskStatus.COMPLETED:
        return record.status.value
    if record.completion_kind is TaskCompletionKind.CANCELLED:
        return "cancelled"
    return "succeeded"


def _legacy_message(record: RuntimeTaskRecord) -> str:
    messages = {
        TaskStatus.QUEUED: "任务已排队",
        TaskStatus.RUNNING: "任务进行中",
        TaskStatus.CANCELLING: "任务正在取消",
        TaskStatus.COMPLETED: (
            "任务已取消"
            if record.completion_kind is TaskCompletionKind.CANCELLED
            else "任务已完成"
        ),
        TaskStatus.FAILED: "任务执行失败",
    }
    return messages[record.status]
