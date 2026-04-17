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

from common.time import utc_now_iso
from domain.models import Base, Project, SubtitleTrack
from persistence.engine import create_runtime_engine, create_session_factory
from repositories.subtitle_repository import SubtitleRepository
from schemas.envelope import error_response
from services.subtitle_service import SubtitleService
from subtitles import router as subtitles_router


def _assert_ok(payload: dict[str, object]) -> object:
    assert payload["ok"] is True
    return payload["data"]


def _build_app(tmp_path: Path) -> FastAPI:
    engine = create_runtime_engine(tmp_path / "runtime.db")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    now = utc_now_iso()
    with session_factory() as session:
        session.add(
            Project(
                id="project-subtitle",
                name="字幕项目",
                description="",
                status="active",
                current_script_version=0,
                current_storyboard_version=0,
                created_at=now,
                updated_at=now,
                last_accessed_at=now,
            )
        )
        session.add(
            SubtitleTrack(
                id="subtitle-track-1",
                project_id="project-subtitle",
                timeline_id=None,
                source="script",
                language="zh-CN",
                style_json="""
                {
                  "preset": "creator-default",
                  "fontSize": 32,
                  "position": "bottom",
                  "textColor": "#FFFFFF",
                  "background": "rgba(0,0,0,0.62)"
                }
                """.strip(),
                segments_json="""
                [
                  {"segmentIndex": 0, "text": "第一句", "startMs": null, "endMs": null, "confidence": null, "locked": false},
                  {"segmentIndex": 1, "text": "第二句", "startMs": null, "endMs": null, "confidence": null, "locked": false}
                ]
                """.strip(),
                status="ready",
                created_at=now,
            )
        )
        session.commit()

    app = FastAPI()
    app.state.subtitle_service = SubtitleService(
        SubtitleRepository(session_factory=session_factory)
    )
    app.include_router(subtitles_router)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException):  # type: ignore[no-untyped-def]
        message = exc.detail if isinstance(exc.detail, str) else "请求失败"
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(message),
        )

    return app


def test_subtitle_align_contract_updates_segment_times(tmp_path: Path) -> None:
    client = TestClient(_build_app(tmp_path))

    response = client.post(
        "/api/subtitles/tracks/subtitle-track-1/align",
        json={
            "segments": [
                {
                    "segmentIndex": 0,
                    "text": "第一句",
                    "startMs": 0,
                    "endMs": 1800,
                    "confidence": 0.92,
                    "locked": True,
                },
                {
                    "segmentIndex": 1,
                    "text": "第二句",
                    "startMs": 1800,
                    "endMs": 3600,
                    "confidence": 0.88,
                    "locked": True,
                },
            ]
        },
    )

    assert response.status_code == 200
    track = _assert_ok(response.json())
    assert track["segments"][0]["startMs"] == 0
    assert track["segments"][1]["endMs"] == 3600


def test_subtitle_style_templates_contract_returns_builtin_templates(
    tmp_path: Path,
) -> None:
    client = TestClient(_build_app(tmp_path))

    response = client.get("/api/subtitles/style-templates")

    assert response.status_code == 200
    templates = _assert_ok(response.json())
    assert templates
    assert templates[0]["style"]["preset"]


def test_subtitle_export_contract_returns_real_content(tmp_path: Path) -> None:
    client = TestClient(_build_app(tmp_path))

    response = client.post(
        "/api/subtitles/tracks/subtitle-track-1/export",
        json={"format": "srt"},
    )

    assert response.status_code == 200
    export = _assert_ok(response.json())
    assert export["format"] == "srt"
    assert export["status"] == "ready"
    assert "第一句" in export["content"]
