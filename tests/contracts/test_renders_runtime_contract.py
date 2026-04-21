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

from common.time import utc_now
from domain.models import Base, Project, RenderTask
from persistence.engine import create_runtime_engine, create_session_factory
from repositories.render_repository import RenderRepository
from schemas.envelope import error_response
from services.render_service import RenderService
from renders import router as renders_router


def _assert_ok(payload: dict[str, object]) -> object:
    assert payload["ok"] is True
    return payload["data"]


def _build_app(tmp_path: Path) -> FastAPI:
    engine = create_runtime_engine(tmp_path / "runtime.db")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    now = utc_now()
    output_file = tmp_path / "contract-output.mp4"
    output_file.write_bytes(b"render-output")
    with session_factory() as session:
        session.add(
            Project(
                id="project-render",
                name="渲染项目",
                description="",
                status="active",
                current_script_version=0,
                current_storyboard_version=0,
                created_at=now.isoformat(),
                updated_at=now.isoformat(),
                last_accessed_at=now.isoformat(),
            )
        )
        session.add(
            RenderTask(
                id="render-task-1",
                project_id="project-render",
                project_name="渲染项目",
                preset="1080p",
                format="mp4",
                status="completed",
                progress=100,
                output_path=str(output_file),
                error_message=None,
                started_at=now,
                finished_at=now,
            )
        )
        session.commit()

    app = FastAPI()
    app.state.render_service = RenderService(RenderRepository(session_factory=session_factory))
    app.include_router(renders_router)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException):  # type: ignore[no-untyped-def]
        message = exc.detail if isinstance(exc.detail, str) else "请求失败"
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(
                message,
                error_code=getattr(exc, "error_code", None),
            ),
        )

    return app


def test_render_templates_contract_returns_builtin_profiles(tmp_path: Path) -> None:
    client = TestClient(_build_app(tmp_path))

    response = client.get("/api/renders/templates")

    assert response.status_code == 200
    templates = _assert_ok(response.json())
    assert templates
    assert templates[0]["is_default"] is True


def test_render_task_contract_exposes_stage_output_and_failure(tmp_path: Path) -> None:
    client = TestClient(_build_app(tmp_path))

    response = client.get("/api/renders/tasks/render-task-1")

    assert response.status_code == 200
    task = _assert_ok(response.json())
    assert {"stage", "output", "failure"}.issubset(task)
    assert task["stage"]["code"] == "completed"
    assert task["output"]["exists"] is True
    assert task["failure"]["error_code"] is None


def test_render_resource_usage_contract_returns_real_disk_usage(tmp_path: Path) -> None:
    client = TestClient(_build_app(tmp_path))

    response = client.get("/api/renders/resource-usage")

    assert response.status_code == 200
    usage = _assert_ok(response.json())
    assert usage["disk"]["status"] == "ready"
    assert usage["disk"]["usagePct"] >= 0
    assert usage["cpu"]["status"] in {"ready", "unavailable"}
    assert usage["gpu"]["status"] == "unavailable"


def test_render_retry_contract_updates_task_status(tmp_path: Path) -> None:
    client = TestClient(_build_app(tmp_path))

    response = client.patch(
        "/api/renders/tasks/render-task-1",
        json={"status": "failed", "progress": 60, "error_message": "失败"},
    )
    assert response.status_code == 200

    response = client.post("/api/renders/tasks/render-task-1/retry")

    assert response.status_code == 200
    data = _assert_ok(response.json())
    assert data["status"] == "queued"
    assert data["progress"] == 0
    assert data["error_message"] is None


def test_render_cancel_contract_returns_structured_conflict(tmp_path: Path) -> None:
    client = TestClient(_build_app(tmp_path))

    response = client.post("/api/renders/tasks/render-task-1/cancel")

    assert response.status_code == 409
    error = response.json()
    assert error["error_code"] == "render.task_not_cancellable"
