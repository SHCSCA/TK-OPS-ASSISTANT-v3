from __future__ import annotations

from fastapi import APIRouter, Request, Response, status

from schemas.envelope import ok_response
from schemas.renders import RenderTaskCreateInput, RenderTaskUpdateInput
from services.render_service import RenderService

router = APIRouter(prefix="/api/renders/tasks", tags=["renders"])


def _svc(request: Request) -> RenderService:
    return request.app.state.render_service  # type: ignore[no-any-return]


@router.get("/")
def list_tasks(request: Request, status: str | None = None) -> dict[str, object]:
    tasks = _svc(request).list_tasks(status=status)
    return ok_response([task.model_dump(mode="json") for task in tasks])


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_task(payload: RenderTaskCreateInput, request: Request) -> dict[str, object]:
    task = _svc(request).create_task(payload)
    return ok_response(task.model_dump(mode="json"))


@router.get("/{task_id}")
def get_task(task_id: str, request: Request) -> dict[str, object]:
    task = _svc(request).get_task(task_id)
    return ok_response(task.model_dump(mode="json"))


@router.patch("/{task_id}")
def update_task(
    task_id: str,
    payload: RenderTaskUpdateInput,
    request: Request,
) -> dict[str, object]:
    task = _svc(request).update_task(task_id, payload)
    return ok_response(task.model_dump(mode="json"))


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: str, request: Request) -> Response:
    _svc(request).delete_task(task_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{task_id}/cancel")
def cancel_task(task_id: str, request: Request) -> dict[str, object]:
    result = _svc(request).cancel_task(task_id)
    return ok_response(result.model_dump(mode="json"))
