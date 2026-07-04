from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from urllib.parse import unquote
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from common.time import utc_now_iso
from domain.models import Asset, Base, Project
from persistence.engine import create_runtime_engine, create_session_factory
from repositories.asset_repository import AssetRepository
from repositories.timeline_repository import TimelineRepository
from schemas.workspace import (
    TimelineCreateInput,
    TimelineUpdateInput,
    WorkspaceAICommandInput,
)
from services import task_manager as task_manager_module
from services.task_manager import TaskManager
from services.workspace_service import WorkspaceService


def _make_workspace_service(
    tmp_path: Path,
    *,
    task_manager: TaskManager | None = None,
    ai_text_generation_service=None,
) -> WorkspaceService:
    service, _ = _make_workspace_context(
        tmp_path,
        task_manager=task_manager,
        ai_text_generation_service=ai_text_generation_service,
    )
    return service


def _make_workspace_context(
    tmp_path: Path,
    *,
    task_manager: TaskManager | None = None,
    ai_text_generation_service=None,
) -> tuple[WorkspaceService, AssetRepository]:
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
    repository = TimelineRepository(session_factory=session_factory)
    asset_repository = AssetRepository(session_factory=session_factory)
    return (
        WorkspaceService(
            repository,
            asset_repository=asset_repository,
            task_manager=task_manager,
            ai_text_generation_service=ai_text_generation_service,
        ),
        asset_repository,
    )


def _timeline_payload() -> list[dict[str, object]]:
    return [
        {
            "id": "track-video-1",
            "kind": "video",
            "name": "视频轨 1",
            "orderIndex": 0,
            "locked": False,
            "muted": False,
            "clips": [
                {
                    "id": "clip-video-1",
                    "trackId": "track-video-1",
                    "sourceType": "manual",
                    "sourceId": None,
                    "label": "开场镜头",
                    "startMs": 0,
                    "durationMs": 4200,
                    "inPointMs": 0,
                    "outPointMs": None,
                    "status": "ready",
                    "prompt": "开场钩子",
                    "resolution": {"width": 1920, "height": 1080},
                    "editableFields": ["label", "startMs", "durationMs", "prompt"],
                }
            ],
        },
        {
            "id": "track-audio-1",
            "kind": "audio",
            "name": "配音轨 1",
            "orderIndex": 1,
            "locked": False,
            "muted": False,
            "clips": [],
        },
    ]


def _timeline_payload_with_neighbor_clip() -> list[dict[str, object]]:
    tracks = _timeline_payload()
    video_track = tracks[0]
    clips = video_track["clips"]
    assert isinstance(clips, list)
    clips.append(
        {
            "id": "clip-video-2",
            "trackId": "track-video-1",
            "sourceType": "manual",
            "sourceId": None,
            "label": "邻近镜头",
            "startMs": 5000,
            "durationMs": 2000,
            "inPointMs": 0,
            "outPointMs": None,
            "status": "ready",
            "prompt": None,
            "resolution": None,
            "editableFields": ["label", "startMs", "durationMs"],
        }
    )
    return tracks


def _timeline_payload_with_audio_clip() -> list[dict[str, object]]:
    tracks = _timeline_payload()
    audio_track = tracks[1]
    clips = audio_track["clips"]
    assert isinstance(clips, list)
    clips.append(
        {
            "id": "clip-audio-1",
            "trackId": "track-audio-1",
            "sourceType": "manual",
            "sourceId": None,
            "label": "已有环境声",
            "startMs": 1000,
            "durationMs": 2400,
            "inPointMs": 0,
            "outPointMs": None,
            "status": "ready",
            "prompt": None,
            "resolution": None,
            "editableFields": ["label", "startMs", "durationMs"],
        }
    )
    return tracks


def _create_timeline(service: WorkspaceService) -> str:
    created = service.create_project_timeline(
        "project-workspace",
        TimelineCreateInput(name="主时间线"),
    )
    assert created.timeline is not None

    updated = service.update_timeline(
        created.timeline.id,
        TimelineUpdateInput(
            name="主时间线",
            durationSeconds=12,
            tracks=_timeline_payload(),
        ),
    )
    assert updated.timeline is not None
    return updated.timeline.id


def _create_timeline_with_audio_clip(service: WorkspaceService) -> str:
    created = service.create_project_timeline(
        "project-workspace",
        TimelineCreateInput(name="主时间线"),
    )
    assert created.timeline is not None

    updated = service.update_timeline(
        created.timeline.id,
        TimelineUpdateInput(
            name="主时间线",
            durationSeconds=12,
            tracks=_timeline_payload_with_audio_clip(),
        ),
    )
    assert updated.timeline is not None
    return updated.timeline.id


def _create_timeline_with_neighbor_clip(service: WorkspaceService) -> str:
    created = service.create_project_timeline(
        "project-workspace",
        TimelineCreateInput(name="主时间线"),
    )
    assert created.timeline is not None

    updated = service.update_timeline(
        created.timeline.id,
        TimelineUpdateInput(
            name="主时间线",
            durationSeconds=12,
            tracks=_timeline_payload_with_neighbor_clip(),
        ),
    )
    assert updated.timeline is not None
    return updated.timeline.id


def _seed_asset(
    asset_repository: AssetRepository,
    tmp_path: Path,
    *,
    asset_id: str,
    asset_type: str,
    name: str,
    file_name: str,
    duration_ms: int | None,
    metadata_json: str | None = None,
    create_file: bool = True,
) -> Asset:
    asset_path = tmp_path / file_name
    if create_file:
        asset_path.write_bytes(b"runtime asset")
    now = utc_now_iso()
    return asset_repository.create_asset(
        Asset(
            id=asset_id,
            name=name,
            type=asset_type,
            source="local",
            group_id=None,
            file_path=str(asset_path),
            file_size_bytes=asset_path.stat().st_size if asset_path.exists() else None,
            duration_ms=duration_ms,
            thumbnail_path=None,
            thumbnail_generated_at=None,
            tags=None,
            project_id="project-workspace",
            metadata_json=metadata_json,
            created_at=now,
            updated_at=now,
        )
    )


