from __future__ import annotations

import json
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
from domain.models import Base, Project, SubtitleTrack, VoiceTrack
from persistence.engine import create_runtime_engine, create_session_factory
from repositories.subtitle_repository import SubtitleRepository
from repositories.voice_repository import VoiceRepository
from schemas.envelope import error_response
from services.subtitle_service import SubtitleService
from subtitles import router as subtitles_router


def _assert_ok(payload: dict[str, object]) -> object:
    assert payload["ok"] is True
    return payload["data"]


def _assert_subtitle_track_contract(track: dict[str, object]) -> None:
    assert track["id"]
    assert track["projectId"]
    assert track["status"]
    assert track["createdAt"]
    assert track["updatedAt"]
    assert track["alignment"]["status"]
    assert "diffSummary" in track["alignment"]
    assert "errorCode" in track["alignment"]
    assert "errorMessage" in track["alignment"]
    assert "nextAction" in track["alignment"]


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
            VoiceTrack(
                id="voice-track-1",
                project_id="project-subtitle",
                timeline_id=None,
                source="tts",
                provider="openai",
                voice_name="标准女声",
                file_path=str(tmp_path / "voice.mp3"),
                segments_json='[{"segmentIndex":0,"text":"第一句"}]',
                status="ready",
                version=3,
                config_json="{}",
                created_at=now,
                updated_at=now,
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
                  {"segmentIndex": 0, "text": "第一句", "startMs": 0, "endMs": 1800, "confidence": 0.92, "locked": true},
                  {"segmentIndex": 1, "text": "第二句", "startMs": 1800, "endMs": 3600, "confidence": 0.88, "locked": true}
                ]
                """.strip(),
                metadata_json=json.dumps(
                    {
                        "sourceVoice": {
                            "trackId": "voice-track-1",
                            "revision": 3,
                            "updatedAt": now,
                        },
                        "alignment": {
                            "status": "aligned",
                            "diffSummary": {
                                "segmentCountChanged": False,
                                "timingChangedSegments": 0,
                                "textChangedSegments": 0,
                                "lockedSegments": 2,
                            },
                            "errorCode": None,
                            "errorMessage": None,
                            "nextAction": "可继续导出字幕。",
                            "updatedAt": now,
                        },
                    },
                    ensure_ascii=False,
                ),
                status="ready",
                created_at=now,
                updated_at=now,
            )
        )
        session.commit()

    app = FastAPI()
    app.state.subtitle_service = SubtitleService(
        SubtitleRepository(session_factory=session_factory),
        voice_repository=VoiceRepository(session_factory=session_factory),
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


def test_subtitle_track_contract_returns_source_voice_and_alignment(tmp_path: Path) -> None:
    client = TestClient(_build_app(tmp_path))

    response = client.get("/api/subtitles/tracks/subtitle-track-1")

    assert response.status_code == 200
    track = _assert_ok(response.json())
    _assert_subtitle_track_contract(track)
    assert track["sourceVoice"]["trackId"] == "voice-track-1"
    assert track["sourceVoice"]["revision"] == 3
    assert track["alignment"]["status"] == "aligned"


def test_subtitle_generate_contract_returns_draft_when_source_voice_missing(
    tmp_path: Path,
) -> None:
    client = TestClient(_build_app(tmp_path))

    response = client.post(
        "/api/subtitles/projects/project-subtitle/tracks/generate",
        json={
            "sourceText": "第一句\n第二句",
            "language": "zh-CN",
            "stylePreset": "creator-default",
        },
    )

    assert response.status_code == 200
    data = _assert_ok(response.json())
    track = data["track"]
    _assert_subtitle_track_contract(track)
    assert track["sourceVoice"] is None
    assert track["alignment"]["status"] == "draft"


def test_subtitle_generate_contract_returns_source_voice_snapshot(
    tmp_path: Path,
) -> None:
    client = TestClient(_build_app(tmp_path))

    response = client.post(
        "/api/subtitles/projects/project-subtitle/tracks/generate",
        json={
            "sourceText": "第一句\n第二句",
            "language": "zh-CN",
            "stylePreset": "creator-default",
            "sourceVoiceTrackId": "voice-track-1",
        },
    )

    assert response.status_code == 200
    data = _assert_ok(response.json())
    track = data["track"]
    _assert_subtitle_track_contract(track)
    assert track["sourceVoice"]["trackId"] == "voice-track-1"
    assert track["sourceVoice"]["revision"] == 3
    assert track["alignment"]["status"] == "pending_alignment"


def test_subtitle_align_contract_updates_diff_summary(tmp_path: Path) -> None:
    client = TestClient(_build_app(tmp_path))

    response = client.post(
        "/api/subtitles/tracks/subtitle-track-1/align",
        json={
            "segments": [
                {
                    "segmentIndex": 0,
                    "text": "第一句",
                    "startMs": 0,
                    "endMs": 1600,
                    "confidence": 0.92,
                    "locked": True,
                },
                {
                    "segmentIndex": 1,
                    "text": "第二句已调整",
                    "startMs": 1600,
                    "endMs": 3600,
                    "confidence": 0.88,
                    "locked": False,
                },
            ]
        },
    )

    assert response.status_code == 200
    track = _assert_ok(response.json())
    _assert_subtitle_track_contract(track)
    diff = track["alignment"]["diffSummary"]
    assert track["alignment"]["status"] == "aligned"
    assert diff["segmentCountChanged"] is False
    assert diff["timingChangedSegments"] == 2
    assert diff["textChangedSegments"] == 1


def test_subtitle_align_contract_rejects_missing_timecodes_with_chinese_error(
    tmp_path: Path,
) -> None:
    client = TestClient(_build_app(tmp_path))

    response = client.post(
        "/api/subtitles/tracks/subtitle-track-1/align",
        json={
            "segments": [
                {
                    "segmentIndex": 0,
                    "text": "第一句",
                    "startMs": 0,
                    "endMs": None,
                }
            ]
        },
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["ok"] is False
    assert "时间码" in payload["error"]


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
