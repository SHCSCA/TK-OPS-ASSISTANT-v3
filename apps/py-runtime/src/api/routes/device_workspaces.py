from __future__ import annotations

from fastapi import APIRouter, Request, status

from schemas.device_workspaces import (
    BrowserInstanceCreateInput,
    DeviceWorkspaceCreateInput,
    DeviceWorkspaceUpdateInput,
    ExecutionBindingCreateInput,
)
from schemas.envelope import ok_response
from services.device_workspace_service import DeviceWorkspaceService

router = APIRouter(prefix="/api/devices", tags=["devices"])


def _svc(request: Request) -> DeviceWorkspaceService:
    return request.app.state.device_workspace_service  # type: ignore[no-any-return]


@router.get("/workspaces")
def list_workspaces(request: Request) -> dict[str, object]:
    items = _svc(request).list_workspaces()
    return ok_response([item.model_dump(mode="json") for item in items])


@router.post("/workspaces", status_code=status.HTTP_201_CREATED)
def create_workspace(
    payload: DeviceWorkspaceCreateInput,
    request: Request,
) -> dict[str, object]:
    item = _svc(request).create_workspace(payload)
    return ok_response(item.model_dump(mode="json"))


@router.get("/workspaces/{ws_id}")
def get_workspace(ws_id: str, request: Request) -> dict[str, object]:
    item = _svc(request).get_workspace(ws_id)
    return ok_response(item.model_dump(mode="json"))


@router.patch("/workspaces/{ws_id}")
def update_workspace(
    ws_id: str,
    payload: DeviceWorkspaceUpdateInput,
    request: Request,
) -> dict[str, object]:
    item = _svc(request).update_workspace(ws_id, payload)
    return ok_response(item.model_dump(mode="json"))


@router.delete("/workspaces/{ws_id}")
def delete_workspace(ws_id: str, request: Request) -> dict[str, object]:
    _svc(request).delete_workspace(ws_id)
    return ok_response({"deleted": True})


@router.post("/workspaces/{ws_id}/health-check")
def health_check(ws_id: str, request: Request) -> dict[str, object]:
    result = _svc(request).health_check(ws_id)
    return ok_response(result.model_dump(mode="json"))


@router.get("/browser-instances")
def list_browser_instances(
    request: Request,
    workspace_id: str | None = None,
) -> dict[str, object]:
    items = _svc(request).list_browser_instances(workspace_id=workspace_id)
    return ok_response([item.model_dump(mode="json") for item in items])


@router.post("/browser-instances", status_code=status.HTTP_201_CREATED)
def create_browser_instance(
    payload: BrowserInstanceCreateInput,
    request: Request,
) -> dict[str, object]:
    item = _svc(request).create_browser_instance(payload)
    return ok_response(item.model_dump(mode="json"))


@router.delete("/browser-instances/{instance_id}")
def delete_browser_instance(instance_id: str, request: Request) -> dict[str, object]:
    result = _svc(request).delete_browser_instance(instance_id)
    return ok_response(result)


@router.get("/bindings")
def list_bindings(
    request: Request,
    account_id: str | None = None,
    device_workspace_id: str | None = None,
) -> dict[str, object]:
    items = _svc(request).list_bindings(
        account_id=account_id,
        device_workspace_id=device_workspace_id,
    )
    return ok_response([item.model_dump(mode="json") for item in items])


@router.post("/bindings", status_code=status.HTTP_201_CREATED)
def create_binding(payload: ExecutionBindingCreateInput, request: Request) -> dict[str, object]:
    item = _svc(request).create_binding(payload)
    return ok_response(item.model_dump(mode="json"))


@router.delete("/bindings/{binding_id}")
def delete_binding(binding_id: str, request: Request) -> dict[str, object]:
    result = _svc(request).delete_binding(binding_id)
    return ok_response(result)
