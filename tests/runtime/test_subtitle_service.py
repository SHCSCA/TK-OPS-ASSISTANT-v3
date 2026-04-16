from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi import HTTPException

from common.time import utc_now_iso
from domain.models import Base, Project
from persistence.engine import create_runtime_engine, create_session_factory
from repositories.subtitle_repository import SubtitleRepository
from schemas.subtitles import SubtitleTrackGenerateInput, SubtitleTrackUpdateInput
from services.subtitle_service import SubtitleService


def _make_subtitle_service(tmp_path: Path) -> SubtitleService:
    engine = create_runtime_engine(tmp_path / "runtime.db")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    with session_factory() as session:
        now = utc_now_iso()
        session.add(
            Project(
                id="project-subtitles",
                name="字幕测试项目",
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
    repository = SubtitleRepository(session_factory=session_factory)
    return SubtitleService(repository)


def test_generate_track_creates_blocked_track_with_real_segments(
    tmp_path: Path,
) -> None:
    service = _make_subtitle_service(tmp_path)

    result = service.generate_track(
        "project-subtitles",
        SubtitleTrackGenerateInput(
            sourceText="第一段脚本\n\n第二段脚本",
            language="zh-CN",
            stylePreset="creator-default",
        ),
    )

    assert result.track.status == "blocked"
    assert result.track.source == "script"
    assert result.track.language == "zh-CN"
    assert result.track.style.preset == "creator-default"
    assert result.track.segments[0].text == "第一段脚本"
    assert result.track.segments[0].startMs is None
    assert result.task is None
    assert "字幕对齐 Provider" in result.message

    stored = service.get_track(result.track.id)
    encoded_segments = json.dumps(
        [segment.model_dump(mode="json") for segment in stored.segments],
        ensure_ascii=False,
    )
    assert "第一段脚本" in encoded_segments


def test_update_track_persists_segments_and_style(tmp_path: Path) -> None:
    service = _make_subtitle_service(tmp_path)
    result = service.generate_track(
        "project-subtitles",
        SubtitleTrackGenerateInput(sourceText="待校正字幕"),
    )

    updated = service.update_track(
        result.track.id,
        SubtitleTrackUpdateInput(
            segments=[
                {
                    "segmentIndex": 0,
                    "text": "校正后的字幕",
                    "startMs": 0,
                    "endMs": 2200,
                    "confidence": None,
                    "locked": True,
                }
            ],
            style={
                "preset": "creator-default",
                "fontSize": 38,
                "position": "bottom",
                "textColor": "#FFFFFF",
                "background": "rgba(0,0,0,0.62)",
            },
        ),
    )

    assert updated.segments[0].text == "校正后的字幕"
    assert updated.segments[0].locked is True
    assert updated.style.fontSize == 38


def test_generate_track_rejects_empty_source_text(tmp_path: Path) -> None:
    service = _make_subtitle_service(tmp_path)

    with pytest.raises(HTTPException) as exc_info:
        service.generate_track(
            "project-subtitles",
            SubtitleTrackGenerateInput(sourceText="  \n "),
        )

    assert exc_info.value.status_code == 400
    assert "字幕源文本为空" in str(exc_info.value.detail)


def test_delete_missing_track_returns_chinese_error(tmp_path: Path) -> None:
    service = _make_subtitle_service(tmp_path)

    with pytest.raises(HTTPException) as exc_info:
        service.delete_track("missing-track")

    assert exc_info.value.status_code == 404
    assert "字幕版本不存在" in str(exc_info.value.detail)
