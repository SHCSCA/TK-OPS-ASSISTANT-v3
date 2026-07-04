from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from common.time import utc_now_iso
from domain.models import Base, Project, SubtitleTrack, VoiceTrack
from persistence.engine import create_runtime_engine, create_session_factory
from repositories.script_repository import ScriptRepository
from repositories.storyboard_repository import StoryboardRepository
from repositories.subtitle_repository import SubtitleRepository
from repositories.timeline_repository import TimelineRepository
from repositories.voice_repository import VoiceRepository
from schemas.workspace import WorkspaceTimelineAssembleInput
from services.task_manager import TaskManager
from services.workspace_assembly import WorkspaceAssemblyService
from services.workspace_service import WorkspaceService


@dataclass
class AssemblyFixture:
    script_repository: ScriptRepository
    service: WorkspaceAssemblyService
    storyboard_repository: StoryboardRepository
    subtitle_repository: SubtitleRepository
    timeline_repository: TimelineRepository
    voice_repository: VoiceRepository


def _make_assembly_fixture(tmp_path: Path) -> AssemblyFixture:
    engine = create_runtime_engine(tmp_path / "runtime.db")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    with session_factory() as session:
        now = utc_now_iso()
        session.add(
            Project(
                id="project-workspace",
                name="剪辑工作台测试项目",
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

    timeline_repository = TimelineRepository(session_factory=session_factory)
    workspace_service = WorkspaceService(timeline_repository, task_manager=TaskManager())
    script_repository = ScriptRepository(session_factory=session_factory)
    storyboard_repository = StoryboardRepository(session_factory=session_factory)
    voice_repository = VoiceRepository(session_factory=session_factory)
    subtitle_repository = SubtitleRepository(session_factory=session_factory)
    service = WorkspaceAssemblyService(
        timeline_repository=timeline_repository,
        script_repository=script_repository,
        storyboard_repository=storyboard_repository,
        voice_repository=voice_repository,
        subtitle_repository=subtitle_repository,
        workspace_service=workspace_service,
    )
    return AssemblyFixture(
        script_repository=script_repository,
        service=service,
        storyboard_repository=storyboard_repository,
        subtitle_repository=subtitle_repository,
        timeline_repository=timeline_repository,
        voice_repository=voice_repository,
    )


def test_assembly_creates_managed_tracks_from_latest_sources(tmp_path: Path) -> None:
    fixture = _make_assembly_fixture(tmp_path)
    _seed_script(fixture, segment_count=2)
    _seed_storyboard(fixture, scene_count=2)
    _seed_voice_track(fixture, status="ready")
    _seed_subtitle_track(fixture, status="aligned")

    result = fixture.service.assemble_project_timeline(
        "project-workspace",
        WorkspaceTimelineAssembleInput(mode="merge_managed", timelineName="主时间线"),
    )

    assert result.timeline is not None
    assert [track.id for track in result.timeline.tracks[:3]] == [
        "managed-video-storyboard",
        "managed-audio-voice",
        "managed-subtitle-track",
    ]
    assert result.timeline.durationSeconds == 10
    assert result.timeline.tracks[0].clips[0].metadata.sourceKind == "storyboard"
    assert result.timeline.tracks[0].clips[0].metadata.segmentId == "S01"
    assert result.timeline.tracks[1].clips[0].sourceType == "voice_track"
    assert result.timeline.tracks[1].clips[0].sourceId == "voice-track-ready"
    assert result.timeline.tracks[2].clips[0].sourceType == "subtitle_track"
    assert result.timeline.tracks[2].clips[0].metadata.text == "字幕 1"
    assert result.saveState is not None
    assert result.saveState.source == "assembly"
    assert result.assemblyState is not None
    assert result.assemblyState.status == "ready"
    assert [source.kind for source in result.assemblyState.sources] == [
        "script",
        "storyboard",
        "voice",
        "subtitle",
    ]


def test_assembly_aligns_ai_managed_tracks_to_storyboard_timing(tmp_path: Path) -> None:
    fixture = _make_assembly_fixture(tmp_path)
    _seed_script(fixture, segment_count=2)
    _seed_storyboard(fixture, scene_count=2)
    _seed_voice_track(
        fixture,
        status="ready",
        segments_json=json.dumps(
            [
                {"segmentIndex": 0, "text": "口播 1", "startMs": 0, "endMs": 1800},
                {"segmentIndex": 1, "text": "口播 2", "startMs": 1800, "endMs": 3600},
            ],
            ensure_ascii=False,
        ),
    )
    _seed_subtitle_track(
        fixture,
        status="aligned",
        segments_json=json.dumps(
            [
                {"segmentIndex": 0, "text": "字幕 1", "startMs": 0, "endMs": 2600},
                {"segmentIndex": 1, "text": "字幕 2", "startMs": 2600, "endMs": 5200},
            ],
            ensure_ascii=False,
        ),
    )

    result = fixture.service.assemble_project_timeline(
        "project-workspace",
        WorkspaceTimelineAssembleInput(mode="merge_managed", timelineName="主时间线"),
    )

    assert result.timeline is not None
    managed_ranges = [
        [(clip.startMs, clip.durationMs) for clip in track.clips]
        for track in result.timeline.tracks[:3]
    ]
    assert managed_ranges == [
        [(0, 5000), (5000, 5000)],
        [(0, 5000), (5000, 5000)],
        [(0, 5000), (5000, 5000)],
    ]
    assert result.timeline.durationSeconds == 10


def test_assembly_preserves_manual_tracks(tmp_path: Path) -> None:
    fixture = _make_assembly_fixture(tmp_path)
    timeline_id = _seed_existing_timeline_with_manual_track(fixture)
    _seed_script(fixture, segment_count=1)
    _seed_storyboard(fixture, scene_count=1)

    result = fixture.service.assemble_project_timeline(
        "project-workspace",
        WorkspaceTimelineAssembleInput(mode="merge_managed", timelineName="主时间线"),
    )

    assert result.timeline is not None
    track_ids = [track.id for track in result.timeline.tracks]
    assert "managed-video-storyboard" in track_ids
    assert "manual-video-track" in track_ids
    assert result.timeline.id == timeline_id


def test_assembly_rebuilds_stale_managed_tracks_and_preserves_manual_tracks(tmp_path: Path) -> None:
    fixture = _make_assembly_fixture(tmp_path)
    timeline_id = _seed_existing_timeline_with_stale_managed_tracks(fixture)
    _seed_script(fixture, segment_count=1)
    _seed_storyboard(fixture, scene_count=1)
    _seed_voice_track(fixture, status="ready")
    _seed_subtitle_track(fixture, status="aligned")

    result = fixture.service.assemble_project_timeline(
        "project-workspace",
        WorkspaceTimelineAssembleInput(mode="merge_managed", timelineName="主时间线"),
    )

    assert result.timeline is not None
    assert result.timeline.id == timeline_id
    assert [track.id for track in result.timeline.tracks] == [
        "managed-video-storyboard",
        "managed-audio-voice",
        "managed-subtitle-track",
        "manual-video-track",
    ]
    managed_ranges = [
        [(clip.startMs, clip.durationMs) for clip in track.clips]
        for track in result.timeline.tracks[:3]
    ]
    assert managed_ranges == [[(0, 5000)], [(0, 5000)], [(0, 5000)]]
    assert all(track.clips[0].label != "旧受管片段" for track in result.timeline.tracks[:3])
    assert result.timeline.tracks[3].clips[0].id == "manual-clip-1"
    assert result.timeline.durationSeconds == 5


def test_assembly_reports_missing_voice_and_subtitle_sources(tmp_path: Path) -> None:
    fixture = _make_assembly_fixture(tmp_path)
    _seed_script(fixture, segment_count=1)
    _seed_storyboard(fixture, scene_count=1)

    result = fixture.service.assemble_project_timeline(
        "project-workspace",
        WorkspaceTimelineAssembleInput(mode="merge_managed", timelineName="主时间线"),
    )

    assert result.timeline is not None
    assert result.assemblyState is not None
    assert result.assemblyState.status == "warning"
    assert "缺少可用配音轨。" in result.assemblyState.issues
    assert "缺少可用字幕轨。" in result.assemblyState.issues


def test_assembly_reports_all_missing_sources_without_misleading_success_message(tmp_path: Path) -> None:
    fixture = _make_assembly_fixture(tmp_path)

    result = fixture.service.assemble_project_timeline(
        "project-workspace",
        WorkspaceTimelineAssembleInput(mode="merge_managed", timelineName="主时间线"),
    )

    assert result.timeline is not None
    assert result.timeline.tracks == []
    assert result.assemblyState is not None
    assert result.assemblyState.status == "warning"
    assert {source.status for source in result.assemblyState.sources} == {"missing"}
    assert "未生成 AI 三轨" in result.message
    assert "补齐来源" in result.message
    assert "已从脚本、分镜、配音和字幕汇入" not in result.message
    assert result.saveState is not None
    assert result.saveState.message == "已保存当前时间线状态，未生成 AI 受管轨道。"


def _seed_script(fixture: AssemblyFixture, *, segment_count: int) -> None:
    segments = [
        {
            "segmentId": f"S{index + 1:02d}",
            "time": f"{index * 5}-{(index + 1) * 5}s",
            "goal": f"段落目标 {index + 1}",
            "voiceover": f"口播 {index + 1}",
            "subtitle": f"字幕 {index + 1}",
            "visualSuggestion": f"画面建议 {index + 1}",
        }
        for index in range(segment_count)
    ]
    fixture.script_repository.save_version(
        "project-workspace",
        source="ai_generate",
        content="\n".join(segment["voiceover"] for segment in segments),
        format="json_v1",
        document_json={"title": "测试脚本", "segments": segments},
        provider="deepseek",
        model="deepseek-v4-flash",
    )


def _seed_storyboard(fixture: AssemblyFixture, *, scene_count: int) -> None:
    scenes = [
        {
            "sceneId": f"SH{index + 1:02d}",
            "title": f"镜头 {index + 1}",
            "summary": f"镜头摘要 {index + 1}",
            "visualPrompt": f"画面提示 {index + 1}",
            "time": f"{index * 5}-{(index + 1) * 5}s",
            "voiceover": f"口播 {index + 1}",
            "subtitle": f"字幕 {index + 1}",
        }
        for index in range(scene_count)
    ]
    fixture.storyboard_repository.save_version(
        "project-workspace",
        based_on_script_revision=1,
        source="ai_generate",
        scenes=scenes,
        format="json_v1",
        storyboard_json={"shots": scenes},
        provider="deepseek",
        model="deepseek-v4-flash",
    )


def _seed_voice_track(
    fixture: AssemblyFixture,
    *,
    status: str,
    segments_json: str | None = None,
) -> None:
    now = utc_now_iso()
    fixture.voice_repository.create_track(
        VoiceTrack(
            id="voice-track-ready",
            project_id="project-workspace",
            timeline_id=None,
            source="tts",
            provider="volcengine_tts",
            voice_name="Vivi 2.0",
            file_path="voice/voice-track-ready.mp3",
            segments_json=segments_json or json.dumps(
                [
                    {
                        "segmentIndex": 0,
                        "text": "口播 1",
                        "startMs": 0,
                        "endMs": 5000,
                        "audioAssetId": None,
                    },
                    {
                        "segmentIndex": 1,
                        "text": "口播 2",
                        "startMs": 5000,
                        "endMs": 10000,
                        "audioAssetId": None,
                    },
                ],
                ensure_ascii=False,
            ),
            status=status,
            version=1,
            config_json="{}",
            created_at=now,
            updated_at=now,
        )
    )


def _seed_subtitle_track(
    fixture: AssemblyFixture,
    *,
    status: str,
    segments_json: str | None = None,
) -> None:
    now = utc_now_iso()
    fixture.subtitle_repository.create_track(
        SubtitleTrack(
            id="subtitle-track-ready",
            project_id="project-workspace",
            timeline_id=None,
            source="script",
            language="zh-CN",
            style_json=json.dumps(
                {
                    "preset": "creator-default",
                    "fontSize": 32,
                    "position": "bottom",
                    "textColor": "#FFFFFF",
                    "background": "rgba(0,0,0,0.62)",
                }
            ),
            segments_json=segments_json or json.dumps(
                [
                    {
                        "segmentIndex": 0,
                        "text": "字幕 1",
                        "startMs": 0,
                        "endMs": 5000,
                        "confidence": 0.9,
                        "locked": False,
                    },
                    {
                        "segmentIndex": 1,
                        "text": "字幕 2",
                        "startMs": 5000,
                        "endMs": 10000,
                        "confidence": 0.9,
                        "locked": False,
                    },
                ],
                ensure_ascii=False,
            ),
            metadata_json="{}",
            status=status,
            created_at=now,
            updated_at=now,
        )
    )


def _seed_existing_timeline_with_manual_track(fixture: AssemblyFixture) -> str:
    timeline = fixture.timeline_repository.create_empty("project-workspace", "主时间线")
    manual_tracks = [
        {
            "id": "manual-video-track",
            "kind": "video",
            "name": "手动视频轨",
            "orderIndex": 20,
            "locked": False,
            "muted": False,
            "clips": [
                {
                    "id": "manual-clip-1",
                    "trackId": "manual-video-track",
                    "sourceType": "manual",
                    "sourceId": None,
                    "label": "手动片段",
                    "startMs": 0,
                    "durationMs": 3000,
                    "inPointMs": 0,
                    "outPointMs": None,
                    "status": "ready",
                    "editableFields": [],
                    "metadata": {"sourceKind": "manual"},
                }
            ],
        }
    ]
    fixture.timeline_repository.update_timeline(
        timeline.id,
        name="主时间线",
        duration_seconds=3,
        tracks_json=json.dumps(manual_tracks, ensure_ascii=False),
    )
    return timeline.id


def _seed_existing_timeline_with_stale_managed_tracks(fixture: AssemblyFixture) -> str:
    timeline = fixture.timeline_repository.create_empty("project-workspace", "主时间线")
    tracks = [
        _stale_track("managed-video-storyboard", "video", "旧分镜视频轨", 0, 2000),
        _stale_track("managed-audio-voice", "audio", "旧配音轨", 1, 3000),
        _stale_track("managed-subtitle-track", "subtitle", "旧字幕轨", 2, 9000),
        {
            "id": "manual-video-track",
            "kind": "video",
            "name": "手动视频轨",
            "orderIndex": 20,
            "locked": False,
            "muted": False,
            "clips": [
                {
                    "id": "manual-clip-1",
                    "trackId": "manual-video-track",
                    "sourceType": "manual",
                    "sourceId": None,
                    "label": "手动片段",
                    "startMs": 0,
                    "durationMs": 2000,
                    "inPointMs": 0,
                    "outPointMs": None,
                    "status": "ready",
                    "editableFields": [],
                    "metadata": {"sourceKind": "manual"},
                }
            ],
        },
    ]
    fixture.timeline_repository.update_timeline(
        timeline.id,
        name="主时间线",
        duration_seconds=9,
        tracks_json=json.dumps(tracks, ensure_ascii=False),
    )
    return timeline.id


def _stale_track(
    track_id: str,
    kind: str,
    name: str,
    order_index: int,
    duration_ms: int,
) -> dict[str, object]:
    return {
        "id": track_id,
        "kind": kind,
        "name": name,
        "orderIndex": order_index,
        "locked": False,
        "muted": False,
        "clips": [
            {
                "id": f"{track_id}-stale",
                "trackId": track_id,
                "sourceType": "storyboard" if kind == "video" else "voice_track",
                "sourceId": "stale-source",
                "label": "旧受管片段",
                "startMs": 0,
                "durationMs": duration_ms,
                "inPointMs": 0,
                "outPointMs": None,
                "status": "ready",
                "editableFields": [],
                "metadata": {"sourceKind": "stale"},
            }
        ],
    }
