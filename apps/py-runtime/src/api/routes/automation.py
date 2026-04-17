from __future__ import annotations

from fastapi import APIRouter, Request, status

from schemas.automation import AutomationTaskCreateInput, AutomationTaskUpdateInput
from schemas.envelope import ok_response
from services.automation_service import AutomationService

router = APIRouter(prefix="/api/automation/tasks", tags=["automation"])


def _svc(request: Request) -> AutomationService:
    return request.app.state.automation_service  # type: ignore[no-any-return]


@router.get("/")
def list_tasks(
    request: Request,
    status: str | None = None,
    type: str | None = None,
) -> dict[str, object]:
    tasks = _svc(request).list_tasks(status=status, type=type)
    return ok_response([task.model_dump(mode="json") for task in tasks])


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_task(payload: AutomationTaskCreateInput, request: Request) -> dict[str, object]:
    task = _svc(request).create_task(payload)
    return ok_response(task.model_dump(mode="json"))


@router.get("/{task_id}")
def get_task(task_id: str, request: Request) -> dict[str, object]:
    task = _svc(request).get_task(task_id)
    return ok_response(task.model_dump(mode="json"))


@router.patch("/{task_id}")
def update_task(
    task_id: str,
    payload: AutomationTaskUpdateInput,
    request: Request,
) -> dict[str, object]:
    task = _svc(request).update_task(task_id, payload)
    return ok_response(task.model_dump(mode="json"))


@router.post("/{task_id}/pause")
def pause_task(task_id: str, request: Request) -> dict[str, object]:
    task = _svc(request).pause_task(task_id)
    return ok_response(task.model_dump(mode="json"))


@router.post("/{task_id}/resume")
def resume_task(task_id: str, request: Request) -> dict[str, object]:
    task = _svc(request).resume_task(task_id)
    return ok_response(task.model_dump(mode="json"))


@router.delete("/{task_id}")
def delete_task(task_id: str, request: Request) -> dict[str, object]:
    _svc(request).delete_task(task_id)
    return ok_response({"deleted": True})


@router.post("/{task_id}/trigger")
def trigger_task(task_id: str, request: Request) -> dict[str, object]:
    result = _svc(request).trigger_task(task_id)
    return ok_response(result.model_dump(mode="json"))


@router.get("/{task_id}/runs")
def list_runs(
    task_id: str,
    request: Request,
    limit: int = 20,
) -> dict[str, object]:
    runs = _svc(request).list_runs(task_id, limit=limit)
    return ok_response([run.model_dump(mode="json") for run in runs])
