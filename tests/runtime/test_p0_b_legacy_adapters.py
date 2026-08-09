from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, Request, WebSocket

from api.routes.legacy.access import require_legacy_access
from api.routes.legacy.tasks import list_tasks
from app.route_registry import (
    LEGACY_COMPATIBILITY_HTTP_ROUTERS,
    LEGACY_UNMIGRATED_HTTP_ROUTERS,
    register_routes,
)
from app.websocket_security import (
    build_legacy_websocket_connection_authorizer,
)
from errors import DomainError, ErrorCode
from services.tasks.coordinator import TaskCoordinator
from services.tasks.types import (
    RuntimeTaskRecord,
    TaskScope,
    TaskStatus,
)


def test_production_legacy_http_requires_runtime_session() -> None:
    request = _http_request(
        mode="production",
        expected_host="127.0.0.1:43119",
        headers={
            "host": "127.0.0.1:43119",
            "origin": "tauri://localhost",
        },
    )

    with pytest.raises(DomainError) as captured:
        require_legacy_access(request)

    assert captured.value.error_code == ErrorCode.RUNTIME_SESSION_REQUIRED


def test_unknown_runtime_mode_legacy_http_fails_closed() -> None:
    request = _http_request(
        mode="release",
        expected_host="127.0.0.1:43119",
        headers={
            "host": "127.0.0.1:43119",
            "origin": "tauri://localhost",
        },
    )

    with pytest.raises(DomainError) as captured:
        require_legacy_access(request)

    assert captured.value.error_code == ErrorCode.RUNTIME_SESSION_REQUIRED


def test_production_route_registry_excludes_unmigrated_legacy_routes() -> None:
    app = _RouterRecorder()
    container = SimpleNamespace(
        config=SimpleNamespace(mode="production"),
        services=SimpleNamespace(bootstrap_v1=_ActiveLicenseService()),
        kernel=SimpleNamespace(
            websocket_manager=object(),
            policy=SimpleNamespace(
                websocket_subscribe_timeout_seconds=1.0,
                websocket_max_message_bytes=1024,
                legacy_websocket_max_message_bytes=1024,
            ),
        ),
    )

    register_routes(app, container)

    assert all(
        router in app.included_routers
        for router in LEGACY_COMPATIBILITY_HTTP_ROUTERS
    )
    assert all(
        router not in app.included_routers
        for router in LEGACY_UNMIGRATED_HTTP_ROUTERS
    )


def test_production_route_table_excludes_legacy_account_routes() -> None:
    app = FastAPI()
    container = SimpleNamespace(
        config=SimpleNamespace(mode="production"),
        services=SimpleNamespace(bootstrap_v1=_ActiveLicenseService()),
        kernel=SimpleNamespace(
            websocket_manager=object(),
            policy=SimpleNamespace(
                websocket_subscribe_timeout_seconds=1.0,
                websocket_max_message_bytes=1024,
                legacy_websocket_max_message_bytes=1024,
            ),
        ),
    )

    register_routes(app, container)

    account_routes = {
        (method, route.path)
        for route in app.routes
        if route.path.startswith("/api/accounts")
        for method in getattr(route, "methods", set())
    }
    assert account_routes == set()
    legacy_paths = {route.path for route in app.routes}
    assert "/api/dashboard" not in legacy_paths
    assert "/api/device-workspaces" not in legacy_paths
    assert "/api/publishing" not in legacy_paths


def test_development_legacy_http_keeps_controlled_origin_compatibility() -> None:
    request = _http_request(
        mode="development",
        expected_host="",
        headers={"origin": "http://127.0.0.1:5173"},
    )

    require_legacy_access(request)


def test_legacy_task_list_only_returns_active_system_tasks() -> None:
    task_service = _TaskService(
        [
            _task("task-system-running", TaskScope.SYSTEM, TaskStatus.RUNNING),
            _task("task-account-running", TaskScope.ACCOUNT, TaskStatus.RUNNING),
            _task("task-system-done", TaskScope.SYSTEM, TaskStatus.COMPLETED),
        ]
    )
    coordinator = TaskCoordinator(
        task_service=task_service,
        task_runner=SimpleNamespace(),
        recovery_service=SimpleNamespace(),
    )
    request = _http_request(
        mode="development",
        expected_host="",
        headers={},
    )
    request.app.state.task_coordinator = coordinator

    response = asyncio.run(list_tasks(request, limit=200))

    assert response["data"] == [
        {
            "id": "task-system-running",
            "task_type": "bootstrap.self_check",
            "project_id": None,
            "status": "running",
            "progress": 50,
            "message": "任务进行中",
            "created_at": "2026-07-26T10:00:00Z",
            "updated_at": "2026-07-26T10:01:00Z",
        }
    ]


