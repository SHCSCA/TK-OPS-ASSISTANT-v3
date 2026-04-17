from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from schemas.envelope import error_response, ok_response
from schemas.error_codes import ErrorCodes
from services.task_manager import task_manager

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("")
def list_tasks(
    type: str | None = Query(default=None),
    status: str | None = Query(default=None),
) -> dict[str, object]:
    statuses = (
        {item.strip() for item in status.split(",") if item.strip()}
        if status is not None
        else None
    )
    tasks = [
        task.to_dict()
        for task in task_manager.list_tasks(kind=type, statuses=statuses)
    ]
    return ok_response(tasks)


@router.get("/{task_id}")
def get_task(task_id: str) -> dict[str, object]:
    task = task_manager.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return ok_response(task.to_dict())


@router.post("/{task_id}/cancel")
def cancel_task(task_id: str):
    task = task_manager.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    if not task_manager.cancel(task_id):
        return JSONResponse(
            status_code=409,
            content=error_response("任务不可取消", error_code=ErrorCodes.TASK_CONFLICT),
        )
    return ok_response(
        {
            "task_id": task_id,
            "status": "cancelling",
            "message": "任务取消请求已提交",
        }
    )
