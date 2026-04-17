from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from schemas.ai_capabilities import AICapabilityConfigDto


def test_dashboard_service_can_clear_current_project(runtime_app) -> None:
    service = runtime_app.state.dashboard_service

    created = service.create_project(name="Dashboard Project", description="clear context")
    selected = service.set_current_project(created.id)

    assert selected.projectId == created.id

    cleared = service.set_current_project(None)

    assert cleared is None
    assert service.get_current_project() is None


def test_settings_service_broadcasts_config_changed(runtime_app, monkeypatch: pytest.MonkeyPatch) -> None:
    from services import settings_service as settings_service_module

    broadcast = AsyncMock()
    monkeypatch.setattr(settings_service_module.ws_manager, "broadcast", broadcast)

    service = runtime_app.state.settings_service
    current = service.get_settings()
    updated = service.update_settings(
        current.model_copy(
            update={
                "logging": current.logging.model_copy(update={"level": "DEBUG"}),
            }
        )
    )

    assert updated.logging.level == "DEBUG"
    assert broadcast.await_count == 1
    message = broadcast.await_args.args[0]
    assert message["type"] == "config.changed"
    assert message["payload"]["changedKeys"] == ["logging.level"]


def test_ai_capability_service_broadcasts_capability_change(
    runtime_app,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from services import ai_capability_service as ai_capability_service_module

    broadcast = AsyncMock()
    monkeypatch.setattr(ai_capability_service_module.ws_manager, "broadcast", broadcast)

    service = runtime_app.state.ai_capability_service
    settings = service.get_settings()
    updated = [
        item.model_copy(update={"enabled": not item.enabled})
        if item.capabilityId == "script_generation"
        else item
        for item in settings.capabilities
    ]

    next_settings = service.update_capabilities(updated)

    assert next_settings.capabilities[0].enabled is False
    assert broadcast.await_count == 1
    message = broadcast.await_args.args[0]
    assert message["type"] == "ai-capability.changed"
    assert message["payload"]["capabilityIds"] == ["script_generation"]


def test_task_manager_tracks_extended_task_shape_and_filters() -> None:
    from services.task_manager import TaskInfo, TaskManager

    manager = TaskManager()
    task = TaskInfo(
        id="task-1",
        kind="video-import",
        label="导入视频",
        status="running",
        progress_pct=10,
        started_at="2026-04-17T08:00:00Z",
        finished_at=None,
        eta_ms=1000,
        project_id="project-1",
        owner_ref={"kind": "imported-video", "id": "video-1"},
        error_code=None,
        error_message=None,
        retryable=False,
        created_at="2026-04-17T08:00:00Z",
        updated_at="2026-04-17T08:00:01Z",
        task_type="video-import",
        progress=10,
        message="导入中",
    )
    manager._tasks[task.id] = task

    running_tasks = manager.list_tasks(kind="video-import", statuses={"running"})

    assert [item.to_dict() for item in running_tasks] == [
        {
            "id": "task-1",
            "kind": "video-import",
            "label": "导入视频",
            "status": "running",
            "progressPct": 10,
            "startedAt": "2026-04-17T08:00:00Z",
            "finishedAt": None,
            "etaMs": 1000,
            "projectId": "project-1",
            "ownerRef": {"kind": "imported-video", "id": "video-1"},
            "errorCode": None,
            "errorMessage": None,
            "retryable": False,
            "createdAt": "2026-04-17T08:00:00Z",
            "updatedAt": "2026-04-17T08:00:01Z",
        }
    ]
