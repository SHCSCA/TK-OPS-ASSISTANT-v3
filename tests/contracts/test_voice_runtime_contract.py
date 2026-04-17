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
from domain.models import Base, Project, VoiceTrack
from persistence.engine import create_runtime_engine, create_session_factory
from repositories.voice_profile_repository import VoiceProfileRepository
from repositories.voice_repository import VoiceRepository
from schemas.envelope import error_response
from services.task_manager import TaskManager
from services.voice_service import VoiceService
from voice import router as voice_router


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
                id="project-voice",
                name="配音项目",
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
                project_id="project-voice",
                timeline_id=None,
                source="tts",
                provider="pending_provider",
                voice_name="标准女声",
                file_path=None,
                segments_json="""
                [
                  {"segmentIndex": 0, "text": "第一段文本", "startMs": null, "endMs": null, "audioAssetId": null},
                  {"segmentIndex": 1, "text": "第二段文本", "startMs": null, "endMs": null, "audioAssetId": null}
                ]
                """.strip(),
                status="ready",
                created_at=now,
            )
        )
        session.commit()

    app = FastAPI()
    app.state.voice_service = VoiceService(
        VoiceRepository(session_factory=session_factory),
        profile_repository=VoiceProfileRepository(session_factory=session_factory),
        task_manager=TaskManager(),
    )
    app.include_router(voice_router)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException):  # type: ignore[no-untyped-def]
        message = exc.detail if isinstance(exc.detail, str) else "请求失败"
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(message),
        )

    return app


def test_voice_profiles_contract_persists_custom_profile(tmp_path: Path) -> None:
    client = TestClient(_build_app(tmp_path))

    create_response = client.post(
        "/api/voice/profiles",
        json={
            "provider": "openai",
            "voiceId": "shimmer",
            "displayName": "清亮女声",
            "locale": "zh-CN",
            "tags": ["清亮", "通用"],
            "enabled": True,
        },
    )
    assert create_response.status_code == 201
    created = _assert_ok(create_response.json())
    assert created["voiceId"] == "shimmer"
    assert created["displayName"] == "清亮女声"

    list_response = client.get("/api/voice/profiles")
    assert list_response.status_code == 200
    profiles = _assert_ok(list_response.json())
    assert any(profile["voiceId"] == "shimmer" for profile in profiles)


def test_voice_segment_regenerate_contract_returns_taskbus_task(
    tmp_path: Path,
) -> None:
    client = TestClient(_build_app(tmp_path))

    response = client.post(
        "/api/voice/tracks/voice-track-1/segments/1/regenerate",
        json={
            "profileId": "alloy-zh",
            "speed": 1.0,
            "pitch": 0,
            "emotion": "calm",
        },
    )

    assert response.status_code == 200
    data = _assert_ok(response.json())
    assert data["task"]["kind"] == "ai-voice"
    assert data["task"]["ownerRef"] == {"kind": "voice-track", "id": "voice-track-1"}
    assert data["task"]["status"] in {"queued", "running", "succeeded"}


def test_voice_waveform_contract_returns_unavailable_when_no_audio_file(
    tmp_path: Path,
) -> None:
    client = TestClient(_build_app(tmp_path))

    response = client.get("/api/voice/tracks/voice-track-1/waveform")

    assert response.status_code == 200
    data = _assert_ok(response.json())
    assert data["status"] == "unavailable"
    assert data["points"] == []
    assert "不可用" in data["message"]
