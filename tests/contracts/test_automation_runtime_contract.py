from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

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

from automation import router as automation_router
from common.http_errors import RuntimeHTTPException
from domain.models import Base
from persistence.engine import create_runtime_engine, create_session_factory
from repositories.automation_repository import AutomationRepository
from schemas.automation import AutomationTaskCreateInput
from schemas.envelope import error_response
from services.automation_service import AutomationService


class DeferredTaskManager:
    def __init__(self) -> None:
        self._tasks: dict[str, SimpleNamespace] = {}

    def submit(
        self,
        *,
        task_type: str,
        coro_factory,
        project_id: str | None = None,
        task_id: str | None = None,
    ) -> SimpleNamespace:
        del coro_factory
        if task_id is None:
            raise AssertionError("tests require explicit task_id")
        existing = self._tasks.get(task_id)
        if existing is not None and existing.status in {"queued", "running"}:
            raise ValueError("任务已存在")

        task = SimpleNamespace(
            id=task_id,
            task_type=task_type,
            project_id=project_id,
            status="queued",
            progress=0,
            message="任务已排队。",
            created_at="2026-04-21T00:00:00+00:00",
            updated_at="2026-04-21T00:00:00+00:00",
        )
        self._tasks[task_id] = task
        return task

    def list_active(self) -> list[SimpleNamespace]:
        return [
            task
            for task in self._tasks.values()
            if task.status in {"queued", "running"}
        ]


def _assert_ok(payload: dict[str, object]) -> object:
    assert payload["ok"] is True
    return payload["data"]


def _build_app(tmp_path: Path) -> FastAPI:
    engine = create_runtime_engine(tmp_path / "runtime.db")
    Base.metadata.create_all(engine)
    repository = AutomationRepository(session_factory=create_session_factory(engine))
    service = AutomationService(repository, task_manager=DeferredTaskManager())
    service.create_task(
        AutomationTaskCreateInput(
            name="同步发布状态",
            type="sync_status",
            config_json='{"projectId":"project-1","workspaceId":"workspace-1"}',
        )
    )

    app = FastAPI()
    app.state.automation_service = service
    app.include_router(automation_router)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(
        request: Request,
        exc: StarletteHTTPException,
    ):  # type: ignore[no-untyped-def]
        del request
        message = exc.detail if isinstance(exc.detail, str) else "请求失败"
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(
                message,
                error_code=getattr(exc, "error_code", None),
                details=getattr(exc, "details", None),
            ),
        )

    return app


def test_automation_list_contract_returns_runtime_lifecycle_fields(tmp_path: Path) -> None:
    client = TestClient(_build_app(tmp_path))

    response = client.get("/api/automation/tasks")

    assert response.status_code == 200
    tasks = _assert_ok(response.json())
    assert len(tasks) == 1
    task = tasks[0]
    assert set(task["source"]) == {
        "kind",
        "objectId",
        "projectId",
        "accountId",
        "workspaceId",
        "label",
    }
    assert set(task["queue"]) == {
        "status",
        "inQueue",
        "position",
        "activeRunId",
        "queuedAt",
    }
    assert set(task["latestResult"]) == {
        "runId",
        "status",
        "finishedAt",
        "summary",
        "errorCode",
        "errorMessage",
    }
    assert set(task["retry"]) == {
        "canRetry",
        "reason",
        "errorCode",
        "nextAction",
    }


def test_automation_trigger_contract_returns_queue_metadata(tmp_path: Path) -> None:
    client = TestClient(_build_app(tmp_path))
    task_id = _assert_ok(client.get("/api/automation/tasks").json())[0]["id"]

    response = client.post(f"/api/automation/tasks/{task_id}/trigger")

    assert response.status_code == 200
    result = _assert_ok(response.json())
    assert set(result) == {
        "task_id",
        "run_id",
        "status",
        "queueStatus",
        "queuePosition",
        "activeRunId",
        "nextAction",
        "message",
    }
    assert result["queueStatus"] == "queued"
    assert result["activeRunId"] == result["run_id"]


def test_automation_runs_contract_returns_result_and_retry_fields(tmp_path: Path) -> None:
    client = TestClient(_build_app(tmp_path))
    task_id = _assert_ok(client.get("/api/automation/tasks").json())[0]["id"]
    client.post(f"/api/automation/tasks/{task_id}/trigger")

    response = client.get(f"/api/automation/tasks/{task_id}/runs")

    assert response.status_code == 200
    runs = _assert_ok(response.json())
    assert len(runs) == 1
    assert set(runs[0]) == {
        "id",
        "task_id",
        "status",
        "started_at",
        "finished_at",
        "log_text",
        "resultSummary",
        "errorCode",
        "errorMessage",
        "retryable",
        "nextAction",
        "created_at",
    }


def test_automation_trigger_contract_returns_conflict_when_active_run_exists(
    tmp_path: Path,
) -> None:
    client = TestClient(_build_app(tmp_path))
    task_id = _assert_ok(client.get("/api/automation/tasks").json())[0]["id"]
    first = client.post(f"/api/automation/tasks/{task_id}/trigger")
    assert first.status_code == 200

    second = client.post(f"/api/automation/tasks/{task_id}/trigger")

    assert second.status_code == 409
    payload = second.json()
    assert payload["ok"] is False
    assert payload["error_code"] == "automation.task_already_running"


def test_automation_trigger_contract_returns_binding_required_error(tmp_path: Path) -> None:
    engine = create_runtime_engine(tmp_path / "runtime.db")
    Base.metadata.create_all(engine)
    repository = AutomationRepository(session_factory=create_session_factory(engine))
    service = AutomationService(repository, task_manager=DeferredTaskManager())
    task = service.create_task(
        AutomationTaskCreateInput(
            name="同步账号状态",
            type="sync_status",
            config_json='{"projectId":"project-1"}',
        )
    )

    app = FastAPI()
    app.state.automation_service = service
    app.include_router(automation_router)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(
        request: Request,
        exc: StarletteHTTPException,
    ):  # type: ignore[no-untyped-def]
        del request
        message = exc.detail if isinstance(exc.detail, str) else "请求失败"
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(
                message,
                error_code=getattr(exc, "error_code", None),
                details=getattr(exc, "details", None),
            ),
        )

    client = TestClient(app)

    response = client.post(f"/api/automation/tasks/{task.id}/trigger")

    assert response.status_code == 409
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error_code"] == "automation.binding_required"
