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

from common.time import utc_now
from domain.models import Base, Project, RenderTask, Timeline
from persistence.engine import create_runtime_engine, create_session_factory
from repositories.render_repository import RenderRepository
from repositories.timeline_repository import TimelineRepository
from schemas.envelope import error_response
from services.render_service import RenderService
from renders import router as renders_router


class _FakeMinimalRenderer:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail

    def render_minimal_mp4(
        self,
        *,
        output_path: Path,
        project_id: str | None,
        project_name: str | None,
        preset: str,
        format: str,
    ) -> SimpleNamespace:
        if self.fail:
            return SimpleNamespace(
                output_path=None,
                error_code="media.ffmpeg_unavailable",
                error_message="FFmpeg 未安装或未配置到可执行路径。",
            )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"contract-render-output")
        return SimpleNamespace(output_path=output_path, error_code=None, error_message=None)


def _assert_ok(payload: dict[str, object]) -> object:
    assert payload["ok"] is True
    return payload["data"]


def _build_app(tmp_path: Path, *, renderer: _FakeMinimalRenderer | None = None) -> FastAPI:
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
        session.add(
            Timeline(
                id="timeline-render",
                project_id="project-render",
                name="主时间线",
                status="draft",
                duration_seconds=12,
                tracks_json="[]",
                source="test",
                created_at=now.isoformat(),
                updated_at=now.isoformat(),
            )
        )
        session.commit()

    app = FastAPI()
    app.state.render_service = RenderService(
        RenderRepository(session_factory=session_factory),
        timeline_repository=TimelineRepository(session_factory=session_factory),
        export_root=tmp_path / "exports",
        renderer=renderer or _FakeMinimalRenderer(),
    )
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


def test_create_render_task_contract_writes_real_output_file(tmp_path: Path) -> None:
    client = TestClient(_build_app(tmp_path))

    response = client.post(
        "/api/renders/tasks",
        json={
            "project_id": "project-render",
            "project_name": "渲染项目",
            "timeline_id": "timeline-render",
            "preset": "1080p",
            "format": "mp4",
        },
    )

    assert response.status_code == 201
    task = _assert_ok(response.json())
    assert task["timeline_id"] == "timeline-render"
    assert task["status"] == "completed"
    assert task["progress"] == 100
    assert task["output"]["exists"] is True
    assert task["output"]["size_bytes"] == len(b"contract-render-output")
    assert task["output"]["path"].endswith(".mp4")
    assert Path(task["output"]["path"]).exists()
    assert task["failure"]["error_code"] is None


def test_create_render_task_contract_rejects_timeline_project_mismatch(tmp_path: Path) -> None:
    client = TestClient(_build_app(tmp_path))

    response = client.post(
        "/api/renders/tasks",
        json={
            "project_id": "project-other",
            "project_name": "错误项目",
            "timeline_id": "timeline-render",
            "preset": "1080p",
            "format": "mp4",
        },
    )

    assert response.status_code == 409
    error = response.json()
    assert error["ok"] is False
    assert error["error_code"] == "render.timeline_project_mismatch"
    assert error["error"] == "时间线不属于当前项目，请重新从 AI 剪辑工作台进入导出链路。"


def test_create_render_task_contract_exposes_renderer_failure(tmp_path: Path) -> None:
    client = TestClient(_build_app(tmp_path, renderer=_FakeMinimalRenderer(fail=True)))

    response = client.post("/api/renders/tasks", json={"project_id": "project-render"})

    assert response.status_code == 201
    task = _assert_ok(response.json())
    assert task["status"] == "failed"
    assert task["stage"]["code"] == "failed"
    assert task["failure"]["error_code"] == "media.ffmpeg_unavailable"
    assert task["failure"]["error_message"] == "FFmpeg 未安装或未配置到可执行路径。"
    assert task["failure"]["retryable"] is True
    assert task["failure"]["next_action"]["key"] == "retry-render"

    follow_up = client.get(f"/api/renders/tasks/{task['id']}")
    persisted = _assert_ok(follow_up.json())
    assert persisted["failure"]["error_code"] == "media.ffmpeg_unavailable"


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
        json={
            "status": "failed",
            "progress": 60,
            "error_code": "media.ffmpeg_failed",
            "error_message": "失败",
        },
    )
    assert response.status_code == 200

    response = client.post("/api/renders/tasks/render-task-1/retry")

    assert response.status_code == 200
    data = _assert_ok(response.json())
    assert data["status"] == "completed"
    assert data["progress"] == 100
    assert data["output"]["exists"] is True
    assert data["output_path"] is not None
    assert data["error_code"] is None
    assert data["error_message"] is None
    assert data["failure"]["error_code"] is None


