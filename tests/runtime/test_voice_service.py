from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi import HTTPException

from common.time import utc_now_iso
from domain.models import Base, Project
from persistence.engine import create_runtime_engine, create_session_factory
from repositories.voice_repository import VoiceRepository
from schemas.voice import VoiceTrackGenerateInput
from services.voice_service import VoiceService


def _make_voice_service(tmp_path: Path) -> VoiceService:
    engine = create_runtime_engine(tmp_path / "runtime.db")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    with session_factory() as session:
        now = utc_now_iso()
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
        session.commit()
    repository = VoiceRepository(session_factory=session_factory)
    return VoiceService(repository)


def test_list_profiles_returns_chinese_default_voice(tmp_path: Path) -> None:
    service = _make_voice_service(tmp_path)

    profiles = service.list_profiles()

    assert profiles[0].id == "alloy-zh"
    assert profiles[0].displayName == "清晰叙述"
    assert "旁白" in profiles[0].tags


def test_generate_track_blocks_without_provider_and_keeps_segments_json(
    tmp_path: Path,
) -> None:
    service = _make_voice_service(tmp_path)

    result = service.generate_track(
        "project-voice",
        VoiceTrackGenerateInput(
            profileId="alloy-zh",
            sourceText="第一段脚本\n\n第二段脚本",
            speed=1.0,
            pitch=0,
            emotion="calm",
        ),
    )

    assert result.track.status == "blocked"
    assert result.track.provider == "pending_provider"
    assert result.track.filePath is None
    assert result.track.segments[0].text == "第一段脚本"
    assert result.track.segments[1].segmentIndex == 1
    assert result.task is None
    assert "TTS Provider" in result.message

    stored = service.get_track(result.track.id)
    encoded_segments = json.dumps(
        [segment.model_dump(mode="json") for segment in stored.segments],
        ensure_ascii=False,
    )
    assert "第一段脚本" in encoded_segments


def test_generate_track_rejects_empty_source_text(tmp_path: Path) -> None:
    service = _make_voice_service(tmp_path)

    with pytest.raises(HTTPException) as exc_info:
        service.generate_track(
            "project-voice",
            VoiceTrackGenerateInput(
                profileId="alloy-zh",
                sourceText="  \n ",
                speed=1.0,
                pitch=0,
                emotion="calm",
            ),
        )

    assert exc_info.value.status_code == 400
    assert "脚本文本为空" in str(exc_info.value.detail)


def test_delete_missing_track_returns_chinese_error(tmp_path: Path) -> None:
    service = _make_voice_service(tmp_path)

    with pytest.raises(HTTPException) as exc_info:
        service.delete_track("missing-track")

    assert exc_info.value.status_code == 404
    assert "配音版本不存在" in str(exc_info.value.detail)
