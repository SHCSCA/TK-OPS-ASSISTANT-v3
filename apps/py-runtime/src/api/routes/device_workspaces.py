from __future__ import annotations

from fastapi import APIRouter, Request, Response, status

from schemas.device_workspaces import DeviceWorkspaceCreateInput, DeviceWorkspaceUpdateInput
from schemas.envelope import ok_response
from services.device_workspace_service import DeviceWorkspaceService

router = APIRouter(prefix="/api/devices/workspaces", tags=["device-workspaces"])


def _svc(request: Request) -> DeviceWorkspaceService:
    return request.app.state.device_workspace_service  # type: ignore[no-any-return]


@router.get("/")
def list_workspaces(request: Request) -> dict[str, object]:
    items = _svc(request).list_workspaces()
    return ok_response([item.model_dump(mode="json") for item in items])


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_workspace(
    payload: DeviceWorkspaceCreateInput,
    request: Request,
) -> dict[str, object]:
    item = _svc(request).create_workspace(payload)
    return ok_response(item.model_dump(mode="json"))


@router.get("/{ws_id}")
def get_workspace(ws_id: str, request: Request) -> dict[str, object]:
    item = _svc(request).get_workspace(ws_id)
    return ok_response(item.model_dump(mode="json"))


@router.patch("/{ws_id}")
def update_workspace(
    ws_id: str,
    payload: DeviceWorkspaceUpdateInput,
    request: Request,
) -> dict[str, object]:
    item = _svc(request).update_workspace(ws_id, payload)
    return ok_response(item.model_dump(mode="json"))


@router.delete("/{ws_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workspace(ws_id: str, request: Request) -> Response:
    _svc(request).delete_workspace(ws_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{ws_id}/health-check")
def health_check(ws_id: str, request: Request) -> dict[str, object]:
    result = _svc(request).health_check(ws_id)
    return ok_response(result.model_dump(mode="json"))
