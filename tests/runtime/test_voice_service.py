from __future__ import annotations

import asyncio
import json
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from ai.providers import dispatch_tts
from ai.providers.base import TTSResponse
from ai.providers.errors import ProviderHTTPException
from common.time import utc_now_iso
from domain.models import Base, Project, VoiceTrack
from persistence.engine import create_runtime_engine, create_session_factory
from repositories.voice_profile_repository import VoiceProfileRepository
from repositories.voice_repository import VoiceRepository
from schemas.voice import (
    VoiceProfileCreateInput,
    VoiceSegmentRegenerateInput,
    VoiceTrackGenerateInput,
)
from services.ai_capability_service import ProviderRuntimeConfig
from services.task_manager import TaskManager
from services.voice_artifact_store import VoiceArtifactStore
from services.voice_service import VoiceService


class _FakeAICapabilityService:
    def __init__(
        self,
        *,
        runtime: ProviderRuntimeConfig,
        capability_provider: str = "openai",
        capability_model: str = "gpt-4o-mini-tts",
    ) -> None:
        self._runtime = runtime
        self._capability = SimpleNamespace(
            provider=capability_provider,
            model=capability_model,
        )

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


def _field(value: object, name: str) -> object:
    if isinstance(value, dict):
        return value[name]
    return getattr(value, name)


