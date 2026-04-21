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

from accounts import router as accounts_router
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


def _build_app(tmp_path: Path) -> FastAPI:
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

    workspace_root = tmp_path / "account-workspace"
    workspace_root.mkdir()
    workspace = device_service.create_workspace(
        DeviceWorkspaceCreateInput(
            name="Account Workspace",
            root_path=str(workspace_root),
        )
    )
    account = account_service.create_account(
        AccountCreateInput(
            name="Ready Account",
            status="active",
            username="ready_account",
            authExpiresAt="2099-01-01T00:00:00Z",
        )
    )
    account_service.upsert_binding(
        account.id,
        AccountBindingUpsertInput(
            browserInstanceId=workspace.id,
            status="active",
            source="manual",
        ),
    )
    account_service.refresh_stats(account.id)

    app = FastAPI()
    app.state.account_service = account_service
    app.include_router(accounts_router)

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

    return app


def test_accounts_list_contract_returns_publish_readiness(tmp_path: Path) -> None:
    client = TestClient(_build_app(tmp_path))

    response = client.get("/api/accounts")

    assert response.status_code == 200
    accounts = _assert_ok(response.json())
    assert len(accounts) == 1
    account = accounts[0]
    assert set(account["publishReadiness"]) == {
        "canPublish",
        "status",
        "lastValidatedAt",
        "errorCode",
        "errorMessage",
        "suggestedAction",
        "binding",
    }
    assert account["publishReadiness"]["status"] == "ready"
    assert account["publishReadiness"]["binding"]["status"] == "active"


def test_account_refresh_stats_contract_returns_validation_result(tmp_path: Path) -> None:
    client = TestClient(_build_app(tmp_path))
    account_id = _assert_ok(client.get("/api/accounts").json())[0]["id"]

    response = client.post(f"/api/accounts/{account_id}/refresh-stats")

    assert response.status_code == 200
    result = _assert_ok(response.json())
    assert result["id"] == account_id
    assert result["providerStatus"] == "ready"
    assert result["publishReadiness"]["canPublish"] is True
    assert result["publishReadiness"]["lastValidatedAt"] is not None
