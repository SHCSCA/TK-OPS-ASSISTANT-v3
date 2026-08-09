from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.dependencies.account_scope import (
    get_account_scope,
    get_account_scope_allow_archived,
)
from api.dependencies.license_guard import require_active_license
from api.dependencies.request_context import install_request_context_middleware
from api.routes.v1.tasks import router
from app.exception_handlers import install_exception_handlers
from services.accounts.scope import AccountScope
from services.accounts.types import AccountStatus
from services.tasks.types import (
    RuntimeTaskRecord,
    TaskCompletionKind,
    TaskScope,
    TaskStatus,
)


def _record(
    *,
    scope: TaskScope,
    account_id: str | None,
    status: TaskStatus = TaskStatus.RUNNING,
) -> RuntimeTaskRecord:
    return RuntimeTaskRecord(
        id="task_contract",
        scope=scope,
        account_id=account_id,
        task_type="test.operation",
        status=status,
        completion_kind=(
            TaskCompletionKind.CANCELLED
            if status is TaskStatus.COMPLETED
            else None
        ),
        failure_kind=None,
        progress=0.5,
        cancellable=True,
        timeout_at="2026-07-26T01:00:00Z",
        attempt=1,
        retry_of_task_id=None,
        config_snapshot_json="{}",
        result_ref=None,
        error_code=None,
        error_log_id=None,
        revision=2,
        created_at="2026-07-26T00:00:00Z",
        started_at="2026-07-26T00:00:01Z",
        completed_at=(
            "2026-07-26T00:00:02Z"
            if status is TaskStatus.COMPLETED
            else None
        ),
        updated_at="2026-07-26T00:00:01Z",
        idempotency_key_hash="a" * 64,
        request_hash="b" * 64,
        handler_version=1,
    )


class _Coordinator:
    async def list_system_tasks(self, *, limit: int) -> list[RuntimeTaskRecord]:
        assert limit == 20
        return [_record(scope=TaskScope.SYSTEM, account_id=None)]

    async def list_account_tasks(
        self,
        account_id: str,
        *,
        limit: int,
    ) -> list[RuntimeTaskRecord]:
        assert limit == 20
        return [_record(scope=TaskScope.ACCOUNT, account_id=account_id)]

    async def get_system_task(self, _task_id: str) -> RuntimeTaskRecord:
        return _record(scope=TaskScope.SYSTEM, account_id=None)

    async def get_account_task(
        self,
        account_id: str,
        _task_id: str,
    ) -> RuntimeTaskRecord:
        return _record(scope=TaskScope.ACCOUNT, account_id=account_id)

    async def cancel_system_task(
        self,
        _task_id: str,
        *,
        idempotency_key: str,
    ) -> RuntimeTaskRecord:
        assert idempotency_key == "idem_cancel"
        return _record(
            scope=TaskScope.SYSTEM,
            account_id=None,
            status=TaskStatus.COMPLETED,
        )

    async def cancel_account_task(
        self,
        account_id: str,
        _task_id: str,
        *,
        idempotency_key: str,
    ) -> RuntimeTaskRecord:
        assert idempotency_key == "idem_cancel"
        return _record(
            scope=TaskScope.ACCOUNT,
            account_id=account_id,
            status=TaskStatus.COMPLETED,
        )


def _account_scope(account_id: str) -> AccountScope:
    return AccountScope(
        account_id=account_id,
        account_revision=1,
        status=AccountStatus.READY,
        request_id="req_contract",
    )


def _build_app() -> FastAPI:
    app = FastAPI()
    app.state.task_coordinator = _Coordinator()
    app.dependency_overrides[require_active_license] = lambda: None
    app.dependency_overrides[get_account_scope] = _account_scope
    app.dependency_overrides[get_account_scope_allow_archived] = (
        _account_scope
    )
    install_request_context_middleware(app)
    install_exception_handlers(app)
    app.include_router(router)
    return app


def test_system_task_contract_uses_v1_envelope_and_camel_case() -> None:
    with TestClient(_build_app()) as client:
        response = client.get("/api/v1/system/tasks/task_contract")

    assert response.status_code == 200
    assert response.json()["data"] == {
        "taskId": "task_contract",
        "scope": "system",
        "accountId": None,
        "taskType": "test.operation",
        "status": "running",
        "cancellable": True,
        "createdAt": "2026-07-26T00:00:00Z",
        "completionKind": None,
        "failureKind": None,
        "progress": 0.5,
        "resultRef": None,
        "errorCode": None,
        "logId": None,
        "revision": 2,
    }


def test_task_list_contract_is_persistent_and_scope_isolated() -> None:
    with TestClient(_build_app()) as client:
        system_response = client.get("/api/v1/system/tasks?limit=20")
        account_response = client.get("/api/v1/accounts/acc_a/tasks?limit=20")

    assert system_response.status_code == 200
    assert system_response.json()["data"]["items"][0]["scope"] == "system"
    assert system_response.json()["data"]["items"][0]["accountId"] is None
    assert account_response.status_code == 200
    account_task = account_response.json()["data"]["items"][0]
    assert account_task["scope"] == "account"
    assert account_task["accountId"] == "acc_a"


def test_account_cancel_contract_returns_terminal_kind_and_invalidation() -> None:
    with TestClient(_build_app()) as client:
        response = client.post(
            "/api/v1/accounts/acc_a/tasks/task_contract/cancel",
            headers={"Idempotency-Key": "idem_cancel"},
        )

    payload = response.json()
    assert response.status_code == 200
    assert payload["data"]["status"] == "completed"
    assert payload["data"]["completionKind"] == "cancelled"
    assert payload["meta"] == {
        "revision": 2,
        "invalidations": ["account:acc_a:tasks"],
    }


def test_task_paths_publish_and_enforce_stable_id_contract() -> None:
    app = _build_app()
    schema = app.openapi()
    expected = {
        "type": "string",
        "minLength": 1,
        "maxLength": 128,
        "pattern": r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$",
    }
    targets = (
        ("/api/v1/system/tasks/{task_id}", "get"),
        ("/api/v1/system/tasks/{task_id}/cancel", "post"),
        ("/api/v1/accounts/{account_id}/tasks/{task_id}", "get"),
        ("/api/v1/accounts/{account_id}/tasks/{task_id}/cancel", "post"),
    )
    for path, method in targets:
        parameters = schema["paths"][path][method]["parameters"]
        parameter = next(item for item in parameters if item["name"] == "task_id")
        assert parameter["in"] == "path"
        assert parameter["required"] is True
        assert {
            key: parameter["schema"][key]
            for key in expected
        } == expected

    with TestClient(app) as client:
        response = client.get("/api/v1/system/tasks/invalid:task")

    assert response.status_code == 422
    assert response.json()["error_code"] == "REQUEST_VALIDATION_FAILED"
