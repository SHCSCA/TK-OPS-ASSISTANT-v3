from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi import HTTPException

from common.time import utc_now_iso
from domain.models import Base, Project, SubtitleTrack, VoiceTrack
from persistence.engine import create_runtime_engine, create_session_factory
from repositories.subtitle_repository import SubtitleRepository
from repositories.voice_repository import VoiceRepository
from schemas.subtitles import (
    SubtitleExportInput,
    SubtitleSegmentDto,
    SubtitleStyleDto,
    SubtitleTrackAlignInput,
    SubtitleTrackGenerateInput,
    SubtitleTrackUpdateInput,
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

    return SubtitleService(
        SubtitleRepository(session_factory=session_factory),
        voice_repository=VoiceRepository(session_factory=session_factory),
    )


def test_generate_track_creates_draft_track_without_source_voice(tmp_path: Path) -> None:
    service = _make_subtitle_service(tmp_path)

    generated = service.generate_track(
        "project-subtitle",
        SubtitleTrackGenerateInput(
            sourceText="开场介绍。\n第二句内容更长一些。",
            language="zh-CN",
            stylePreset="creator-default",
        ),
    )

    assert generated.track.projectId == "project-subtitle"
    assert generated.track.source == "script"
    assert generated.track.status == "ready"
    assert generated.track.updatedAt
    assert generated.track.sourceVoice is None
    assert generated.track.alignment.status == "draft"
    assert generated.task is not None
    assert generated.task["mode"] == "deterministic-local"
    assert generated.task["segmentCount"] == 2
    assert "本地" in generated.message
    assert len(generated.track.segments) == 2


def test_generate_track_records_source_voice_snapshot(tmp_path: Path) -> None:
    service = _make_subtitle_service(tmp_path)

    generated = service.generate_track(
        "project-subtitle",
        SubtitleTrackGenerateInput(
            sourceText="第一句。\n第二句。",
            language="zh-CN",
            stylePreset="creator-default",
            sourceVoiceTrackId="voice-track-1",
        ),
    )

    assert generated.track.sourceVoice is not None
    assert generated.track.sourceVoice.trackId == "voice-track-1"
    assert generated.track.sourceVoice.revision == 3
    assert generated.track.alignment.status == "pending_alignment"


def test_align_track_updates_alignment_diff_summary(tmp_path: Path) -> None:
    service = _make_subtitle_service(tmp_path)

    updated = service.align_track(
        "subtitle-track-1",
        SubtitleTrackAlignInput(
            segments=[
                SubtitleSegmentDto(
                    segmentIndex=0,
                    text="第一句",
                    startMs=0,
                    endMs=1500,
                    confidence=0.92,
                    locked=True,
                ),
                SubtitleSegmentDto(
                    segmentIndex=1,
                    text="第二句已调整",
                    startMs=1500,
                    endMs=3600,
                    confidence=0.88,
                    locked=False,
                ),
            ]
        ),
    )

    assert updated.status == "ready"
    assert updated.alignment.status == "aligned"
    assert updated.alignment.diffSummary is not None
    assert updated.alignment.diffSummary.segmentCountChanged is False
    assert updated.alignment.diffSummary.timingChangedSegments == 2
    assert updated.alignment.diffSummary.textChangedSegments == 1
    assert updated.alignment.diffSummary.lockedSegments == 1


def test_update_track_marks_needs_alignment_when_timecodes_missing(tmp_path: Path) -> None:
    service = _make_subtitle_service(tmp_path)

    updated = service.update_track(
        "subtitle-track-1",
        SubtitleTrackUpdateInput(
            segments=[
                SubtitleSegmentDto(
                    segmentIndex=0,
                    text="第一句",
                    startMs=None,
                    endMs=None,
                )
            ],
            style=SubtitleStyleDto(preset="creator-default"),
        ),
    )

    assert updated.status == "draft"
    assert updated.alignment.status == "needs_alignment"
    assert updated.alignment.errorCode == "subtitle.timecode_incomplete"
    assert updated.alignment.errorMessage is not None
    assert "时间码" in updated.alignment.errorMessage


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


def test_export_track_rejects_missing_timecodes_with_chinese_error(
    tmp_path: Path,
) -> None:
    service = _make_subtitle_service(tmp_path)

    service.update_track(
        "subtitle-track-1",
        SubtitleTrackUpdateInput(
            segments=[
                SubtitleSegmentDto(
                    segmentIndex=0,
                    text="第一句",
                    startMs=None,
                    endMs=None,
                )
            ],
            style=SubtitleStyleDto(preset="creator-default"),
        ),
    )

    with pytest.raises(HTTPException) as exc_info:
        service.export_track("subtitle-track-1", SubtitleExportInput(format="srt"))

    assert exc_info.value.status_code == 400
    assert "时间码" in str(exc_info.value.detail)


def test_generate_track_rejects_unknown_source_voice(tmp_path: Path) -> None:
    service = _make_subtitle_service(tmp_path)

    with pytest.raises(HTTPException) as exc_info:
        service.generate_track(
            "project-subtitle",
            SubtitleTrackGenerateInput(
                sourceText="第一句",
                sourceVoiceTrackId="missing-voice-track",
            ),
        )

    assert exc_info.value.status_code == 404
    assert "音轨" in str(exc_info.value.detail)


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
