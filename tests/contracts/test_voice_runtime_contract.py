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

from ai.providers.base import TTSResponse
from common.time import utc_now_iso
from domain.models import Base, Project, VoiceTrack
from persistence.engine import create_runtime_engine, create_session_factory
from repositories.voice_profile_repository import VoiceProfileRepository
from repositories.voice_repository import VoiceRepository
from schemas.voice import VoiceProfileCreateInput
from schemas.envelope import error_response
from services.ai_capability_service import ProviderRuntimeConfig
from services.task_manager import TaskManager
from services.voice_artifact_store import VoiceArtifactStore
from services.voice_service import VoiceService
from voice import router as voice_router


class _FakeAICapabilityService:
    def __init__(self, runtime: ProviderRuntimeConfig) -> None:
        self._runtime = runtime
        self._capability = SimpleNamespace(provider="volcengine_tts", model="seed-tts-2.0")

    def get_provider_runtime_config(self, provider_id: str) -> ProviderRuntimeConfig:
        assert provider_id == self._runtime.provider
        return self._runtime

    def get_capability(self, capability_id: str):
        assert capability_id == "tts_generation"
        return self._capability


class _FakeSettingsService:
    def __init__(self, workspace_root: Path) -> None:
        self._workspace_root = workspace_root

    def get_settings(self):
        return SimpleNamespace(
            runtime=SimpleNamespace(workspaceRoot=str(self._workspace_root))
        )


def _assert_ok(payload: dict[str, object]) -> object:
    assert payload["ok"] is True
    return payload["data"]


def _field(value: object, name: str) -> object:
    if isinstance(value, dict):
        return value[name]
    return getattr(value, name)


def _assert_voice_track_contract(
    track: dict[str, object],
    *,
    expected_status: str,
    preview_statuses: set[str],
    active_task_statuses: set[str] | None = None,
) -> None:
    assert track["status"] == expected_status
    assert track["version"]
    assert track["updatedAt"]
    assert track["config"]
    assert track["preview"]
    assert "activeTask" in track

    version = track["version"]
    config = track["config"]
    preview = track["preview"]
    active_task = track["activeTask"]

    assert _field(version, "revision") >= 1
    assert _field(version, "updatedAt")
    assert _field(config, "parameterSource") in {"profile", "runtime", "manual", "seed"}
    assert _field(preview, "status") in preview_statuses

    if active_task is None:
        assert active_task_statuses is None
    else:
        assert active_task_statuses is not None
        assert _field(active_task, "status") in active_task_statuses


def _build_app(
    tmp_path: Path,
    *,
    ai_capability_service=None,
    tts_dispatcher=None,
    artifact_store=None,
    voice_profile_source=None,
) -> FastAPI:
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
                provider="volcengine_tts",
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
    voice_repository = VoiceRepository(session_factory=session_factory)
    app.state.voice_repository = voice_repository
    app.state.voice_service = VoiceService(
        voice_repository,
        profile_repository=VoiceProfileRepository(session_factory=session_factory),
        task_manager=TaskManager(),
        ai_capability_service=ai_capability_service,
        tts_dispatcher=tts_dispatcher,
        voice_artifact_store=artifact_store,
        voice_profile_source=voice_profile_source,
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
            "provider": "volcengine_tts",
            "voiceId": "zh_female_test_bigtts",
            "displayName": "清亮女声",
            "locale": "zh-CN",
            "tags": ["清亮", "通用"],
            "enabled": True,
        },
    )
    assert create_response.status_code == 201
    created = _assert_ok(create_response.json())
    assert created["voiceId"] == "zh_female_test_bigtts"
    assert created["displayName"] == "清亮女声"

    list_response = client.get("/api/voice/profiles")
    assert list_response.status_code == 200
    profiles = _assert_ok(list_response.json())
    assert any(profile["voiceId"] == "zh_female_test_bigtts" for profile in profiles)


