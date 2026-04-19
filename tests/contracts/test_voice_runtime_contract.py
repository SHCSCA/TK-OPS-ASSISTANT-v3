from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from starlette.exceptions import HTTPException as StarletteHTTPException

SRC_DIR = Path(__file__).resolve().parents[2] / 'apps' / 'py-runtime' / 'src'
ROUTES_DIR = SRC_DIR / 'api' / 'routes'
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
from schemas.envelope import error_response
from services.ai_capability_service import ProviderRuntimeConfig
from services.task_manager import TaskManager
from services.voice_artifact_store import VoiceArtifactStore
from services.voice_service import VoiceService
from voice import router as voice_router


class _FakeAICapabilityService:
    def __init__(self, runtime: ProviderRuntimeConfig) -> None:
        self._runtime = runtime
        self._capability = SimpleNamespace(provider='openai', model='gpt-4o-mini-tts')

    def get_provider_runtime_config(self, provider_id: str) -> ProviderRuntimeConfig:
        assert provider_id == self._runtime.provider
        return self._runtime

    def get_capability(self, capability_id: str):
        assert capability_id == 'tts_generation'
        return self._capability


class _FakeSettingsService:
    def __init__(self, workspace_root: Path) -> None:
        self._workspace_root = workspace_root

    def get_settings(self):
        return SimpleNamespace(
            runtime=SimpleNamespace(workspaceRoot=str(self._workspace_root))
        )


def _assert_ok(payload: dict[str, object]) -> object:
    assert payload['ok'] is True
    return payload['data']


def _build_app(
    tmp_path: Path,
    *,
    ai_capability_service=None,
    tts_dispatcher=None,
    artifact_store=None,
) -> FastAPI:
    engine = create_runtime_engine(tmp_path / 'runtime.db')
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    now = utc_now_iso()
    with session_factory() as session:
        session.add(
            Project(
                id='project-voice',
                name='配音项目',
                description='',
                status='active',
                current_script_version=0,
                current_storyboard_version=0,
                created_at=now,
                updated_at=now,
                last_accessed_at=now,
            )
        )
        session.add(
            VoiceTrack(
                id='voice-track-1',
                project_id='project-voice',
                timeline_id=None,
                source='tts',
                provider='openai',
                voice_name='标准女声',
                file_path=None,
                segments_json="""
                [
                  {"segmentIndex": 0, "text": "第一段文本", "startMs": null, "endMs": null, "audioAssetId": null},
                  {"segmentIndex": 1, "text": "第二段文本", "startMs": null, "endMs": null, "audioAssetId": null}
                ]
                """.strip(),
                status='ready',
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
    )
    app.include_router(voice_router)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException):  # type: ignore[no-untyped-def]
        message = exc.detail if isinstance(exc.detail, str) else '请求失败'
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(message),
        )

    return app


def test_voice_profiles_contract_persists_custom_profile(tmp_path: Path) -> None:
    client = TestClient(_build_app(tmp_path))

    create_response = client.post(
        '/api/voice/profiles',
        json={
            'provider': 'openai',
            'voiceId': 'shimmer',
            'displayName': '清亮女声',
            'locale': 'zh-CN',
            'tags': ['清亮', '通用'],
            'enabled': True,
        },
    )
    assert create_response.status_code == 201
    created = _assert_ok(create_response.json())
    assert created['voiceId'] == 'shimmer'
    assert created['displayName'] == '清亮女声'

    list_response = client.get('/api/voice/profiles')
    assert list_response.status_code == 200
    profiles = _assert_ok(list_response.json())
    assert any(profile['voiceId'] == 'shimmer' for profile in profiles)


def test_voice_generate_track_contract_returns_blocked_when_tts_is_unavailable(
    tmp_path: Path,
) -> None:
    client = TestClient(_build_app(tmp_path))

    response = client.post(
        '/api/voice/projects/project-voice/tracks/generate',
        json={
            'profileId': 'alloy-zh',
            'sourceText': '第一句\n第二句',
            'speed': 1.0,
            'pitch': 0,
            'emotion': 'calm',
        },
    )

    assert response.status_code == 200
    data = _assert_ok(response.json())
    assert data['track']['status'] == 'blocked'
    assert data['track']['provider'] == 'openai'
    assert data['task'] is None
    assert '未配置可用 TTS Provider' in data['message']