def test_get_project_timeline_returns_empty_state(tmp_path: Path) -> None:
    service = _make_workspace_service(tmp_path)

    result = service.get_project_timeline("project-workspace")

    assert result.timeline is None
    assert result.activeTask is None
    assert result.saveState is None
    assert "没有时间线" in result.message


def test_create_project_timeline_stores_empty_draft(tmp_path: Path) -> None:
    service = _make_workspace_service(tmp_path)

    result = service.create_project_timeline(
        "project-workspace",
        TimelineCreateInput(name="主时间线"),
    )

    assert result.timeline is not None
    assert result.timeline.projectId == "project-workspace"
    assert result.timeline.status == "draft"
    assert result.timeline.source == "manual"
    assert result.timeline.tracks == []
    assert result.timeline.version is not None
    assert result.timeline.version.trackCount == 0
    assert result.timeline.version.clipCount == 0
    assert result.timeline.assetReferenceStatus is not None
    assert result.timeline.assetReferenceStatus.totalClips == 0
    assert result.activeTask is None
    assert result.saveState is not None
    assert result.saveState.saved is True
    assert result.saveState.source == "create"


def test_update_timeline_persists_clip_metadata(tmp_path: Path) -> None:
    service = _make_workspace_service(tmp_path)
    created = service.create_project_timeline(
        "project-workspace",
        TimelineCreateInput(name="主时间线"),
    )
    assert created.timeline is not None

    updated = service.update_timeline(
        created.timeline.id,
        TimelineUpdateInput(
            name="主时间线",
            durationSeconds=12,
            tracks=_timeline_payload(),
        ),
    )

    assert updated.timeline is not None
    clip = updated.timeline.tracks[0].clips[0]
    assert updated.timeline.durationSeconds == 12
    assert updated.timeline.version is not None
    assert updated.timeline.version.trackCount == 2
    assert updated.timeline.version.clipCount == 1
    assert updated.timeline.assetReferenceStatus is not None
    assert updated.timeline.assetReferenceStatus.totalClips == 1
    assert updated.timeline.assetReferenceStatus.manualClips == 1
    assert updated.saveState is not None
    assert updated.saveState.source == "save"
    assert clip.label == "开场镜头"
    assert clip.prompt == "开场钩子"
    assert clip.resolution is not None
    assert clip.resolution.width == 1920
    assert clip.editableFields == ["label", "startMs", "durationMs", "prompt"]

    loaded = service.get_project_timeline("project-workspace")
    assert loaded.timeline is not None
    loaded_clip = loaded.timeline.tracks[0].clips[0]
    assert loaded.saveState is not None
    assert loaded.saveState.source == "load"
    assert loaded_clip.prompt == "开场钩子"
    assert loaded_clip.resolution is not None
    assert loaded_clip.resolution.height == 1080


def test_fetch_clip_returns_detail_with_metadata(tmp_path: Path) -> None:
    service = _make_workspace_service(tmp_path)
    _create_timeline(service)

    clip = service.fetch_clip("clip-video-1")

    assert clip.id == "clip-video-1"
    assert clip.timelineId is not None
    assert clip.trackId == "track-video-1"
    assert clip.prompt == "开场钩子"
    assert clip.resolution is not None
    assert clip.resolution.width == 1920
    assert clip.editableFields == ["label", "startMs", "durationMs", "prompt"]


def test_move_clip_updates_timeline_atomically(tmp_path: Path) -> None:
    service = _make_workspace_service(tmp_path)
    _create_timeline(service)

    result = service.move_clip(
        "clip-video-1",
        {
            "targetTrackId": "track-audio-1",
            "startMs": 5200,
        },
    )

    assert result.timeline is not None
    moved_clip = result.timeline.tracks[1].clips[0]
    assert moved_clip.trackId == "track-audio-1"
    assert moved_clip.startMs == 5200
    assert result.timeline.tracks[0].clips == []
    assert result.saveState is not None
    assert result.saveState.source == "clip_move"