def _seed_project(session_factory) -> None:
    now = utc_now_iso()
    with session_factory() as session:
        session.add(
            Project(
                id="project-voice",
                name="配音测试项目",
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
                provider="openai",
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


def _make_voice_service(
    tmp_path: Path,
    *,
    ai_capability_service=None,
    tts_dispatcher=None,
    artifact_store=None,
) -> tuple[VoiceService, VoiceRepository, TaskManager]:
    engine = create_runtime_engine(tmp_path / "runtime.db")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    _seed_project(session_factory)

    task_manager = TaskManager()
    repository = VoiceRepository(session_factory=session_factory)
    service = VoiceService(
        repository,
        profile_repository=VoiceProfileRepository(session_factory=session_factory),
        task_manager=task_manager,
        ai_capability_service=ai_capability_service,
        tts_dispatcher=tts_dispatcher,
        voice_artifact_store=artifact_store,
    )
    return service, repository, task_manager


async def _wait_for_task(task_manager: TaskManager, task_id: str) -> str:
    for _ in range(100):
        task = task_manager.get(task_id)
        if task is not None and task.status in {"succeeded", "failed", "cancelled"}:
            return task.status
        await asyncio.sleep(0.01)
    raise AssertionError(f"任务未在预期时间内结束: {task_id}")


def test_list_profiles_seeds_builtin_profiles_and_supports_create(
    tmp_path: Path,
) -> None:
    service, _, _ = _make_voice_service(tmp_path)

    profiles = service.list_profiles()
    assert profiles
    assert profiles[0].voiceId == "alloy"
    assert profiles[0].provider == "openai"

    created = service.create_profile(
        VoiceProfileCreateInput(
            provider="openai",
            voiceId="shimmer",
            displayName="清亮女声",
            locale="zh-CN",
            tags=["清亮", "通用"],
            enabled=True,
        )
    )

    assert created.voiceId == "shimmer"
    assert created.enabled is True
    assert any(profile.voiceId == "shimmer" for profile in service.list_profiles())


def test_get_track_returns_ready_snapshot_with_version_and_preview(
    tmp_path: Path,
) -> None:
    service, _, _ = _make_voice_service(tmp_path)

    track = service.get_track("voice-track-1")

    assert _field(track, "status") == "ready"
    assert _field(_field(track, "version"), "revision") >= 1
    assert _field(_field(track, "version"), "updatedAt")
    assert _field(_field(track, "config"), "parameterSource") in {
        "seed",
        "profile",
        "runtime",
        "manual",
    }
    assert _field(_field(track, "preview"), "status") in {"ready", "missing_audio"}
    assert _field(track, "activeTask") is None


def test_generate_track_returns_blocked_when_tts_is_not_available(
    tmp_path: Path,
) -> None:
    service, repository, _ = _make_voice_service(tmp_path)

    result = service.generate_track(
        "project-voice",
        VoiceTrackGenerateInput(
            profileId="alloy-zh",
            sourceText="第一句\n第二句",
        ),
    )

    assert result.track.status == "blocked"
    assert _field(_field(result.track, "version"), "revision") >= 1
    assert _field(_field(result.track, "version"), "updatedAt")
    assert _field(_field(result.track, "config"), "parameterSource") in {
        "seed",
        "profile",
        "runtime",
        "manual",
    }
    assert _field(_field(result.track, "preview"), "status") in {"blocked", "missing_audio"}
    assert result.task is None
    assert _field(result.track, "activeTask") is None
    assert "TTS Provider" in result.message

    stored = repository.get_track(result.track.id)
    assert stored is not None
    assert stored.status == "blocked"
    assert stored.file_path is None


def test_generate_track_returns_blocked_when_provider_has_no_registered_tts_adapter(
    tmp_path: Path,
) -> None:
    runtime = ProviderRuntimeConfig(
        provider="localai",
        label="LocalAI",
        api_key=None,
        base_url="http://127.0.0.1:8080/v1",
        secret_source="test",
        requires_secret=False,
        supports_text_generation=True,
        supports_tts=True,
        protocol_family="openai_chat",
    )
    service, repository, _ = _make_voice_service(
        tmp_path,
        ai_capability_service=_FakeAICapabilityService(
            runtime=runtime,
            capability_provider="localai",
            capability_model="localai-tts-model",
        ),
        tts_dispatcher=dispatch_tts,
        artifact_store=VoiceArtifactStore(
            settings_service=_FakeSettingsService(tmp_path / "workspace")
        ),
    )
    profile = service.create_profile(
        VoiceProfileCreateInput(
            provider="localai",
            voiceId="localai-voice",
            displayName="本地音色",
            locale="zh-CN",
            tags=["本地"],
            enabled=True,
        )
    )

    result = service.generate_track(
        "project-voice",
        VoiceTrackGenerateInput(
            profileId=profile.id,
            sourceText="待合成文本",
        ),
    )

    assert result.track.status == "blocked"
    assert _field(_field(result.track, "version"), "revision") >= 1
    assert _field(_field(result.track, "version"), "updatedAt")
    assert _field(_field(result.track, "config"), "parameterSource") in {
        "seed",
        "profile",
        "runtime",
        "manual",
    }
    assert _field(_field(result.track, "preview"), "status") in {"blocked", "missing_audio"}
    assert result.task is None
    assert "TTS Provider" in result.message

    stored = repository.get_track(result.track.id)
    assert stored is not None
    assert stored.status == "blocked"


def test_generate_track_submits_task_and_writes_audio_file_when_openai_tts_is_available(
    tmp_path: Path,
) -> None:
    runtime = ProviderRuntimeConfig(
        provider="openai",
        label="OpenAI",
        api_key="sk-test-openai",
        base_url="https://api.openai.com/v1/responses",
        secret_source="test",
        requires_secret=True,
        supports_text_generation=True,
        supports_tts=True,
        protocol_family="openai_responses",
    )
    settings_service = _FakeSettingsService(tmp_path / "workspace")
    service, repository, task_manager = _make_voice_service(
        tmp_path,
        ai_capability_service=_FakeAICapabilityService(runtime=runtime),
        tts_dispatcher=lambda runtime_config, request: TTSResponse(
            audio_bytes=b"voice-bytes",
            content_type="audio/mpeg",
            provider="openai",
            model=request.model,
        ),
        artifact_store=VoiceArtifactStore(settings_service=settings_service),
    )

    async def _run() -> None:
        result = service.generate_track(
            "project-voice",
            VoiceTrackGenerateInput(
                profileId="alloy-zh",
                sourceText="第一句\n第二句",
                speed=1.1,
            ),
        )

        assert result.track.status == "processing"
        assert _field(_field(result.track, "version"), "revision") >= 1
        assert _field(_field(result.track, "version"), "updatedAt")
        assert _field(_field(result.track, "config"), "parameterSource") in {
            "seed",
            "profile",
            "runtime",
            "manual",
        }
        assert _field(_field(result.track, "preview"), "status") == "processing"
        assert result.task is not None
        assert _field(result.track, "activeTask") is not None
        assert _field(result.track.activeTask, "status") in {"queued", "running"}
        assert _field(result.track.activeTask, "id") == result.task["id"]
        assert result.task["kind"] == "ai-voice"
        assert result.task["ownerRef"] == {"kind": "voice-track", "id": result.track.id}

        final_status = await _wait_for_task(task_manager, result.task["id"])
        assert final_status == "succeeded"

        stored = repository.get_track(result.track.id)
        assert stored is not None
        assert stored.status == "ready"
        assert stored.provider == "openai"
        assert stored.file_path is not None
        output_path = Path(stored.file_path)
        assert output_path.exists()
        assert output_path.read_bytes() == b"voice-bytes"
        assert output_path.parent == settings_service._workspace_root / "voice"
        assert output_path.name == f"{result.track.id}.mp3"

    asyncio.run(_run())


def test_generate_track_marks_failed_when_tts_dispatcher_raises(
    tmp_path: Path,
) -> None:
    runtime = ProviderRuntimeConfig(
        provider="openai",
        label="OpenAI",
        api_key="sk-test-openai",
        base_url="https://api.openai.com/v1/responses",
        secret_source="test",
        requires_secret=True,
        supports_text_generation=True,
        supports_tts=True,
        protocol_family="openai_responses",
    )
    service, repository, task_manager = _make_voice_service(
        tmp_path,
        ai_capability_service=_FakeAICapabilityService(runtime=runtime),
        tts_dispatcher=lambda runtime_config, request: (_ for _ in ()).throw(
            ProviderHTTPException(
                status_code=502,
                detail="AI Provider 返回错误",
                error_code="ai_provider_server_error",
            )
        ),
        artifact_store=VoiceArtifactStore(
            settings_service=_FakeSettingsService(tmp_path / "workspace")
        ),
    )

    async def _run() -> None:
        result = service.generate_track(
            "project-voice",
            VoiceTrackGenerateInput(
                profileId="alloy-zh",
                sourceText="失败文本",
            ),
        )

        assert result.track.status == "processing"
        assert _field(_field(result.track, "version"), "revision") >= 1
        assert _field(_field(result.track, "version"), "updatedAt")
        assert _field(_field(result.track, "preview"), "status") == "processing"
        assert result.task is not None

        final_status = await _wait_for_task(task_manager, result.task["id"])
        assert final_status == "failed"

        stored = repository.get_track(result.track.id)
        assert stored is not None
        assert stored.status == "failed"
        assert stored.file_path is None

        snapshot = service.get_track(result.track.id)
        assert snapshot.status == "failed"
        assert _field(_field(snapshot, "version"), "revision") >= 1
        assert _field(_field(snapshot, "version"), "updatedAt")
        assert _field(_field(snapshot, "preview"), "status") == "failed"
        active_task = _field(snapshot, "activeTask")
        if active_task is not None:
            assert _field(active_task, "status") == "failed"

    asyncio.run(_run())


def test_generate_track_offloads_tts_dispatch_and_file_write_from_event_loop_thread(
    tmp_path: Path,
) -> None:
    runtime = ProviderRuntimeConfig(
        provider="openai",
        label="OpenAI",
        api_key="sk-test-openai",
        base_url="https://api.openai.com/v1/responses",
        secret_source="test",
        requires_secret=True,
        supports_text_generation=True,
        supports_tts=True,
        protocol_family="openai_responses",
    )
    thread_ids: dict[str, int] = {}

    class _RecordingArtifactStore:
        def __init__(self, output_root: Path) -> None:
            self._output_root = output_root

        def write_audio(
            self,
            track_id: str,
            *,
            audio_bytes: bytes,
            output_format: str,
        ) -> str:
            thread_ids["artifact"] = threading.get_ident()
            output_path = self._output_root / f"{track_id}.{output_format}"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(audio_bytes)
            return str(output_path)

    def _fake_dispatcher(runtime_config, request):
        thread_ids["dispatcher"] = threading.get_ident()
        return TTSResponse(
            audio_bytes=b"thread-check",
            content_type="audio/mpeg",
            provider="openai",
            model=request.model,
        )

    service, _, task_manager = _make_voice_service(
        tmp_path,
        ai_capability_service=_FakeAICapabilityService(runtime=runtime),
        tts_dispatcher=_fake_dispatcher,
        artifact_store=_RecordingArtifactStore(tmp_path / "voice-output"),
    )

    async def _run() -> None:
        loop_thread_id = threading.get_ident()
        result = service.generate_track(
            "project-voice",
            VoiceTrackGenerateInput(
                profileId="alloy-zh",
                sourceText="line-1\nline-2",
            ),
        )

        assert result.task is not None
        final_status = await _wait_for_task(task_manager, result.task["id"])
        assert final_status == "succeeded"
        assert thread_ids["dispatcher"] != loop_thread_id
        assert thread_ids["artifact"] != loop_thread_id

    asyncio.run(_run())


def test_generate_track_marks_failed_when_audio_write_fails(
    tmp_path: Path,
) -> None:
    runtime = ProviderRuntimeConfig(
        provider="openai",
        label="OpenAI",
        api_key="sk-test-openai",
        base_url="https://api.openai.com/v1/responses",
        secret_source="test",
        requires_secret=True,
        supports_text_generation=True,
        supports_tts=True,
        protocol_family="openai_responses",
    )

    class _FailingArtifactStore:
        def write_audio(
            self,
            track_id: str,
            *,
            audio_bytes: bytes,
            output_format: str,
        ) -> str:
            raise OSError("disk full")

    service, repository, task_manager = _make_voice_service(
        tmp_path,
        ai_capability_service=_FakeAICapabilityService(runtime=runtime),
        tts_dispatcher=lambda runtime_config, request: TTSResponse(
            audio_bytes=b"voice-bytes",
            content_type="audio/mpeg",
            provider="openai",
            model=request.model,
        ),
        artifact_store=_FailingArtifactStore(),
    )

    async def _run() -> None:
        result = service.generate_track(
            "project-voice",
            VoiceTrackGenerateInput(
                profileId="alloy-zh",
                sourceText="line-1",
            ),
        )

        assert result.track.status == "processing"
        assert _field(_field(result.track, "version"), "revision") >= 1
        assert _field(_field(result.track, "version"), "updatedAt")
        assert _field(_field(result.track, "preview"), "status") == "processing"
        assert result.task is not None
        assert _field(result.track, "activeTask") is not None

        final_status = await _wait_for_task(task_manager, result.task["id"])
        assert final_status == "failed"

        stored = repository.get_track(result.track.id)
        assert stored is not None
        assert stored.status == "failed"
        assert stored.file_path is None

        snapshot = service.get_track(result.track.id)
        assert snapshot.status == "failed"
        assert _field(_field(snapshot, "version"), "revision") >= 1
        assert _field(_field(snapshot, "version"), "updatedAt")
        assert _field(_field(snapshot, "preview"), "status") == "failed"
        active_task = _field(snapshot, "activeTask")
        if active_task is not None:
            assert _field(active_task, "status") == "failed"

    asyncio.run(_run())


def test_regenerate_segment_returns_taskbus_task(tmp_path: Path) -> None:
    runtime = ProviderRuntimeConfig(
        provider="openai",
        label="OpenAI",
        api_key="sk-test-openai",
        base_url="https://api.openai.com/v1/responses",
        secret_source="test",
        requires_secret=True,
        supports_text_generation=True,
        supports_tts=True,
        protocol_family="openai_responses",
    )
    settings_service = _FakeSettingsService(tmp_path / "workspace")
    service, repository, task_manager = _make_voice_service(
        tmp_path,
        ai_capability_service=_FakeAICapabilityService(runtime=runtime),
        tts_dispatcher=lambda runtime_config, request: TTSResponse(
            audio_bytes=b"regenerated-segment",
            content_type="audio/mpeg",
            provider="openai",
            model=request.model,
        ),
        artifact_store=VoiceArtifactStore(settings_service=settings_service),
    )

    async def _run() -> None:
        result = await service.regenerate_segment(
            "voice-track-1",
            "1",
            VoiceSegmentRegenerateInput(
                profileId="alloy-zh",
                speed=1.0,
                pitch=0,
                emotion="calm",
            ),
        )

        assert result.task is not None
        assert result.task["kind"] == "ai-voice"
        assert result.task["ownerRef"] == {"kind": "voice-track", "id": "voice-track-1"}
        assert result.task["status"] in {"queued", "running", "succeeded"}
        assert _field(_field(result.track, "version"), "revision") >= 1
        assert _field(_field(result.track, "version"), "updatedAt")
        assert _field(_field(result.track, "config"), "parameterSource") in {
            "seed",
            "profile",
            "runtime",
            "manual",
        }
        assert _field(_field(result.track, "preview"), "status") in {"processing", "ready"}
        active_task = _field(result.track, "activeTask")
        assert active_task is not None
        assert _field(active_task, "status") in {"queued", "running", "succeeded"}

        final_status = await _wait_for_task(task_manager, result.task["id"])
        assert final_status == "succeeded"

        stored = repository.get_track("voice-track-1")
        assert stored is not None
        segments = json.loads(stored.segments_json)
        assert segments[1]["regeneration"]["status"] == "succeeded"
        assert segments[1]["regeneration"]["profileId"] == "alloy-zh"
        assert segments[1]["regeneration"]["taskId"] == result.task["id"]

    asyncio.run(_run())


def test_regenerate_segment_returns_blocked_result_when_tts_provider_is_missing(
    tmp_path: Path,
) -> None:
    service, repository, _ = _make_voice_service(tmp_path)

    result = asyncio.run(
        service.regenerate_segment(
            "voice-track-1",
            "1",
            VoiceSegmentRegenerateInput(
                profileId="alloy-zh",
                speed=1.0,
                pitch=0,
                emotion="calm",
            ),
        )
    )

    assert result.task is not None
    assert result.task["status"] == "blocked"
    assert result.task["retryable"] is True
    assert result.track.status == "blocked"
    assert _field(_field(result.track, "version"), "revision") >= 1
    assert _field(_field(result.track, "version"), "updatedAt")
    assert _field(_field(result.track, "config"), "parameterSource") in {
        "seed",
        "profile",
        "runtime",
        "manual",
    }
    assert _field(_field(result.track, "preview"), "status") in {"blocked", "missing_audio"}
    active_task = _field(result.track, "activeTask")
    if active_task is not None:
        assert _field(active_task, "status") == "blocked"
    assert "TTS Provider" in result.message

    stored = repository.get_track("voice-track-1")
    assert stored is not None
    segments = json.loads(stored.segments_json)
    assert segments[1]["regeneration"]["status"] == "blocked"
    assert segments[1]["regeneration"]["retryable"] is True


def test_fetch_waveform_returns_missing_audio_status_without_audio_file(
    tmp_path: Path,
) -> None:
    service, _, _ = _make_voice_service(tmp_path)

    waveform = service.fetch_waveform("voice-track-1")

    assert waveform.status == "missing_audio"
    assert waveform.points == []
    assert "音频文件" in waveform.message


def test_regenerate_missing_segment_rejects_unknown_segment(
    tmp_path: Path,
) -> None:
    service, _, _ = _make_voice_service(tmp_path)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            service.regenerate_segment(
                "voice-track-1",
                "999",
                VoiceSegmentRegenerateInput(profileId="alloy-zh"),
            )
        )

    assert exc_info.value.status_code == 404
    assert "片段" in str(exc_info.value.detail)
