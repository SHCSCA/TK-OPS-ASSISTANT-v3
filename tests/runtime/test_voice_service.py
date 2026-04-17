from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import HTTPException

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
from services.task_manager import TaskManager
from services.voice_service import VoiceService


def _make_voice_service(tmp_path: Path) -> VoiceService:
    engine = create_runtime_engine(tmp_path / "runtime.db")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
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

    return VoiceService(
        VoiceRepository(session_factory=session_factory),
        profile_repository=VoiceProfileRepository(session_factory=session_factory),
        task_manager=TaskManager(),
    )


def test_list_profiles_seeds_builtin_profiles_and_supports_create(
    tmp_path: Path,
) -> None:
    service = _make_voice_service(tmp_path)

    profiles = service.list_profiles()
    assert profiles
    assert profiles[0].voiceId == "alloy"

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


def test_regenerate_segment_returns_taskbus_task(tmp_path: Path) -> None:
    service = _make_voice_service(tmp_path)

    result = service.regenerate_segment(
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


def test_fetch_waveform_returns_unavailable_without_audio_file(
    tmp_path: Path,
) -> None:
    service = _make_voice_service(tmp_path)

    waveform = service.fetch_waveform("voice-track-1")

    assert waveform.status == "unavailable"
    assert waveform.points == []
    assert "不可用" in waveform.message


def test_regenerate_missing_segment_rejects_unknown_segment(
    tmp_path: Path,
) -> None:
    service = _make_voice_service(tmp_path)

    with pytest.raises(HTTPException) as exc_info:
        service.regenerate_segment(
            "voice-track-1",
            "999",
            VoiceSegmentRegenerateInput(profileId="alloy-zh"),
        )

    assert exc_info.value.status_code == 404
    assert "片段" in str(exc_info.value.detail)
