from __future__ import annotations

from fastapi import APIRouter, Request, status

from schemas.accounts import AccountBindingUpsertInput
from schemas.device_workspaces import (
    BrowserInstanceCreateInput,
    DeviceWorkspaceCreateInput,
    DeviceWorkspaceUpdateInput,
)
from schemas.envelope import ok_response
from services.device_workspace_service import DeviceWorkspaceService

router = APIRouter(prefix="/api/devices", tags=["device-workspaces"])


def _svc(request: Request) -> DeviceWorkspaceService:
    return request.app.state.device_workspace_service  # type: ignore[no-any-return]


@router.get("/workspaces")
@router.get("/browser-instances")
def list_workspaces(request: Request) -> dict[str, object]:
    items = _svc(request).list_workspaces()
    return ok_response([item.model_dump(mode="json") for item in items])


@router.post("/workspaces", status_code=status.HTTP_201_CREATED)
@router.post("/browser-instances", status_code=status.HTTP_201_CREATED)
def create_workspace(
    payload: DeviceWorkspaceCreateInput,
    request: Request,
) -> dict[str, object]:
    item = _svc(request).create_workspace(payload)
    return ok_response(item.model_dump(mode="json"))


@router.get("/workspaces/{ws_id}")
@router.get("/browser-instances/{ws_id}")
def get_workspace(ws_id: str, request: Request) -> dict[str, object]:
    item = _svc(request).get_workspace(ws_id)
    return ok_response(item.model_dump(mode="json"))


@router.patch("/workspaces/{ws_id}")
@router.patch("/browser-instances/{ws_id}")
async def update_workspace(
    ws_id: str,
    payload: DeviceWorkspaceUpdateInput,
    request: Request,
) -> dict[str, object]:
    item = _svc(request).update_workspace(ws_id, payload)
    return ok_response(item.model_dump(mode="json"))


@router.delete("/workspaces/{ws_id}")
@router.delete("/browser-instances/{ws_id}")
def delete_workspace(ws_id: str, request: Request) -> dict[str, object]:
    _svc(request).delete_workspace(ws_id)
    return ok_response({"deleted": True})


@router.post("/workspaces/{ws_id}/health-check")
@router.post("/browser-instances/{ws_id}/health-check")
def health_check(ws_id: str, request: Request) -> dict[str, object]:
    result = _svc(request).health_check(ws_id)
    return ok_response(result.model_dump(mode="json"))


@router.get("/workspaces/{ws_id}/logs")
@router.get("/browser-instances/{ws_id}/logs")
def list_workspace_logs(
    ws_id: str,
    request: Request,
    since: str | None = None,
) -> dict[str, object]:
    logs = _svc(request).list_logs(ws_id, since=since)
    return ok_response([entry.model_dump(mode="json") for entry in logs])


@router.get("/workspaces/{ws_id}/browser-instances")
def list_browser_instances(ws_id: str, request: Request) -> dict[str, object]:
    items = _svc(request).list_browser_instances(ws_id)
    return ok_response([item.model_dump(mode="json") for item in items])


@router.post("/workspaces/{ws_id}/browser-instances", status_code=status.HTTP_201_CREATED)
def create_browser_instance(
    ws_id: str,
    payload: BrowserInstanceCreateInput,
    request: Request,
) -> dict[str, object]:
    item = _svc(request).create_browser_instance(
        ws_id,
        name=payload.name,
        profile_path=payload.profilePath,
    )
    return ok_response(item.model_dump(mode="json"))


@router.get("/workspaces/{ws_id}/browser-instances/{instance_id}")
def get_browser_instance(
    ws_id: str,
    instance_id: str,
    request: Request,
) -> dict[str, object]:
    item = _svc(request).get_browser_instance(ws_id, instance_id)
    return ok_response(item.model_dump(mode="json"))


@router.post("/workspaces/{ws_id}/browser-instances/{instance_id}/start")
def start_browser_instance(
    ws_id: str,
    instance_id: str,
    request: Request,
) -> dict[str, object]:
    result = _svc(request).start_browser_instance(ws_id, instance_id)
    return ok_response(result.model_dump(mode="json"))


@router.post("/workspaces/{ws_id}/browser-instances/{instance_id}/stop")
def stop_browser_instance(
    ws_id: str,
    instance_id: str,
    request: Request,
) -> dict[str, object]:
    result = _svc(request).stop_browser_instance(ws_id, instance_id)
    return ok_response(result.model_dump(mode="json"))


@router.post("/workspaces/{ws_id}/browser-instances/{instance_id}/health-check")
def health_check_browser_instance(
    ws_id: str,
    instance_id: str,
    request: Request,
) -> dict[str, object]:
    result = _svc(request).health_check_browser_instance(ws_id, instance_id)
    return ok_response(result.model_dump(mode="json"))


@router.get("/bindings")
def list_bindings(request: Request) -> dict[str, object]:
    bindings = _svc(request).list_bindings()
    return ok_response([binding.model_dump(mode="json") for binding in bindings])


@router.put("/bindings/{account_id}")
def upsert_binding(
    account_id: str,
    payload: AccountBindingUpsertInput,
    request: Request,
) -> dict[str, object]:
    binding = _svc(request).upsert_binding(account_id, payload)
    return ok_response(binding.model_dump(mode="json"))


@router.get("/bindings/{binding_id}")
def get_binding(binding_id: str, request: Request) -> dict[str, object]:
    binding = _svc(request).get_binding(binding_id)
    return ok_response(binding.model_dump(mode="json"))


@router.delete("/bindings/{binding_id}")
def delete_binding(binding_id: str, request: Request) -> dict[str, object]:
    result = _svc(request).delete_binding(binding_id)
    return ok_response(result)
