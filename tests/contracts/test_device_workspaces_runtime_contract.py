from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from starlette.exceptions import HTTPException as StarletteHTTPException

SRC_DIR = Path(__file__).resolve().parents[2] / "apps" / "py-runtime" / "src"
ROUTES_DIR = SRC_DIR / "api" / "routes"
if str(ROUTES_DIR) not in sys.path:
    sys.path.insert(0, str(ROUTES_DIR))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from device_workspaces import router as device_router
from domain.models import Base
from persistence.engine import create_runtime_engine, create_session_factory
from repositories.account_repository import AccountRepository
from repositories.device_workspace_repository import DeviceWorkspaceRepository
from schemas.accounts import AccountBindingUpsertInput, AccountCreateInput
from schemas.device_workspaces import DeviceWorkspaceCreateInput
from schemas.envelope import error_response
from services.account_service import AccountService
from services.device_workspace_service import DeviceWorkspaceService


def _assert_ok(payload: dict[str, object]) -> object:
    assert payload["ok"] is True
    return payload["data"]


def _build_app(tmp_path: Path) -> tuple[FastAPI, str, str]:
    engine = create_runtime_engine(tmp_path / "runtime.db")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    account_repository = AccountRepository(session_factory=session_factory)
    device_repository = DeviceWorkspaceRepository(session_factory=session_factory)
    account_service = AccountService(
        account_repository,
        binding_repository=device_repository,
    )
    device_service = DeviceWorkspaceService(device_repository)

    workspace_root = tmp_path / "device-workspace"
    workspace_root.mkdir()
    workspace = device_service.create_workspace(
        DeviceWorkspaceCreateInput(
            name="Runtime Workspace",
            root_path=str(workspace_root),
        )
    )
    account = account_service.create_account(
        AccountCreateInput(
            name="Device Bound Account",
            status="active",
            username="bound_account",
        )
    )
    account_service.upsert_binding(
        account.id,
        AccountBindingUpsertInput(
            browserInstanceId=workspace.id,
            status="active",
            source="manual",
            metadataJson=None,
        ),
    )

    app = FastAPI()
    app.state.device_workspace_service = device_service
    app.include_router(device_router)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(
        request: Request,
        exc: StarletteHTTPException,
    ):  # type: ignore[no-untyped-def]
        del request
        message = exc.detail if isinstance(exc.detail, str) else "请求失败"
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(message),
        )

    return app, workspace.id, account.id


def test_device_workspaces_list_contract_returns_runtime_summaries(
    tmp_path: Path,
) -> None:
    app, workspace_id, account_id = _build_app(tmp_path)
    client = TestClient(app)

    response = client.get("/api/devices/workspaces")

    assert response.status_code == 200
    workspaces = _assert_ok(response.json())
    assert len(workspaces) == 1
    workspace = workspaces[0]
    assert workspace["id"] == workspace_id
    assert set(workspace["environmentStatus"]) == {
        "status",
        "rootPathExists",
        "isDirectory",
        "browserInstanceCount",
        "runningBrowserInstanceCount",
        "errorCode",
        "errorMessage",
        "nextAction",
    }
    assert workspace["environmentStatus"]["status"] == "ready_without_browser"
    assert workspace["bindingSummary"]["totalBindings"] == 1
    assert workspace["bindingSummary"]["accountIds"] == [account_id]
    assert workspace["healthSummary"]["status"] == "unknown"


def test_device_workspace_health_check_contract_returns_actionable_result(
    tmp_path: Path,
) -> None:
    app, workspace_id, _ = _build_app(tmp_path)
    client = TestClient(app)

    response = client.post(f"/api/devices/workspaces/{workspace_id}/health-check")

    assert response.status_code == 200
    result = _assert_ok(response.json())
    assert result["workspace_id"] == workspace_id
    assert result["status"] == "ready"
    assert result["environmentStatus"]["status"] == "ready_without_browser"
    assert result["bindingSummary"]["activeBindings"] == 1
