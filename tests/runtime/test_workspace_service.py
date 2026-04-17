from __future__ import annotations

from pathlib import Path

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
from services.workspace_service import WorkspaceService


def _make_workspace_service(tmp_path: Path) -> WorkspaceService:
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
    return WorkspaceService(repository)


def test_get_project_timeline_returns_empty_state(tmp_path: Path) -> None:
    service = _make_workspace_service(tmp_path)

    result = service.get_project_timeline("project-workspace")

    assert result.timeline is None
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


def test_update_timeline_persists_track_json(tmp_path: Path) -> None:
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
            tracks=[
                {
                    "id": "track-video-1",
                    "kind": "video",
                    "name": "视频轨 1",
                    "orderIndex": 0,
                    "locked": False,
                    "muted": False,
                    "clips": [],
                }
            ],
        ),
    )

    assert updated.timeline is not None
    assert updated.timeline.durationSeconds == 12
    assert updated.timeline.tracks[0].kind == "video"

    loaded = service.get_project_timeline("project-workspace")
    assert loaded.timeline is not None
    assert loaded.timeline.tracks[0].name == "视频轨 1"


def test_update_timeline_rejects_unknown_track_kind(tmp_path: Path) -> None:
    service = _make_workspace_service(tmp_path)
    created = service.create_project_timeline(
        "project-workspace",
        TimelineCreateInput(name="主时间线"),
    )
    assert created.timeline is not None

    with pytest.raises(HTTPException) as exc_info:
        service.update_timeline(
            created.timeline.id,
            TimelineUpdateInput(
                tracks=[
                    {
                        "id": "track-unknown",
                        "kind": "effect",
                        "name": "特效轨",
                        "orderIndex": 0,
                        "locked": False,
                        "muted": False,
                        "clips": [],
                    }
                ],
            ),
        )

    assert exc_info.value.status_code == 400
    assert "时间线轨道类型不支持" in str(exc_info.value.detail)


def test_run_ai_command_returns_blocked_without_fake_task(tmp_path: Path) -> None:
    service = _make_workspace_service(tmp_path)

    result = service.run_ai_command(
        "project-workspace",
        WorkspaceAICommandInput(
            timelineId="timeline-1",
            capabilityId="magic_cut",
            parameters={"selectedClipId": "clip-1"},
        ),
    )

    assert result.status == "blocked"
    assert result.task is None
    assert "尚未接入" in result.message