def test_get_failed_render_task_contract_exposes_retry_action(tmp_path: Path) -> None:
    client = TestClient(_build_app(tmp_path))
    response = client.patch(
        "/api/renders/tasks/render-task-1",
        json={
            "status": "failed",
            "error_code": "media.ffmpeg_failed",
            "error_message": "FFmpeg 渲染失败，请检查媒体工具配置。",
        },
    )
    assert response.status_code == 200

    response = client.get("/api/renders/tasks/render-task-1")

    task = _assert_ok(response.json())
    assert task["stage"]["code"] == "failed"
    assert task["failure"]["error_code"] == "media.ffmpeg_failed"
    assert task["failure"]["next_action"]["key"] == "retry-render"


def test_get_completed_render_without_output_path_reports_failure(tmp_path: Path) -> None:
    client = TestClient(_build_app(tmp_path))
    response = client.patch(
        "/api/renders/tasks/render-task-1",
        json={"status": "completed", "progress": 100, "output_path": None},
    )
    assert response.status_code == 200

    response = client.get("/api/renders/tasks/render-task-1")

    task = _assert_ok(response.json())
    assert task["output"]["path"] is None
    assert task["failure"]["error_code"] == "render.output_not_found"


def test_get_completed_render_missing_output_file_reports_failure(tmp_path: Path) -> None:
    client = TestClient(_build_app(tmp_path))
    response = client.patch(
        "/api/renders/tasks/render-task-1",
        json={
            "status": "completed",
            "progress": 100,
            "output_path": str(tmp_path / "missing.mp4"),
        },
    )
    assert response.status_code == 200

    response = client.get("/api/renders/tasks/render-task-1")

    task = _assert_ok(response.json())
    assert task["output"]["exists"] is False
    assert task["failure"]["error_code"] == "render.output_not_found"


def test_retry_non_retryable_render_returns_structured_conflict(tmp_path: Path) -> None:
    client = TestClient(_build_app(tmp_path))

    response = client.post("/api/renders/tasks/render-task-1/retry")

    assert response.status_code == 409
    error = response.json()
    assert error["ok"] is False
    assert error["error_code"] == "render.task_not_retryable"
    assert error["error"] == "只有失败或已取消的任务可以重试。"


def test_cancel_running_render_contract_returns_cancelled_envelope(tmp_path: Path) -> None:
    client = TestClient(_build_app(tmp_path))
    response = client.patch(
        "/api/renders/tasks/render-task-1",
        json={"status": "rendering", "progress": 40},
    )
    assert response.status_code == 200

    response = client.post("/api/renders/tasks/render-task-1/cancel")

    assert response.status_code == 200
    data = _assert_ok(response.json())
    assert data["status"] == "cancelled"
    follow_up = client.get("/api/renders/tasks/render-task-1")
    task = _assert_ok(follow_up.json())
    assert task["failure"]["error_code"] == "render.task_cancelled"


def test_render_cancel_contract_returns_structured_conflict(tmp_path: Path) -> None:
    client = TestClient(_build_app(tmp_path))

    response = client.post("/api/renders/tasks/render-task-1/cancel")

    assert response.status_code == 409
    error = response.json()
    assert error["ok"] is False
    assert error["error_code"] == "render.task_not_cancellable"
    assert error["error"] == "只有排队中或渲染中的任务可以取消。"
