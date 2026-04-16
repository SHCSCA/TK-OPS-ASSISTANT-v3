from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from schemas.envelope import error_response, ok_response
from services.task_manager import task_manager

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("")
def list_tasks() -> dict[str, object]:
    tasks = [task.to_dict() for task in task_manager.list_active()]
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
            content=error_response("任务不可取消"),
        )
    return ok_response(
        {
            "task_id": task_id,
            "status": "cancelling",
            "message": "任务取消请求已提交",
        }
    )