def test_voice_profiles_refresh_contract_syncs_provider_voices(tmp_path: Path) -> None:
    client = TestClient(
        _build_app(
            tmp_path,
            voice_profile_source=lambda provider_id: [
                VoiceProfileCreateInput(
                    provider="volcengine_tts",
                    voiceId="zh_female_tianmei_moon_bigtts",
                    displayName="豆包甜美女声",
                    locale="zh-CN",
                    tags=["豆包", "女声"],
                    enabled=True,
                )
            ]
            if provider_id == "volcengine_tts"
            else [],
        )
    )

    response = client.post("/api/voice/providers/volcengine_tts/profiles/refresh")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    data = payload["data"]
    assert set(data) == {"provider", "status", "message", "savedCount", "profiles"}
    assert data["provider"] == "volcengine_tts"
    assert data["status"] == "refreshed"
    assert data["savedCount"] == 1
    assert data["profiles"][0]["voiceId"] == "zh_female_tianmei_moon_bigtts"


def test_voice_generate_track_contract_returns_blocked_when_tts_is_unavailable(
    tmp_path: Path,
) -> None:
    client = TestClient(_build_app(tmp_path))

    response = client.post(
        "/api/voice/projects/project-voice/tracks/generate",
        json={
            "profileId": "volcengine-vv-20-zh",
            "sourceText": "第一句\n第二句",
            "speed": 1.0,
            "pitch": 0,
            "emotion": "calm",
        },
    )

    assert response.status_code == 200
    data = _assert_ok(response.json())
    track = data["track"]
    _assert_voice_track_contract(
        track,
        expected_status="blocked",
        preview_statuses={"blocked", "missing_audio"},
    )
    assert track["provider"] == "volcengine_tts"
    assert data["task"] is None
    assert track["activeTask"] is None
    assert "TTS Provider" in data["message"]


def test_voice_generate_track_contract_returns_processing_task_when_tts_is_available(
    tmp_path: Path,
) -> None:
    runtime = ProviderRuntimeConfig(
        provider="volcengine_tts",
        label="火山豆包语音",
        api_key="api-key-test-volcengine-tts",
        base_url="https://openspeech.bytedance.com/api/v3/tts/unidirectional/sse",
        secret_source="test",
        requires_secret=True,
        supports_text_generation=False,
        supports_tts=True,
        protocol_family="volcengine_tts",
    )
    client = TestClient(
        _build_app(
            tmp_path,
            ai_capability_service=_FakeAICapabilityService(runtime),
            tts_dispatcher=lambda runtime_config, request: TTSResponse(
                audio_bytes=b"voice-bytes",
                content_type="audio/mpeg",
                provider="volcengine_tts",
                model=request.model,
            ),
            artifact_store=VoiceArtifactStore(
                settings_service=_FakeSettingsService(tmp_path / "workspace")
            ),
        )
    )

    response = client.post(
        "/api/voice/projects/project-voice/tracks/generate",
        json={
            "profileId": "volcengine-vv-20-zh",
            "sourceText": "第一句\n第二句",
            "speed": 1.0,
            "pitch": 0,
            "emotion": "calm",
        },
    )

    assert response.status_code == 200
    data = _assert_ok(response.json())
    track = data["track"]
    task = data["task"]
    _assert_voice_track_contract(
        track,
        expected_status="processing",
        preview_statuses={"processing"},
        active_task_statuses={"queued", "running"},
    )
    assert track["provider"] == "volcengine_tts"
    assert _field(track["activeTask"], "id") == task["id"]
    assert _field(track["activeTask"], "status") == task["status"]
    assert _field(track["activeTask"], "progress") == task["progress"]
    assert task["kind"] == "ai-voice"
    assert task["projectId"] == "project-voice"
    assert task["ownerRef"] == {"kind": "voice-track", "id": track["id"]}
    assert task["status"] in {"queued", "running"}
    assert isinstance(task["message"], str)