def test_development_legacy_websocket_uses_no_session_subprotocol() -> None:
    app = FastAPI()
    app.state.runtime_config = SimpleNamespace(
        mode="development",
        expected_host="",
        allowed_origins=("http://127.0.0.1:5173",),
        runtime_session_token="",
    )
    websocket = _websocket(
        app,
        headers={"origin": "http://127.0.0.1:5173"},
    )
    authorize = build_legacy_websocket_connection_authorizer(
        _ActiveLicenseService()
    )

    access = asyncio.run(authorize(websocket))

    assert access.accepted_subprotocol is None
    assert access.session_id.startswith("ws_legacy_")


def test_production_legacy_websocket_requires_v1_session_subprotocol() -> None:
    app = FastAPI()
    app.state.runtime_config = SimpleNamespace(
        mode="production",
        expected_host="127.0.0.1:43119",
        allowed_origins=("tauri://localhost",),
        runtime_session_token="expected-session",
    )
    websocket = _websocket(
        app,
        headers={
            "host": "127.0.0.1:43119",
            "origin": "tauri://localhost",
        },
    )
    authorize = build_legacy_websocket_connection_authorizer(
        _ActiveLicenseService()
    )

    with pytest.raises(DomainError) as captured:
        asyncio.run(authorize(websocket))

    assert captured.value.error_code == ErrorCode.RUNTIME_SESSION_INVALID


class _RouterRecorder:
    def __init__(self) -> None:
        self.included_routers: list[object] = []

    def include_router(self, router: object) -> None:
        self.included_routers.append(router)


class _TaskService:
    def __init__(self, records: list[RuntimeTaskRecord]) -> None:
        self._records = records

    def list_system_tasks(self, *, limit: int) -> list[RuntimeTaskRecord]:
        return self._records[:limit]


class _ActiveLicenseService:
    def get_license_status(
        self,
        *,
        request_id: str,
        operation_id: str,
    ) -> SimpleNamespace:
        return SimpleNamespace(status="active")


def _task(
    task_id: str,
    scope: TaskScope,
    status: TaskStatus,
) -> RuntimeTaskRecord:
    return RuntimeTaskRecord(
        id=task_id,
        scope=scope,
        account_id="acc-1" if scope is TaskScope.ACCOUNT else None,
        task_type="bootstrap.self_check",
        status=status,
        completion_kind=None,
        failure_kind=None,
        progress=0.5,
        cancellable=True,
        timeout_at=None,
        attempt=1,
        retry_of_task_id=None,
        config_snapshot_json="{}",
        result_ref=None,
        error_code=None,
        error_log_id=None,
        revision=1,
        created_at="2026-07-26T10:00:00Z",
        started_at="2026-07-26T10:00:30Z",
        completed_at=(
            "2026-07-26T10:01:00Z"
            if status is TaskStatus.COMPLETED
            else None
        ),
        updated_at="2026-07-26T10:01:00Z",
        idempotency_key_hash="a" * 64,
        request_hash="b" * 64,
        handler_version=1,
    )


def _http_request(
    *,
    mode: str,
    expected_host: str,
    headers: dict[str, str],
) -> Request:
    app = FastAPI()
    app.state.runtime_config = SimpleNamespace(
        mode=mode,
        expected_host=expected_host,
        allowed_origins=(
            "tauri://localhost",
            "http://127.0.0.1:5173",
        ),
        runtime_session_token="expected-session",
    )
    return Request(
        {
            "type": "http",
            "app": app,
            "method": "GET",
            "scheme": "http",
            "path": "/api/tasks",
            "raw_path": b"/api/tasks",
            "query_string": b"",
            "headers": [
                (
                    name.lower().encode("ascii"),
                    value.encode("latin-1"),
                )
                for name, value in headers.items()
            ],
            "client": ("127.0.0.1", 43120),
            "server": ("127.0.0.1", 43119),
        }
    )


def _websocket(
    app: FastAPI,
    *,
    headers: dict[str, str],
) -> WebSocket:
    async def receive() -> dict[str, object]:
        return {"type": "websocket.disconnect"}

    async def send(_: dict[str, object]) -> None:
        return None

    return WebSocket(
        {
            "type": "websocket",
            "app": app,
            "path": "/api/ws",
            "raw_path": b"/api/ws",
            "root_path": "",
            "scheme": "ws",
            "query_string": b"",
            "headers": [
                (
                    name.lower().encode("ascii"),
                    value.encode("latin-1"),
                )
                for name, value in headers.items()
            ],
            "client": ("127.0.0.1", 43120),
            "server": ("127.0.0.1", 43119),
            "subprotocols": [],
        },
        receive,
        send,
    )
