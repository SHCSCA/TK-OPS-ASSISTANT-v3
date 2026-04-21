from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from common.time import utc_now_iso
from domain.models import Base, Project
from persistence.engine import create_runtime_engine, create_session_factory
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
) -> WorkspaceService:
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
    return WorkspaceService(repository, task_manager=task_manager)


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


def test_preview_returns_local_summary_from_real_timeline(tmp_path: Path) -> None:
    service = _make_workspace_service(tmp_path)
    timeline_id = _create_timeline(service)

    result = service.fetch_timeline_preview(timeline_id)

    assert result.status == "ready"
    assert "已生成" in result.message
    assert result.previewUrl is not None


def test_precheck_returns_ready_for_valid_timeline(tmp_path: Path) -> None:
    service = _make_workspace_service(tmp_path)
    timeline_id = _create_timeline(service)

    result = service.precheck_timeline(timeline_id)

    assert result.status == "ready"
    assert result.issues == []
    assert "通过" in result.message


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
                capabilityId="magic_cut",
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
