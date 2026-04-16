from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

from services.ws_manager import ConnectionManager

pytestmark = pytest.mark.asyncio


async def test_task_manager_broadcasts_lifecycle_events(monkeypatch: pytest.MonkeyPatch) -> None:
    from services import task_manager as task_manager_module

    broadcast = AsyncMock()
    monkeypatch.setattr(task_manager_module.ws_manager, "broadcast", broadcast)
    manager = task_manager_module.TaskManager()

    async def sample_task(progress_callback):
        await progress_callback(45, "正在处理第 3 段")
        return None

    info = manager.submit(
        task_type="tts_generation",
        coro_factory=sample_task,
        project_id="project-1",
    )

    for _ in range(20):
        if manager.get(info.id).status == "succeeded":
            break
        await asyncio.sleep(0.01)

    result = manager.get(info.id)
    assert result is not None
    assert result.status == "succeeded"
    assert result.progress == 100
    assert result.message == "任务已完成"

    event_types = [call.args[0]["type"] for call in broadcast.await_args_list]
    assert event_types == ["task.started", "task.progress", "task.completed"]
    progress_event = broadcast.await_args_list[1].args[0]
    assert progress_event["schema_version"] == 1
    assert progress_event["taskId"] == info.id
    assert progress_event["taskType"] == "tts_generation"
    assert progress_event["projectId"] == "project-1"
    assert progress_event["status"] == "running"
    assert progress_event["progress"] == 45
    assert progress_event["message"] == "正在处理第 3 段"


async def test_task_manager_uses_provided_task_id(monkeypatch: pytest.MonkeyPatch) -> None:
    from services import task_manager as task_manager_module

    broadcast = AsyncMock()
    monkeypatch.setattr(task_manager_module.ws_manager, "broadcast", broadcast)
    manager = task_manager_module.TaskManager()

    async def sample_task(progress_callback):
        await progress_callback(100, "完成")

    info = manager.submit(
        task_type="video_import",
        coro_factory=sample_task,
        project_id="project-1",
        task_id="video-1",
    )

    for _ in range(20):
        if manager.get("video-1") and manager.get("video-1").status == "succeeded":
            break
        await asyncio.sleep(0.01)

    assert info.id == "video-1"
    assert manager.get("video-1") is info
    assert broadcast.await_args_list[0].args[0]["taskId"] == "video-1"


async def test_task_manager_rejects_duplicate_running_task_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from services import task_manager as task_manager_module

    broadcast = AsyncMock()
    monkeypatch.setattr(task_manager_module.ws_manager, "broadcast", broadcast)
    manager = task_manager_module.TaskManager()
    started = asyncio.Event()

    async def slow_task(progress_callback):
        await progress_callback(1, "运行中")
        started.set()
        await asyncio.sleep(10)

    info = manager.submit(
        task_type="video_import",
        coro_factory=slow_task,
        task_id="video-duplicate",
    )
    await asyncio.wait_for(started.wait(), timeout=1)

    with pytest.raises(ValueError, match="任务已存在"):
        manager.submit(
            task_type="video_import",
            coro_factory=slow_task,
            task_id="video-duplicate",
        )

    assert manager.cancel(info.id) is True


async def test_task_manager_marks_failed_tasks(monkeypatch: pytest.MonkeyPatch) -> None:
    from services import task_manager as task_manager_module

    broadcast = AsyncMock()
    monkeypatch.setattr(task_manager_module.ws_manager, "broadcast", broadcast)
    manager = task_manager_module.TaskManager()

    async def failing_task(progress_callback):
        await progress_callback(5, "开始处理")
        raise RuntimeError("provider unavailable")

    info = manager.submit(task_type="asset_analysis", coro_factory=failing_task)

    for _ in range(20):
        if manager.get(info.id).status == "failed":
            break
        await asyncio.sleep(0.01)

    result = manager.get(info.id)
    assert result is not None
    assert result.status == "failed"
    assert result.message == "provider unavailable"
    assert broadcast.await_args_list[-1].args[0]["type"] == "task.failed"


async def test_task_manager_cancels_running_task(monkeypatch: pytest.MonkeyPatch) -> None:
    from services import task_manager as task_manager_module

    broadcast = AsyncMock()
    monkeypatch.setattr(task_manager_module.ws_manager, "broadcast", broadcast)
    manager = task_manager_module.TaskManager()
    started = asyncio.Event()

    async def slow_task(progress_callback):
        await progress_callback(10, "等待取消")
        started.set()
        await asyncio.sleep(10)

    info = manager.submit(task_type="video_generation", coro_factory=slow_task)
    await asyncio.wait_for(started.wait(), timeout=1)

    assert manager.cancel(info.id) is True

    for _ in range(20):
        if manager.get(info.id).status == "cancelled":
            break
        await asyncio.sleep(0.01)

    result = manager.get(info.id)
    assert result is not None
    assert result.status == "cancelled"
    assert result.message == "任务已取消"
    assert broadcast.await_args_list[-1].args[0]["type"] == "task.failed"


async def test_ws_manager_injects_schema_version() -> None:
    manager = ConnectionManager()
    connection = AsyncMock()
    manager.active_connections.append(connection)

    await manager.broadcast({"event": "video_status_changed"})

    connection.send_json.assert_awaited_once_with(
        {"event": "video_status_changed", "schema_version": 1}
    )