def test_voice_generate_track_contract_returns_processing_task_when_tts_is_available(
    tmp_path: Path,
) -> None:
    runtime = ProviderRuntimeConfig(
        provider='openai',
        label='OpenAI',
        api_key='sk-test-openai',
        base_url='https://api.openai.com/v1/responses',
        secret_source='test',
        requires_secret=True,
        supports_text_generation=True,
        supports_tts=True,
        protocol_family='openai_responses',
    )
    client = TestClient(
        _build_app(
            tmp_path,
            ai_capability_service=_FakeAICapabilityService(runtime),
            tts_dispatcher=lambda runtime_config, request: TTSResponse(
                audio_bytes=b'voice-bytes',
                content_type='audio/mpeg',
                provider='openai',
                model=request.model,
            ),
            artifact_store=VoiceArtifactStore(
                settings_service=_FakeSettingsService(tmp_path / 'workspace')
            ),
        )
    )

    response = client.post(
        '/api/voice/projects/project-voice/tracks/generate',
        json={
            'profileId': 'alloy-zh',
            'sourceText': '第一句\n第二句',
            'speed': 1.0,
            'pitch': 0,
            'emotion': 'calm',
        },
    )

    assert response.status_code == 200
    data = _assert_ok(response.json())
    assert data['track']['status'] == 'processing'
    assert data['track']['provider'] == 'openai'
    assert data['task']['kind'] == 'ai-voice'
    assert data['task']['projectId'] == 'project-voice'
    assert data['task']['ownerRef'] == {'kind': 'voice-track', 'id': data['track']['id']}
    assert data['task']['status'] in {'queued', 'running'}
    assert isinstance(data['task']['message'], str)


def test_voice_segment_regenerate_contract_returns_taskbus_task(
    tmp_path: Path,
) -> None:
    runtime = ProviderRuntimeConfig(
        provider='openai',
        label='OpenAI',
        api_key='sk-test-openai',
        base_url='https://api.openai.com/v1/responses',
        secret_source='test',
        requires_secret=True,
        supports_text_generation=True,
        supports_tts=True,
        protocol_family='openai_responses',
    )
    client = TestClient(
        _build_app(
            tmp_path,
            ai_capability_service=_FakeAICapabilityService(runtime),
            tts_dispatcher=lambda runtime_config, request: TTSResponse(
                audio_bytes=b'segment-bytes',
                content_type='audio/mpeg',
                provider='openai',
                model=request.model,
            ),
            artifact_store=VoiceArtifactStore(
                settings_service=_FakeSettingsService(tmp_path / 'workspace')
            ),
        )
    )

    response = client.post(
        '/api/voice/tracks/voice-track-1/segments/1/regenerate',
        json={
            'profileId': 'alloy-zh',
            'speed': 1.0,
            'pitch': 0,
            'emotion': 'calm',
        },
    )

    assert response.status_code == 200
    data = _assert_ok(response.json())
    assert data['task']['kind'] == 'ai-voice'
    assert data['task']['ownerRef'] == {'kind': 'voice-track', 'id': 'voice-track-1'}
    assert data['task']['status'] in {'queued', 'running', 'succeeded'}
    assert data['track']['segments'][1]['regeneration']['profileId'] == 'alloy-zh'
    assert data['track']['segments'][1]['regeneration']['status'] in {
        'queued',
        'running',
        'succeeded',
    }


def test_voice_segment_regenerate_contract_returns_blocked_when_tts_is_unavailable(
    tmp_path: Path,
) -> None:
    client = TestClient(_build_app(tmp_path))

    response = client.post(
        '/api/voice/tracks/voice-track-1/segments/1/regenerate',
        json={
            'profileId': 'alloy-zh',
            'speed': 1.0,
            'pitch': 0,
            'emotion': 'calm',
        },
    )

    assert response.status_code == 200
    data = _assert_ok(response.json())
    assert data['task']['status'] == 'blocked'
    assert data['task']['retryable'] is True
    assert data['track']['segments'][1]['regeneration']['status'] == 'blocked'
    assert 'TTS Provider' in data['message']


def test_voice_waveform_contract_returns_missing_audio_when_no_audio_file(
    tmp_path: Path,
) -> None:
    client = TestClient(_build_app(tmp_path))

    response = client.get('/api/voice/tracks/voice-track-1/waveform')

    assert response.status_code == 200
    data = _assert_ok(response.json())
    assert data['status'] == 'missing_audio'
    assert data['points'] == []
    assert '音频文件' in data['message']


def test_voice_waveform_contract_returns_deterministic_summary_for_local_audio_file(
    tmp_path: Path,
) -> None:
    client = TestClient(_build_app(tmp_path))
    audio_path = tmp_path / 'workspace' / 'voice' / 'voice-track-1.mp3'
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    audio_path.write_bytes(b'voice-waveform-test-bytes-00112233445566778899')
    client.app.state.voice_repository.update_track(
        'voice-track-1',
        file_path=str(audio_path),
    )

    first_response = client.get('/api/voice/tracks/voice-track-1/waveform')
    second_response = client.get('/api/voice/tracks/voice-track-1/waveform')

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    first = _assert_ok(first_response.json())
    second = _assert_ok(second_response.json())
    assert first['status'] == 'ready'
    assert first['points']
    assert first['points'] == second['points']
    assert first['durationMs'] == second['durationMs']
