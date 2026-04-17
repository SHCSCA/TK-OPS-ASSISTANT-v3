from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import HTTPException

from common.time import utc_now_iso
from domain.models import Base, Project, SubtitleTrack
from persistence.engine import create_runtime_engine, create_session_factory
from repositories.subtitle_repository import SubtitleRepository
from schemas.subtitles import (
    SubtitleExportInput,
    SubtitleSegmentDto,
    SubtitleStyleDto,
    SubtitleTrackAlignInput,
)
from services.subtitle_service import SubtitleService


def _make_subtitle_service(tmp_path: Path) -> SubtitleService:
    engine = create_runtime_engine(tmp_path / "runtime.db")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    now = utc_now_iso()
    with session_factory() as session:
        session.add(
            Project(
                id="project-subtitle",
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
                status="ready",
                created_at=now,
            )
        )
        session.commit()

    return SubtitleService(SubtitleRepository(session_factory=session_factory))


def test_align_track_updates_segment_times_and_status(tmp_path: Path) -> None:
    service = _make_subtitle_service(tmp_path)

    updated = service.align_track(
        "subtitle-track-1",
        SubtitleTrackAlignInput(
            segments=[
                SubtitleSegmentDto(
                    segmentIndex=0,
                    text="第一句",
                    startMs=0,
                    endMs=1800,
                    confidence=0.92,
                    locked=True,
                ),
                SubtitleSegmentDto(
                    segmentIndex=1,
                    text="第二句",
                    startMs=1800,
                    endMs=3600,
                    confidence=0.88,
                    locked=True,
                ),
            ]
        ),
    )

    assert updated.status == "ready"
    assert updated.segments[0].startMs == 0
    assert updated.segments[1].endMs == 3600


def test_list_style_templates_returns_builtin_templates(tmp_path: Path) -> None:
    service = _make_subtitle_service(tmp_path)

    templates = service.list_style_templates()

    assert templates
    assert templates[0].style.preset


def test_export_track_returns_real_text_for_supported_formats(
    tmp_path: Path,
) -> None:
    service = _make_subtitle_service(tmp_path)

    export = service.export_track("subtitle-track-1", SubtitleExportInput(format="srt"))

    assert export.format == "srt"
    assert export.status == "ready"
    assert "第一句" in export.content
    assert export.lineCount > 0


def test_align_missing_track_rejects_unknown_track(tmp_path: Path) -> None:
    service = _make_subtitle_service(tmp_path)

    with pytest.raises(HTTPException) as exc_info:
        service.align_track(
            "missing-track",
            SubtitleTrackAlignInput(
                segments=[
                    SubtitleSegmentDto(
                        segmentIndex=0,
                        text="第一句",
                        startMs=0,
                        endMs=1800,
                    )
                ]
            ),
        )

    assert exc_info.value.status_code == 404
    assert "字幕" in str(exc_info.value.detail)