def test_voice_segment_regenerate_contract_returns_taskbus_task(
    tmp_path: Path,
) -> None:
    runtime = ProviderRuntimeConfig(
        provider="volcengine_tts",
        label="火山豆包语音",
        api_key="api-key-test-volcengine-tts",
        base_url="https://openspeech.bytedance.com/api/v3/tts/unidirectional/sse",
        secret_source="test",
        requires_secret=True,
        supports_text_generation=False,
        supports_tts=True,
        protocol_family="volcengine_tts",
    )
    client = TestClient(
        _build_app(
            tmp_path,
            ai_capability_service=_FakeAICapabilityService(runtime),
            tts_dispatcher=lambda runtime_config, request: TTSResponse(
                audio_bytes=b"segment-bytes",
                content_type="audio/mpeg",
                provider="volcengine_tts",
                model=request.model,
            ),
            artifact_store=VoiceArtifactStore(
                settings_service=_FakeSettingsService(tmp_path / "workspace")
            ),
        )
    )

    response = client.post(
        "/api/voice/tracks/voice-track-1/segments/1/regenerate",
        json={
            "profileId": "volcengine-vv-20-zh",
            "speed": 1.0,
            "pitch": 0,
            "emotion": "calm",
        },
    )

    assert response.status_code == 200
    data = _assert_ok(response.json())
    track = data["track"]
    task = data["task"]
    _assert_voice_track_contract(
        track,
        expected_status="processing",
        preview_statuses={"processing"},
        active_task_statuses={"queued", "running", "succeeded"},
    )
    assert task["kind"] == "ai-voice"
    assert task["ownerRef"] == {"kind": "voice-track", "id": "voice-track-1"}
    assert task["status"] in {"queued", "running", "succeeded"}
    assert track["segments"][1]["regeneration"]["profileId"] == "volcengine-vv-20-zh"
    assert track["segments"][1]["regeneration"]["status"] in {
        "queued",
        "running",
        "succeeded",
    }


def test_voice_segment_regenerate_contract_returns_blocked_when_tts_is_unavailable(
    tmp_path: Path,
) -> None:
    client = TestClient(_build_app(tmp_path))

    response = client.post(
        "/api/voice/tracks/voice-track-1/segments/1/regenerate",
        json={
            "profileId": "volcengine-vv-20-zh",
            "speed": 1.0,
            "pitch": 0,
            "emotion": "calm",
        },
    )

    assert response.status_code == 200
    data = _assert_ok(response.json())
    track = data["track"]
    task = data["task"]
    assert track["status"] == "blocked"
    assert track["version"]
    assert track["updatedAt"]
    assert track["config"]
    assert track["preview"]
    assert track["preview"]["status"] in {"blocked", "missing_audio"}
    assert task["status"] == "blocked"
    assert task["retryable"] is True
    assert track["segments"][1]["regeneration"]["status"] == "blocked"
    assert "TTS Provider" in data["message"]


def test_voice_track_contract_returns_ready_snapshot_with_version_and_preview(
    tmp_path: Path,
) -> None:
    client = TestClient(_build_app(tmp_path))

    response = client.get("/api/voice/tracks/voice-track-1")

    assert response.status_code == 200
    track = _assert_ok(response.json())
    _assert_voice_track_contract(
        track,
        expected_status="ready",
        preview_statuses={"ready", "missing_audio"},
    )
    assert track["provider"] == "volcengine_tts"
    assert track["activeTask"] is None


def test_voice_waveform_contract_returns_missing_audio_when_no_audio_file(
    tmp_path: Path,
) -> None:
    client = TestClient(_build_app(tmp_path))

    response = client.get("/api/voice/tracks/voice-track-1/waveform")

    assert response.status_code == 200
    data = _assert_ok(response.json())
    assert data["status"] == "missing_audio"
    assert data["points"] == []
    assert "音频文件" in data["message"]


def test_voice_waveform_contract_returns_deterministic_summary_for_local_audio_file(
    tmp_path: Path,
) -> None:
    client = TestClient(_build_app(tmp_path))
    audio_path = tmp_path / "workspace" / "voice" / "voice-track-1.mp3"
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    audio_path.write_bytes(b"voice-waveform-test-bytes-00112233445566778899")
    client.app.state.voice_repository.update_track(
        "voice-track-1",
        file_path=str(audio_path),
    )

    first_response = client.get("/api/voice/tracks/voice-track-1/waveform")
    second_response = client.get("/api/voice/tracks/voice-track-1/waveform")

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    first = _assert_ok(first_response.json())
    second = _assert_ok(second_response.json())
    assert first["status"] == "ready"
    assert first["points"]
    assert first["points"] == second["points"]
    assert first["durationMs"] == second["durationMs"]
