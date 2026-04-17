from __future__ import annotations

from fastapi import APIRouter, Request, status

from schemas.envelope import ok_response
from schemas.renders import (
    ExportProfileCreateInput,
    RenderTaskCreateInput,
    RenderTaskUpdateInput,
)
from services.render_service import RenderService

router = APIRouter(prefix="/api/renders", tags=["renders"])


def _svc(request: Request) -> RenderService:
    return request.app.state.render_service  # type: ignore[no-any-return]


@router.get("/profiles")
def list_profiles(request: Request) -> dict[str, object]:
    profiles = _svc(request).list_profiles()
    return ok_response([profile.model_dump(mode="json") for profile in profiles])


@router.get("/templates")
def list_templates(request: Request) -> dict[str, object]:
    templates = _svc(request).list_templates()
    return ok_response([template.model_dump(mode="json") for template in templates])


@router.post("/profiles", status_code=status.HTTP_201_CREATED)
def create_profile(payload: ExportProfileCreateInput, request: Request) -> dict[str, object]:
    profile = _svc(request).create_profile(payload)
    return ok_response(profile.model_dump(mode="json"))


@router.get("/resource-usage")
def fetch_resource_usage(request: Request) -> dict[str, object]:
    usage = _svc(request).fetch_resource_usage()
    return ok_response(usage.model_dump(mode="json"))


@router.get("/tasks")
def list_tasks(request: Request, status: str | None = None) -> dict[str, object]:
    tasks = _svc(request).list_tasks(status=status)
    return ok_response([task.model_dump(mode="json") for task in tasks])


@router.post("/tasks", status_code=status.HTTP_201_CREATED)
def create_task(payload: RenderTaskCreateInput, request: Request) -> dict[str, object]:
    task = _svc(request).create_task(payload)
    return ok_response(task.model_dump(mode="json"))


@router.get("/tasks/{task_id}")
def get_task(task_id: str, request: Request) -> dict[str, object]:
    task = _svc(request).get_task(task_id)
    return ok_response(task.model_dump(mode="json"))


@router.patch("/tasks/{task_id}")
def update_task(
    task_id: str,
    payload: RenderTaskUpdateInput,
    request: Request,
) -> dict[str, object]:
    task = _svc(request).update_task(task_id, payload)
    return ok_response(task.model_dump(mode="json"))


@router.delete("/tasks/{task_id}")
def delete_task(task_id: str, request: Request) -> dict[str, object]:
    _svc(request).delete_task(task_id)
    return ok_response({"deleted": True})


@router.post("/tasks/{task_id}/cancel")
def cancel_task(task_id: str, request: Request) -> dict[str, object]:
    result = _svc(request).cancel_task(task_id)
    return ok_response(result.model_dump(mode="json"))


@router.post("/tasks/{task_id}/retry")
def retry_task(task_id: str, request: Request) -> dict[str, object]:
    task = _svc(request).retry_task(task_id)
    return ok_response(task.model_dump(mode="json"))
