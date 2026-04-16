from __future__ import annotations

import asyncio
import logging
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Awaitable, Callable
from uuid import uuid4

from services.ws_manager import ws_manager

log = logging.getLogger(__name__)

TaskStatus = str
ProgressCallback = Callable[[int, str], Awaitable[None]]
TaskCoroFactory = Callable[[ProgressCallback], Awaitable[None]]


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class TaskInfo:
    id: str
    task_type: str
    project_id: str | None
    status: TaskStatus
    progress: int
    message: str
    created_at: str
    updated_at: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class TaskManager:
    """管理内存态长任务生命周期与 WebSocket 进度广播。"""

    def __init__(self) -> None:
        self._tasks: dict[str, TaskInfo] = {}
        self._async_tasks: dict[str, asyncio.Task[None]] = {}

    def submit(
        self,
        task_type: str,
        coro_factory: TaskCoroFactory,
        project_id: str | None = None,
        task_id: str | None = None,
    ) -> TaskInfo:
        resolved_task_id = task_id or str(uuid4())
        existing_task = self._tasks.get(resolved_task_id)
        if existing_task and existing_task.status in {"queued", "running"}:
            raise ValueError("任务已存在")

        now = _utc_now()
        task_info = TaskInfo(
            id=resolved_task_id,
            task_type=task_type,
            project_id=project_id,
            status="queued",
            progress=0,
            message="任务已排队",
            created_at=now,
            updated_at=now,
        )
        self._tasks[task_info.id] = task_info
        self._async_tasks[task_info.id] = asyncio.create_task(
            self._run_task(task_info, coro_factory)
        )
        return task_info

    def cancel(self, task_id: str) -> bool:
        task = self._async_tasks.get(task_id)
        task_info = self._tasks.get(task_id)
        if task is None or task_info is None or task.done():
            return False

        task.cancel()
        return True

    def get(self, task_id: str) -> TaskInfo | None:
        return self._tasks.get(task_id)

    def list_active(self) -> list[TaskInfo]:
        return [
            task
            for task in self._tasks.values()
            if task.status in {"queued", "running"}
        ]

    def to_event(self, task_info: TaskInfo, event_type: str) -> dict[str, object]:
        return {
            "schema_version": 1,
            "type": event_type,
            "taskId": task_info.id,
            "taskType": task_info.task_type,
            "projectId": task_info.project_id,
            "status": task_info.status,
            "progress": task_info.progress,
            "message": task_info.message,
        }

    async def _run_task(
        self,
        task_info: TaskInfo,
        coro_factory: TaskCoroFactory,
    ) -> None:
        try:
            self._update(task_info, status="running", progress=0, message="任务已开始")
            await ws_manager.broadcast(self.to_event(task_info, "task.started"))

            async def progress_callback(progress: int, message: str) -> None:
                normalized_progress = max(0, min(100, int(progress)))
                self._update(
                    task_info,
                    status="running",
                    progress=normalized_progress,
                    message=message,
                )
                await ws_manager.broadcast(self.to_event(task_info, "task.progress"))

            await coro_factory(progress_callback)
            self._update(
                task_info,
                status="succeeded",
                progress=100,
                message="任务已完成",
            )
            await ws_manager.broadcast(self.to_event(task_info, "task.completed"))
        except asyncio.CancelledError:
            self._update(task_info, status="cancelled", message="任务已取消")
            await ws_manager.broadcast(self.to_event(task_info, "task.failed"))
        except Exception as exc:
            log.exception("后台任务执行失败: %s", task_info.id)
            self._update(task_info, status="failed", message=str(exc) or "任务执行失败")
            await ws_manager.broadcast(self.to_event(task_info, "task.failed"))

    def _update(
        self,
        task_info: TaskInfo,
        *,
        status: TaskStatus | None = None,
        progress: int | None = None,
        message: str | None = None,
    ) -> None:
        if status is not None:
            task_info.status = status
        if progress is not None:
            task_info.progress = max(0, min(100, progress))
        if message is not None:
            task_info.message = message
        task_info.updated_at = _utc_now()


task_manager = TaskManager()