def test_move_clip_rejects_overlap_with_same_track_neighbor(tmp_path: Path) -> None:
    service = _make_workspace_service(tmp_path)
    _create_timeline_with_neighbor_clip(service)

    with pytest.raises(HTTPException) as exc_info:
        service.move_clip(
            "clip-video-1",
            {
                "targetTrackId": "track-video-1",
                "startMs": 4800,
            },
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "片段移动后会与同轨片段重叠。"


def test_trim_clip_updates_timeline_atomically(tmp_path: Path) -> None:
    service = _make_workspace_service(tmp_path)
    _create_timeline(service)

    result = service.trim_clip(
        "clip-video-1",
        {
            "startMs": 900,
            "durationMs": 3000,
            "inPointMs": 120,
            "outPointMs": 3120,
        },
    )

    assert result.timeline is not None
    clip = result.timeline.tracks[0].clips[0]
    assert clip.startMs == 900
    assert clip.durationMs == 3000
    assert clip.inPointMs == 120
    assert clip.outPointMs == 3120
    assert result.saveState is not None
    assert result.saveState.source == "clip_trim"


def test_trim_clip_rejects_duration_below_minimum(tmp_path: Path) -> None:
    service = _make_workspace_service(tmp_path)
    _create_timeline(service)

    with pytest.raises(HTTPException) as exc_info:
        service.trim_clip(
            "clip-video-1",
            {
                "durationMs": 200,
            },
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "片段裁剪后至少需要保留 500ms。"


def test_trim_clip_rejects_overlap_with_same_track_neighbor(tmp_path: Path) -> None:
    service = _make_workspace_service(tmp_path)
    _create_timeline_with_neighbor_clip(service)

    with pytest.raises(HTTPException) as exc_info:
        service.trim_clip(
            "clip-video-1",
            {
                "startMs": 0,
                "durationMs": 5500,
            },
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "片段裁剪后会与同轨片段重叠。"


def test_replace_clip_updates_source_metadata(tmp_path: Path) -> None:
    service = _make_workspace_service(tmp_path)
    _create_timeline(service)

    result = service.replace_clip(
        "clip-video-1",
        {
            "sourceType": "voice_track",
            "sourceId": "voice-track-1",
            "label": "新旁白",
            "prompt": "请使用更稳重的语气",
            "resolution": {"width": 1280, "height": 720},
            "editableFields": ["label", "prompt"],
        },
    )

    assert result.timeline is not None
    clip = result.timeline.tracks[0].clips[0]
    assert clip.sourceType == "voice_track"
    assert clip.sourceId == "voice-track-1"
    assert clip.label == "新旁白"
    assert clip.prompt == "请使用更稳重的语气"
    assert clip.resolution is not None
    assert clip.resolution.height == 720
    assert result.timeline.assetReferenceStatus is not None
    assert result.timeline.assetReferenceStatus.manualClips == 0
    assert result.timeline.assetReferenceStatus.referencedClips == 1
    assert result.saveState is not None
    assert result.saveState.source == "clip_replace"


def test_insert_video_asset_clip_at_requested_playhead(tmp_path: Path) -> None:
    service, asset_repository = _make_workspace_context(tmp_path)
    timeline_id = _create_timeline(service)
    _seed_asset(
        asset_repository,
        tmp_path,
        asset_id="asset-video-1",
        asset_type="video",
        name="暖光开场.mp4",
        file_name="warm-open.mp4",
        duration_ms=2600,
        metadata_json='{"resolution": {"width": 1080, "height": 1920}}',
    )

    result = service.insert_asset_clip(
        timeline_id,
        {
            "assetId": "asset-video-1",
            "targetTrackId": "track-video-1",
            "startMs": 4300,
        },
    )

    assert result.timeline is not None
    clip = result.timeline.tracks[0].clips[1]
    assert clip.id == "asset-asset-video-1-4300"
    assert clip.trackId == "track-video-1"
    assert clip.sourceType == "asset"
    assert clip.sourceId == "asset-video-1"
    assert clip.label == "暖光开场.mp4"
    assert clip.startMs == 4300
    assert clip.durationMs == 2600
    assert clip.resolution is not None
    assert clip.resolution.height == 1920
    assert set(clip.editableFields) >= {"label", "startMs", "durationMs"}
    assert result.saveState is not None
    assert result.saveState.source == "clip_insert_asset"


def test_insert_audio_asset_clip_defaults_to_track_end(tmp_path: Path) -> None:
    service, asset_repository = _make_workspace_context(tmp_path)
    timeline_id = _create_timeline_with_audio_clip(service)
    _seed_asset(
        asset_repository,
        tmp_path,
        asset_id="asset-audio-1",
        asset_type="audio",
        name="环境声.wav",
        file_name="room.wav",
        duration_ms=1200,
    )

    result = service.insert_asset_clip(
        timeline_id,
        {
            "assetId": "asset-audio-1",
        },
    )

    assert result.timeline is not None
    clip = result.timeline.tracks[1].clips[1]
    assert clip.id == "asset-asset-audio-1-3400"
    assert clip.trackId == "track-audio-1"
    assert clip.sourceType == "asset"
    assert clip.sourceId == "asset-audio-1"
    assert clip.startMs == 3400
    assert clip.durationMs == 1200


def test_insert_asset_clip_rejects_unavailable_file(tmp_path: Path) -> None:
    service, asset_repository = _make_workspace_context(tmp_path)
    timeline_id = _create_timeline(service)
    _seed_asset(
        asset_repository,
        tmp_path,
        asset_id="asset-missing-1",
        asset_type="video",
        name="丢失素材.mp4",
        file_name="missing.mp4",
        duration_ms=1000,
        create_file=False,
    )

    with pytest.raises(HTTPException) as exc_info:
        service.insert_asset_clip(
            timeline_id,
            {
                "assetId": "asset-missing-1",
                "targetTrackId": "track-video-1",
                "startMs": 4300,
            },
        )

    assert exc_info.value.status_code == 400
    assert "源文件" in str(exc_info.value.detail)


def test_replace_clip_with_video_asset_keeps_timing_and_updates_source(
    tmp_path: Path,
) -> None:
    service, asset_repository = _make_workspace_context(tmp_path)
    _create_timeline(service)
    _seed_asset(
        asset_repository,
        tmp_path,
        asset_id="asset-video-replace",
        asset_type="video",
        name="替换镜头.mp4",
        file_name="replace.mp4",
        duration_ms=8800,
        metadata_json='{"resolution": {"width": 1080, "height": 1920}}',
    )

    result = service.replace_clip(
        "clip-video-1",
        {
            "assetId": "asset-video-replace",
        },
    )

    assert result.timeline is not None
    clip = result.timeline.tracks[0].clips[0]
    assert clip.sourceType == "asset"
    assert clip.sourceId == "asset-video-replace"
    assert clip.label == "替换镜头.mp4"
    assert clip.startMs == 0
    assert clip.durationMs == 4200
    assert clip.resolution is not None
    assert clip.resolution.width == 1080
    assert set(clip.editableFields) >= {"label", "startMs", "durationMs"}
    assert result.saveState is not None
    assert result.saveState.source == "clip_replace"


def test_delete_clip_removes_clip_and_updates_save_state(tmp_path: Path) -> None:
    service = _make_workspace_service(tmp_path)
    _create_timeline(service)

    result = service.delete_clip("clip-video-1")

    assert result.timeline is not None
    assert result.timeline.tracks[0].clips == []
    assert result.timeline.version is not None
    assert result.timeline.version.clipCount == 0
    assert result.saveState is not None
    assert result.saveState.source == "clip_delete"


def test_split_clip_creates_continuous_pair(tmp_path: Path) -> None:
    service = _make_workspace_service(tmp_path)
    _create_timeline(service)

    result = service.split_clip("clip-video-1", {"splitAtMs": 1800})

    assert result.timeline is not None
    clips = result.timeline.tracks[0].clips
    assert [clip.id for clip in clips] == ["clip-video-1", "clip-video-1-split-1800"]
    assert clips[0].startMs == 0
    assert clips[0].durationMs == 1800
    assert clips[0].inPointMs == 0
    assert clips[0].outPointMs == 1800
    assert clips[1].startMs == 1800
    assert clips[1].durationMs == 2400
    assert clips[1].inPointMs == 1800
    assert clips[1].outPointMs == 4200
    assert result.saveState is not None
    assert result.saveState.source == "clip_split"


def test_split_clip_rejects_boundary_split(tmp_path: Path) -> None:
    service = _make_workspace_service(tmp_path)
    _create_timeline(service)

    with pytest.raises(HTTPException) as exc_info:
        service.split_clip("clip-video-1", {"splitAtMs": 0})

    assert exc_info.value.status_code == 400
    assert "片段内部" in str(exc_info.value.detail)


def test_preview_returns_local_summary_from_real_timeline(tmp_path: Path) -> None:
    service = _make_workspace_service(tmp_path)
    timeline_id = _create_timeline(service)

    result = service.fetch_timeline_preview(timeline_id)

    assert result.status == "structure_only"
    assert "已生成" in result.message
    assert result.previewUrl is not None
    assert result.previewMode == "manifest"
    assert result.media is None
    assert result.error is None


def test_preview_manifest_total_duration_uses_timeline_end_for_parallel_tracks(tmp_path: Path) -> None:
    service = _make_workspace_service(tmp_path)
    timeline_id = _create_timeline_with_audio_clip(service)

    result = service.fetch_timeline_preview(timeline_id)

    assert result.previewUrl is not None
    _, encoded_payload = result.previewUrl.split(",", 1)
    preview_payload = json.loads(unquote(encoded_payload))
    assert preview_payload["clipCount"] == 2
    assert preview_payload["tracks"][0]["clipDurationMs"] == 4200
    assert preview_payload["tracks"][1]["clipDurationMs"] == 2400
    assert preview_payload["totalClipDurationMs"] == 4200


def test_preview_returns_registered_asset_media_without_local_path(tmp_path: Path) -> None:
    service, asset_repository = _make_workspace_context(tmp_path)
    timeline_id = _create_timeline(service)
    _seed_asset(
        asset_repository,
        tmp_path,
        asset_id="asset-video-preview",
        asset_type="video",
        name="预览素材.mp4",
        file_name="preview.mp4",
        duration_ms=2600,
    )
    service.insert_asset_clip(
        timeline_id,
        {
            "assetId": "asset-video-preview",
            "targetTrackId": "track-video-1",
            "startMs": 4300,
        },
    )

    result = service.fetch_timeline_preview(timeline_id)

    assert result.status == "ready"
    assert result.previewMode == "media"
    assert result.previewUrl is not None
    assert result.media is not None
    assert result.media.kind == "video"
    assert result.media.mimeType == "video/mp4"
    assert result.media.durationMs == 2600
    assert result.media.url.startswith("/api/assets/asset-video-preview/media?token=")
    assert result.media.source == "asset:asset-video-preview"
    assert str(tmp_path) not in result.media.url
    assert result.error is None


def test_preview_returns_media_for_requested_asset_clip(tmp_path: Path) -> None:
    service, asset_repository = _make_workspace_context(tmp_path)
    created = service.create_project_timeline(
        "project-workspace",
        TimelineCreateInput(name="主时间线"),
    )
    assert created.timeline is not None
    _seed_asset(
        asset_repository,
        tmp_path,
        asset_id="asset-first-preview",
        asset_type="video",
        name="第一个素材.mp4",
        file_name="first-preview.mp4",
        duration_ms=2000,
    )
    _seed_asset(
        asset_repository,
        tmp_path,
        asset_id="asset-second-preview",
        asset_type="video",
        name="第二个素材.mp4",
        file_name="second-preview.mp4",
        duration_ms=3200,
    )
    service.update_timeline(
        created.timeline.id,
        TimelineUpdateInput(
            name="主时间线",
            durationSeconds=8,
            tracks=[
                {
                    "id": "track-video-1",
                    "kind": "video",
                    "name": "视频轨 1",
                    "orderIndex": 0,
                    "locked": False,
                    "muted": False,
                    "clips": [
                        {
                            "id": "clip-first-media",
                            "trackId": "track-video-1",
                            "sourceType": "asset",
                            "sourceId": "asset-first-preview",
                            "label": "第一个素材",
                            "startMs": 0,
                            "durationMs": 2000,
                            "inPointMs": 0,
                            "outPointMs": 2000,
                            "status": "ready",
                        },
                        {
                            "id": "clip-second-media",
                            "trackId": "track-video-1",
                            "sourceType": "asset",
                            "sourceId": "asset-second-preview",
                            "label": "第二个素材",
                            "startMs": 2000,
                            "durationMs": 3200,
                            "inPointMs": 0,
                            "outPointMs": 3200,
                            "status": "ready",
                        },
                    ],
                }
            ],
        ),
    )

    result = service.fetch_timeline_preview(created.timeline.id, clip_id="clip-second-media")

    assert result.previewMode == "media"
    assert result.media is not None
    assert result.media.source == "asset:asset-second-preview"
    assert result.media.durationMs == 3200
    assert "asset-second-preview" in result.media.url


def test_preview_marks_missing_asset_media_unavailable_but_keeps_manifest(tmp_path: Path) -> None:
    service, asset_repository = _make_workspace_context(tmp_path)
    created = service.create_project_timeline(
        "project-workspace",
        TimelineCreateInput(name="主时间线"),
    )
    assert created.timeline is not None
    _seed_asset(
        asset_repository,
        tmp_path,
        asset_id="asset-missing-preview",
        asset_type="video",
        name="缺失预览素材.mp4",
        file_name="missing-preview.mp4",
        duration_ms=3200,
        create_file=False,
    )
    service.update_timeline(
        created.timeline.id,
        TimelineUpdateInput(
            name="主时间线",
            durationSeconds=8,
            tracks=[
                {
                    "id": "track-video-1",
                    "kind": "video",
                    "name": "视频轨 1",
                    "orderIndex": 0,
                    "locked": False,
                    "muted": False,
                    "clips": [
                        {
                            "id": "clip-missing-media",
                            "trackId": "track-video-1",
                            "sourceType": "asset",
                            "sourceId": "asset-missing-preview",
                            "label": "缺失预览素材",
                            "startMs": 0,
                            "durationMs": 3200,
                            "inPointMs": 0,
                            "outPointMs": 3200,
                            "status": "ready",
                        }
                    ],
                }
            ],
        ),
    )

    result = service.fetch_timeline_preview(created.timeline.id)

    assert result.status == "unavailable"
    assert result.previewMode == "unavailable"
    assert result.previewUrl is not None
    assert result.media is None
    assert result.error is not None
    assert result.error.code == "preview.asset_file_missing"
    assert "源文件不可用" in result.error.message


def test_preview_prioritizes_missing_asset_over_later_playable_media(tmp_path: Path) -> None:
    service, asset_repository = _make_workspace_context(tmp_path)
    created = service.create_project_timeline(
        "project-workspace",
        TimelineCreateInput(name="主时间线"),
    )
    assert created.timeline is not None
    _seed_asset(
        asset_repository,
        tmp_path,
        asset_id="asset-mixed-missing-preview",
        asset_type="video",
        name="缺失预览素材.mp4",
        file_name="mixed-missing-preview.mp4",
        duration_ms=2000,
        create_file=False,
    )
    _seed_asset(
        asset_repository,
        tmp_path,
        asset_id="asset-mixed-ready-preview",
        asset_type="video",
        name="可播放预览素材.mp4",
        file_name="mixed-ready-preview.mp4",
        duration_ms=2400,
    )
    service.update_timeline(
        created.timeline.id,
        TimelineUpdateInput(
            name="主时间线",
            durationSeconds=6,
            tracks=[
                {
                    "id": "track-video-1",
                    "kind": "video",
                    "name": "视频轨 1",
                    "orderIndex": 0,
                    "locked": False,
                    "muted": False,
                    "clips": [
                        {
                            "id": "clip-mixed-missing-media",
                            "trackId": "track-video-1",
                            "sourceType": "asset",
                            "sourceId": "asset-mixed-missing-preview",
                            "label": "缺失预览素材",
                            "startMs": 0,
                            "durationMs": 2000,
                            "inPointMs": 0,
                            "outPointMs": 2000,
                            "status": "ready",
                        },
                        {
                            "id": "clip-mixed-ready-media",
                            "trackId": "track-video-1",
                            "sourceType": "asset",
                            "sourceId": "asset-mixed-ready-preview",
                            "label": "可播放预览素材",
                            "startMs": 2000,
                            "durationMs": 2400,
                            "inPointMs": 0,
                            "outPointMs": 2400,
                            "status": "ready",
                        },
                    ],
                }
            ],
        ),
    )

    result = service.fetch_timeline_preview(created.timeline.id)

    assert result.status == "unavailable"
    assert result.previewMode == "unavailable"
    assert result.media is None
    assert result.error is not None
    assert result.error.code == "preview.asset_file_missing"


def test_precheck_returns_ready_for_valid_timeline(tmp_path: Path) -> None:
    service = _make_workspace_service(tmp_path)
    timeline_id = _create_timeline(service)

    result = service.precheck_timeline(timeline_id)

    assert result.status == "ready"
    assert result.issues == []
    assert result.issueDetails == []
    assert "通过" in result.message


def test_precheck_returns_structured_issue_details_for_clip_track_and_timeline(
    tmp_path: Path,
) -> None:
    service = _make_workspace_service(tmp_path)
    created = service.create_project_timeline(
        "project-workspace",
        TimelineCreateInput(name="主时间线"),
    )
    assert created.timeline is not None

    service._repository.update_timeline(  # noqa: SLF001
        created.timeline.id,
        name=None,
        duration_seconds=12,
        tracks_json=json.dumps(
            [
                {
                    "id": "track-video-invalid",
                    "kind": "video",
                    "name": "问题视频轨",
                    "orderIndex": 0,
                    "clips": [
                        {
                            "id": "clip-zero-duration",
                            "trackId": "track-video-invalid",
                            "sourceType": "manual",
                            "label": "零时长片段",
                            "startMs": 0,
                            "durationMs": 0,
                        },
                        {
                            "id": "clip-negative-start",
                            "trackId": "track-video-invalid",
                            "sourceType": "manual",
                            "label": "负起点片段",
                            "startMs": -10,
                            "durationMs": 1200,
                        },
                    ],
                },
                {
                    "id": "track-effect",
                    "kind": "effect",
                    "name": "特效轨",
                    "orderIndex": 1,
                    "clips": [],
                },
                {
                    "id": "track-broken-clips",
                    "kind": "video",
                    "name": "损坏轨",
                    "orderIndex": 2,
                    "clips": "bad",
                },
            ],
            ensure_ascii=False,
        ),
    )

    result = service.precheck_timeline(created.timeline.id)

    assert result.status == "warning"
    assert result.issues == [issue.message for issue in result.issueDetails]

    zero_duration_issue = next(
        issue for issue in result.issueDetails if issue.id == "clip-zero-duration-duration"
    )
    assert zero_duration_issue.targetType == "clip"
    assert zero_duration_issue.clipId == "clip-zero-duration"
    assert zero_duration_issue.trackId == "track-video-invalid"
    assert zero_duration_issue.message == "片段 零时长片段 的时长无效。"

    negative_start_issue = next(
        issue for issue in result.issueDetails if issue.id == "clip-negative-start-start"
    )
    assert negative_start_issue.targetType == "clip"
    assert negative_start_issue.clipId == "clip-negative-start"
    assert negative_start_issue.trackId == "track-video-invalid"

    unsupported_track_issue = next(
        issue for issue in result.issueDetails if issue.id == "track-track-effect-kind"
    )
    assert unsupported_track_issue.targetType == "track"
    assert unsupported_track_issue.targetId == "track-effect"
    assert unsupported_track_issue.trackId == "track-effect"

    clips_format_issue = next(
        issue for issue in result.issueDetails if issue.id == "track-track-broken-clips-clips"
    )
    assert clips_format_issue.targetType == "track"
    assert clips_format_issue.trackId == "track-broken-clips"


def test_precheck_returns_timeline_issue_detail_for_empty_tracks(tmp_path: Path) -> None:
    service = _make_workspace_service(tmp_path)
    created = service.create_project_timeline(
        "project-workspace",
        TimelineCreateInput(name="主时间线"),
    )
    assert created.timeline is not None

    result = service.precheck_timeline(created.timeline.id)

    assert result.status == "warning"
    assert result.issues == ["时间线尚未配置轨道，无法生成本地预检结果。"]
    assert len(result.issueDetails) == 1
    assert result.issueDetails[0].targetType == "timeline"
    assert result.issueDetails[0].targetId == created.timeline.id


def test_get_project_timeline_exposes_active_task_feedback(
    tmp_path: Path,
) -> None:
    task_manager = TaskManager()
    service = _make_workspace_service(tmp_path, task_manager=task_manager)

    async def _assert_active_task() -> None:
        timeline_id = _create_timeline(service)

        async def _long_running_task(progress_callback) -> None:
            await progress_callback(35, "正在分析时间线。")
            await asyncio.sleep(0.2)

        task = task_manager.submit(
            task_type="ai-workspace-command",
            coro_factory=_long_running_task,
            project_id="project-workspace",
        )
        task.owner_ref = {"kind": "timeline", "id": timeline_id}
        task.message = "AI 命令已进入任务队列。"

        result = service.get_project_timeline("project-workspace")

        assert result.activeTask is not None
        assert result.activeTask.id == task.id
        assert result.activeTask.taskType == "ai-workspace-command"
        assert result.activeTask.status in {"queued", "running"}

        task_manager.cancel(task.id)
        await asyncio.sleep(0)

    asyncio.run(_assert_active_task())


def test_run_ai_command_returns_real_taskbus_task(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _make_workspace_service(tmp_path, task_manager=TaskManager())
    timeline_id = _create_timeline(service)
    broadcast = AsyncMock()
    monkeypatch.setattr(task_manager_module.ws_manager, "broadcast", broadcast)

    async def _wait_for_completion() -> None:
        result = service.run_ai_command(
            "project-workspace",
            WorkspaceAICommandInput(
                timelineId=timeline_id,
                capabilityId="timeline_analysis",
                parameters={"selectedClipId": "clip-video-1"},
            ),
        )

        assert result.status == "queued"
        assert result.task is not None
        assert result.task["kind"] == "ai-workspace-command"
        assert result.task["projectId"] == "project-workspace"
        assert result.task["ownerRef"] == {"kind": "timeline", "id": timeline_id}

        for _ in range(50):
            task = service._task_manager.get(result.task["id"])  # type: ignore[attr-defined]
            if task is not None and task.status == "succeeded":
                break
            await asyncio.sleep(0.01)

        task = service._task_manager.get(result.task["id"])  # type: ignore[attr-defined]
        assert task is not None
        assert task.status == "succeeded"
        assert [call.args[0]["type"] for call in broadcast.await_args_list] == [
            "task.started",
            "task.progress",
            "task.completed",
        ]

    asyncio.run(_wait_for_completion())


def test_run_magic_cut_blocks_when_ai_text_generation_service_missing(
    tmp_path: Path,
) -> None:
    task_manager = TaskManager()
    service = _make_workspace_service(
        tmp_path,
        task_manager=task_manager,
        ai_text_generation_service=None,
    )
    timeline_id = _create_timeline(service)

    result = service.run_ai_command(
        "project-workspace",
        WorkspaceAICommandInput(
            timelineId=timeline_id,
            capabilityId="magic_cut",
            parameters={"selectedClipId": "clip-video-1"},
        ),
    )

    assert result.status == "blocked"
    assert result.task is None
    assert result.message == "智能粗剪 Provider 未配置，请先选择可用文本模型。"
    assert task_manager._tasks == {}  # noqa: SLF001


def test_run_magic_cut_returns_blocked_before_task_when_capability_disabled(
    tmp_path: Path,
) -> None:
    class DisabledMagicCutService:
        def validate_text_generation_ready(self, capability_id: str) -> None:
            assert capability_id == "magic_cut"
            from ai.providers.errors import ProviderHTTPException

            raise ProviderHTTPException(
                status_code=400,
                detail="当前 AI 能力已停用。",
                error_code="ai_capability_disabled",
            )

        def generate_text(self, *args, **kwargs):  # pragma: no cover - 该测试要求不会进入后台调用
            raise AssertionError("停用能力不应进入后台 AI 调用")

    service = _make_workspace_service(
        tmp_path,
        task_manager=TaskManager(),
        ai_text_generation_service=DisabledMagicCutService(),
    )
    timeline_id = _create_timeline(service)

    result = service.run_ai_command(
        "project-workspace",
        WorkspaceAICommandInput(
            timelineId=timeline_id,
            capabilityId="magic_cut",
            parameters={"selectedClipId": "clip-video-1"},
        ),
    )

    assert result.status == "blocked"
    assert result.task is None
    assert result.message == "智能粗剪能力未启用，请先在 AI 与系统设置中启用并保存。"


def test_run_magic_cut_returns_blocked_before_task_when_provider_secret_missing(
    tmp_path: Path,
) -> None:
    class MissingSecretMagicCutService:
        def validate_text_generation_ready(self, capability_id: str) -> None:
            assert capability_id == "magic_cut"
            from ai.providers.errors import ProviderHTTPException

            raise ProviderHTTPException(
                status_code=400,
                detail="Provider API Key 尚未配置。",
                error_code="ai_provider_not_configured",
            )

        def generate_text(self, *args, **kwargs):  # pragma: no cover - 该测试要求不会进入后台调用
            raise AssertionError("缺少密钥时不应进入后台 AI 调用")

    service = _make_workspace_service(
        tmp_path,
        task_manager=TaskManager(),
        ai_text_generation_service=MissingSecretMagicCutService(),
    )
    timeline_id = _create_timeline(service)

    result = service.run_ai_command(
        "project-workspace",
        WorkspaceAICommandInput(
            timelineId=timeline_id,
            capabilityId="magic_cut",
            parameters={"selectedClipId": "clip-video-1"},
        ),
    )

    assert result.status == "blocked"
    assert result.task is None
    assert result.message == "智能粗剪 Provider 密钥缺失，请先完成密钥配置。"


def test_run_magic_cut_returns_blocked_before_task_when_provider_unsupported(
    tmp_path: Path,
) -> None:
    class UnsupportedProviderMagicCutService:
        def validate_text_generation_ready(self, capability_id: str) -> None:
            assert capability_id == "magic_cut"
            from ai.providers.errors import ProviderHTTPException

            raise ProviderHTTPException(
                status_code=400,
                detail="当前 Provider 尚未接入文本生成。",
                error_code="ai_provider_unsupported",
            )

        def generate_text(self, *args, **kwargs):  # pragma: no cover - 该测试要求不会进入后台调用
            raise AssertionError("Provider 不支持时不应进入后台 AI 调用")

    service = _make_workspace_service(
        tmp_path,
        task_manager=TaskManager(),
        ai_text_generation_service=UnsupportedProviderMagicCutService(),
    )
    timeline_id = _create_timeline(service)

    result = service.run_ai_command(
        "project-workspace",
        WorkspaceAICommandInput(
            timelineId=timeline_id,
            capabilityId="magic_cut",
            parameters={"selectedClipId": "clip-video-1"},
        ),
    )

    assert result.status == "blocked"
    assert result.task is None
    assert result.message == "智能粗剪 Provider 未配置，请先选择可用文本模型。"


def test_run_magic_cut_returns_blocked_before_task_when_model_unsupported(
    tmp_path: Path,
) -> None:
    class UnsupportedModelMagicCutService:
        def validate_text_generation_ready(self, capability_id: str) -> None:
            assert capability_id == "magic_cut"
            from ai.providers.errors import ProviderHTTPException

            raise ProviderHTTPException(
                status_code=400,
                detail="当前模型不支持智能粗剪所需的文本生成能力，请更换模型。",
                error_code="ai_model_unsupported",
            )

        def generate_text(self, *args, **kwargs):  # pragma: no cover - 该测试要求不会进入后台调用
            raise AssertionError("模型不支持时不应进入后台 AI 调用")

    service = _make_workspace_service(
        tmp_path,
        task_manager=TaskManager(),
        ai_text_generation_service=UnsupportedModelMagicCutService(),
    )
    timeline_id = _create_timeline(service)

    result = service.run_ai_command(
        "project-workspace",
        WorkspaceAICommandInput(
            timelineId=timeline_id,
            capabilityId="magic_cut",
            parameters={"selectedClipId": "clip-video-1"},
        ),
    )

    assert result.status == "blocked"
    assert result.task is None
    assert result.message == "当前模型不支持智能粗剪所需的文本生成能力，请更换模型。"


def test_run_magic_cut_applies_ai_operations_and_persists_timeline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class SuccessfulMagicCutService:
        def __init__(self) -> None:
            self.calls: list[tuple[str, dict[str, str], dict[str, object]]] = []

        def validate_text_generation_ready(self, capability_id: str) -> None:
            assert capability_id == "magic_cut"

        def generate_text(self, capability_id: str, variables: dict[str, str], **kwargs: object):
            assert capability_id == "magic_cut"
            timeline_context = json.loads(variables["timeline_context"])
            assert timeline_context[0]["clips"][0]["id"] == "clip-video-1"
            assert timeline_context[0]["clips"][1]["id"] == "clip-video-2"
            assert "clip-video-1" in variables["instruction"]
            self.calls.append((capability_id, variables, kwargs))

            class Result:
                text = json.dumps(
                    {
                        "summary": "已压缩开场并消除视频轨空隙。",
                        "operations": [
                            {
                                "action": "trim",
                                "clipId": "clip-video-1",
                                "startMs": 0,
                                "durationMs": 3000,
                            },
                            {
                                "action": "move",
                                "clipId": "clip-video-2",
                                "targetTrackId": "track-video-1",
                                "startMs": 3000,
                            },
                        ],
                    },
                    ensure_ascii=False,
                )

            return Result()

    ai_service = SuccessfulMagicCutService()
    service = _make_workspace_service(
        tmp_path,
        task_manager=TaskManager(),
        ai_text_generation_service=ai_service,
    )
    timeline_id = _create_timeline_with_neighbor_clip(service)
    broadcast = AsyncMock()
    monkeypatch.setattr(task_manager_module.ws_manager, "broadcast", broadcast)

    async def _wait_for_success() -> None:
        result = service.run_ai_command(
            "project-workspace",
            WorkspaceAICommandInput(
                timelineId=timeline_id,
                capabilityId="magic_cut",
                parameters={"selectedClipId": "clip-video-1"},
            ),
        )

        assert result.status == "queued"
        assert result.task is not None

        for _ in range(100):
            task = service._task_manager.get(result.task["id"])  # type: ignore[attr-defined]
            if task is not None and task.status == "succeeded":
                break
            await asyncio.sleep(0.01)

        task = service._task_manager.get(result.task["id"])  # type: ignore[attr-defined]
        assert task is not None
        assert task.status == "succeeded"

        refreshed = service.get_project_timeline("project-workspace")
        assert refreshed.timeline is not None
        video_track = next(track for track in refreshed.timeline.tracks if track.id == "track-video-1")

        assert [clip.id for clip in video_track.clips] == [
            "clip-video-1",
            "clip-video-2",
        ]
        assert [(clip.startMs, clip.durationMs, clip.inPointMs, clip.outPointMs) for clip in video_track.clips] == [
            (0, 3000, 0, None),
            (3000, 2000, 0, None),
        ]
        assert video_track.clips[0].startMs + video_track.clips[0].durationMs == video_track.clips[1].startMs
        assert refreshed.timeline.version is not None
        assert refreshed.timeline.version.clipCount == 2
        assert refreshed.activeTask is None
        assert ai_service.calls[0][2]["project_id"] == "project-workspace"
        assert "task.completed" in [call.args[0]["type"] for call in broadcast.await_args_list]

    asyncio.run(_wait_for_success())


def test_magic_cut_operations_are_scoped_to_requested_timeline(tmp_path: Path) -> None:
    service = _make_workspace_service(tmp_path)

    target = service.create_project_timeline(
        "project-workspace",
        TimelineCreateInput(name="目标时间线"),
    )
    assert target.timeline is not None
    target = service.update_timeline(
        target.timeline.id,
        TimelineUpdateInput(
            name="目标时间线",
            durationSeconds=12,
            tracks=_timeline_payload_with_neighbor_clip(),
        ),
    )
    assert target.timeline is not None

    decoy = service.create_project_timeline(
        "project-workspace",
        TimelineCreateInput(name="干扰时间线"),
    )
    assert decoy.timeline is not None
    decoy = service.update_timeline(
        decoy.timeline.id,
        TimelineUpdateInput(
            name="干扰时间线",
            durationSeconds=12,
            tracks=_timeline_payload_with_neighbor_clip(),
        ),
    )
    assert decoy.timeline is not None

    from services.magic_cut import apply_magic_cut_operations

    applied, failed, _ = apply_magic_cut_operations(
        service,
        target.timeline.id,
        [
            {
                "action": "trim",
                "clipId": "clip-video-1",
                "startMs": 0,
                "durationMs": 3000,
            }
        ],
    )

    assert (applied, failed) == (1, 0)

    target_after = json.loads(service._load_timeline(target.timeline.id).tracks_json)  # noqa: SLF001
    decoy_after = json.loads(service._load_timeline(decoy.timeline.id).tracks_json)  # noqa: SLF001
    assert target_after[0]["clips"][0]["durationMs"] == 3000
    assert decoy_after[0]["clips"][0]["durationMs"] == 4200


def test_run_magic_cut_fails_when_all_operations_fail(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class InvalidOperationMagicCutService:
        def validate_text_generation_ready(self, capability_id: str) -> None:
            assert capability_id == "magic_cut"

        def generate_text(self, capability_id: str, variables: dict[str, str], **kwargs: object):
            assert capability_id == "magic_cut"

            class Result:
                text = json.dumps(
                    {
                        "summary": "尝试处理不存在的片段。",
                        "operations": [
                            {
                                "action": "trim",
                                "clipId": "clip-missing",
                                "startMs": 0,
                                "durationMs": 3000,
                            }
                        ],
                    },
                    ensure_ascii=False,
                )

            return Result()

    service = _make_workspace_service(
        tmp_path,
        task_manager=TaskManager(),
        ai_text_generation_service=InvalidOperationMagicCutService(),
    )
    timeline_id = _create_timeline(service)
    broadcast = AsyncMock()
    monkeypatch.setattr(task_manager_module.ws_manager, "broadcast", broadcast)

    async def _wait_for_failure() -> None:
        result = service.run_ai_command(
            "project-workspace",
            WorkspaceAICommandInput(
                timelineId=timeline_id,
                capabilityId="magic_cut",
                parameters={"selectedClipId": "clip-video-1"},
            ),
        )

        assert result.status == "queued"
        assert result.task is not None

        for _ in range(100):
            task = service._task_manager.get(result.task["id"])  # type: ignore[attr-defined]
            if task is not None and task.status == "failed":
                break
            await asyncio.sleep(0.01)

        task = service._task_manager.get(result.task["id"])  # type: ignore[attr-defined]
        assert task is not None
        assert task.status == "failed"
        assert task.message == "智能粗剪执行失败，请查看日志后重试。"
        assert "task.failed" in [call.args[0]["type"] for call in broadcast.await_args_list]

        refreshed = service.get_project_timeline("project-workspace")
        assert refreshed.timeline is not None
        video_track = next(track for track in refreshed.timeline.tracks if track.id == "track-video-1")
        assert [(clip.id, clip.startMs, clip.durationMs) for clip in video_track.clips] == [
            ("clip-video-1", 0, 4200)
        ]

    asyncio.run(_wait_for_failure())


def test_run_magic_cut_masks_unknown_provider_failure_in_task_message(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    raw_provider_error = "raw provider 401 invalid_api_key secret=should-not-leak"
    caplog.set_level(logging.WARNING)

    class RuntimeProviderFailureService:
        def validate_text_generation_ready(self, capability_id: str) -> None:
            assert capability_id == "magic_cut"

        def generate_text(self, *args, **kwargs):
            from ai.providers.errors import ProviderHTTPException

            raise ProviderHTTPException(
                status_code=502,
                detail=raw_provider_error,
                error_code="ai_provider_server_error",
            )

    service = _make_workspace_service(
        tmp_path,
        task_manager=TaskManager(),
        ai_text_generation_service=RuntimeProviderFailureService(),
    )
    timeline_id = _create_timeline(service)
    broadcast = AsyncMock()
    monkeypatch.setattr(task_manager_module.ws_manager, "broadcast", broadcast)

    async def _wait_for_failure() -> None:
        result = service.run_ai_command(
            "project-workspace",
            WorkspaceAICommandInput(
                timelineId=timeline_id,
                capabilityId="magic_cut",
                parameters={"selectedClipId": "clip-video-1"},
            ),
        )

        assert result.status == "queued"
        assert result.task is not None
        for _ in range(50):
            task = service._task_manager.get(result.task["id"])  # type: ignore[attr-defined]
            if task is not None and task.status == "failed":
                break
            await asyncio.sleep(0.01)

        task = service._task_manager.get(result.task["id"])  # type: ignore[attr-defined]
        assert task is not None
        assert task.status == "failed"
        assert raw_provider_error not in task.message
        assert "invalid_api_key" not in task.message
        assert "智能粗剪 AI 调用失败，请检查 Provider 配置或稍后重试。" in task.message
        for call in broadcast.await_args_list:
            assert raw_provider_error not in call.args[0]["message"]
            assert "invalid_api_key" not in call.args[0]["message"]

        log_output = "\n".join(record.getMessage() for record in caplog.records)
        assert raw_provider_error not in log_output
        assert "secret=should-not-leak" not in log_output

    asyncio.run(_wait_for_failure())
