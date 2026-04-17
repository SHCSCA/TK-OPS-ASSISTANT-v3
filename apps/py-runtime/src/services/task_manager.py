from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Awaitable, Callable
from uuid import uuid4

from services.ws_manager import ws_manager

log = logging.getLogger(__name__)

TaskStatus = str
ProgressCallback = Callable[[int, str], Awaitable[None]]
TaskCoroFactory = Callable[[ProgressCallback], Awaitable[None]]


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


@dataclass
class TaskInfo:
    id: str
    status: TaskStatus
    created_at: str
    updated_at: str
    task_type: str | None = None
    project_id: str | None = None
    progress: int = 0
    message: str = ""
    kind: str | None = None
    label: str | None = None
    progress_pct: int | None = None
    started_at: str | None = None
    finished_at: str | None = None
    eta_ms: int | None = None
    owner_ref: dict[str, str] | None = None
    error_code: str | None = None
    error_message: str | None = None
    retryable: bool = False

    def __post_init__(self) -> None:
        resolved_kind = self.kind or self.task_type or "generic"
        resolved_progress = self.progress_pct
        if resolved_progress is None:
            resolved_progress = max(0, min(100, int(self.progress)))

        self.kind = resolved_kind
        self.task_type = resolved_kind
        self.label = self.label or self.message or resolved_kind
        self.progress_pct = resolved_progress
        self.progress = resolved_progress
        if self.status == "failed":
            self.error_message = self.error_message or self.message or "任务执行失败"
            self.message = self.error_message
        elif not self.message:
            self.message = self.label or resolved_kind

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "kind": self.kind,
            "label": self.label,
            "status": self.status,
            "progressPct": self.progress_pct,
            "startedAt": self.started_at,
            "finishedAt": self.finished_at,
            "etaMs": self.eta_ms,
            "projectId": self.project_id,
            "ownerRef": self.owner_ref,
            "errorCode": self.error_code,
            "errorMessage": self.error_message,
            "retryable": self.retryable,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
        }


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
            label=task_type,
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
        return self.list_tasks(statuses={"queued", "running"})

    def list_tasks(
        self,
        *,
        kind: str | None = None,
        statuses: set[str] | None = None,
    ) -> list[TaskInfo]:
        tasks = list(self._tasks.values())
        if kind is not None:
            tasks = [task for task in tasks if task.kind == kind]
        if statuses is not None:
            tasks = [task for task in tasks if task.status in statuses]
        return sorted(tasks, key=lambda item: item.updated_at, reverse=True)

    def to_event(self, task_info: TaskInfo, event_type: str) -> dict[str, object]:
        return {
            "schema_version": 1,
            "type": event_type,
            "taskId": task_info.id,
            "taskType": task_info.kind,
            "projectId": task_info.project_id,
            "status": task_info.status,
            "progress": task_info.progress_pct,
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
        timestamp = _utc_now()
        if status is not None:
            task_info.status = status
            if status == "running" and task_info.started_at is None:
                task_info.started_at = timestamp
            if status in {"succeeded", "failed", "cancelled"}:
                task_info.finished_at = timestamp
        if progress is not None:
            normalized_progress = max(0, min(100, progress))
            task_info.progress = normalized_progress
            task_info.progress_pct = normalized_progress
        if message is not None:
            task_info.message = message
            if task_info.label is None:
                task_info.label = message
            task_info.error_message = message if task_info.status == "failed" else None
        task_info.updated_at = timestamp


task_manager = TaskManager()
