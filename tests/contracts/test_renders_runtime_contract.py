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
                status="rendering",
                progress=35,
                output_path=None,
                error_message=None,
                started_at=now,
                finished_at=None,
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
            content=error_response(message),
        )

    return app


def test_render_templates_contract_returns_builtin_profiles(tmp_path: Path) -> None:
    client = TestClient(_build_app(tmp_path))

    response = client.get("/api/renders/templates")

    assert response.status_code == 200
    templates = _assert_ok(response.json())
    assert templates
    assert templates[0]["is_default"] is True


def test_render_resource_usage_contract_returns_real_disk_usage(tmp_path: Path) -> None:
    client = TestClient(_build_app(tmp_path))

    response = client.get("/api/renders/resource-usage")

    assert response.status_code == 200
    usage = _assert_ok(response.json())
    assert usage["disk"]["status"] == "ready"
    assert usage["disk"]["usagePct"] >= 0
    assert usage["cpu"]["status"] in {"ready", "unavailable"}
    assert usage["gpu"]["status"] == "unavailable"
