from __future__ import annotations

import asyncio
import logging
import math
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import ParamSpec, TypeVar
from uuid import uuid4

from errors import DomainError, ErrorCode
from services.tasks.errors import TaskCancellationRequested, task_snapshot_invalid
from services.tasks.handler_registry import TaskHandlerRegistry
from services.tasks.snapshot import TaskSnapshotPolicy
from services.tasks.task_service import TaskService
from services.tasks.types import (
    JsonValue,
    RuntimeTaskRecord,
    TaskCommitCoordinator,
    TaskCommitDecision,
    TaskExecutionResult,
    TaskFailureKind,
    TaskRuntimePolicy,
    TaskStatus,
)

log = logging.getLogger(__name__)

_P = ParamSpec("_P")
_R = TypeVar("_R")
_BLOCKING_CANCEL_GRACE_SECONDS = 1.0


@dataclass(slots=True)
class _ExecutionContext:
    task_id: str
    account_id: str | None
    attempt: int
    cancellation_event: asyncio.Event
    task_service: TaskService
    commit_coordinator: TaskCommitCoordinator

    async def report_progress(self, progress: float) -> None:
        self.raise_if_cancelled()
        await _run_blocking_call(
            self.task_service.update_progress,
            self.task_id,
            progress,
        )

    def raise_if_cancelled(self) -> None:
        if self.cancellation_event.is_set():
            raise TaskCancellationRequested()

    def enable_commit_coordination(self) -> TaskCommitCoordinator:
        return self.commit_coordinator.enable()


class TaskRunner:
    """在受控并发和持久超时边界内执行任务处理器。"""

    def __init__(
        self,
        *,
        task_service: TaskService,
        handler_registry: TaskHandlerRegistry,
        snapshot_policy: TaskSnapshotPolicy,
        runtime_policy: TaskRuntimePolicy,
        shutdown_grace_seconds: float = 10.0,
    ) -> None:
        if (
            not math.isfinite(shutdown_grace_seconds)
            or shutdown_grace_seconds <= 0
        ):
            raise ValueError("任务执行器停机宽限时间必须是大于零的有限数")
        self._task_service = task_service
        self._handler_registry = handler_registry
        self._snapshot_policy = snapshot_policy
        self._max_concurrency = runtime_policy.max_concurrency
        self._shutdown_grace_seconds = shutdown_grace_seconds
        self._semaphore: asyncio.Semaphore | None = None
        self._handles: dict[str, asyncio.Task[None]] = {}
        self._cancellation_events: dict[str, asyncio.Event] = {}
        self._execution_contexts: dict[str, _ExecutionContext] = {}
        self._state = "new"

    def start(self) -> None:
        """启动或重新启动执行器，重建事件循环绑定的并发控制对象。"""
        if self._state == "running":
            return
        if self._state == "stopping":
            raise RuntimeError("任务执行器正在关闭，不能重新启动")
        if any(not handle.done() for handle in self._handles.values()):
            raise RuntimeError("任务执行器仍有未回收任务，不能重新启动")
        self._handles.clear()
        self._cancellation_events.clear()
        self._execution_contexts.clear()
        self._semaphore = asyncio.Semaphore(self._max_concurrency)
        self._state = "running"

    def schedule(self, task_id: str) -> None:
        if self._state == "new":
            self.start()
        elif self._state == "stopping":
            raise RuntimeError("任务执行器正在关闭，不能接收新任务")
        elif self._state == "stopped":
            raise RuntimeError("任务执行器已停止，请先显式重新启动")
        existing = self._handles.get(task_id)
        if existing is not None and not existing.done():
            return
        semaphore = self._semaphore
        if semaphore is None:
            raise RuntimeError("任务执行器并发控制尚未初始化")
        cancellation_event = asyncio.Event()
        self._cancellation_events[task_id] = cancellation_event
        handle = asyncio.create_task(
            self._run(task_id, cancellation_event, semaphore),
            name=f"runtime-task:{task_id}",
        )
        self._handles[task_id] = handle
        handle.add_done_callback(
            lambda completed, current_id=task_id: self._on_done(
                current_id,
                completed,
            )
        )

    def request_cancel(self, task_id: str) -> None:
        cancellation_event = self._cancellation_events.get(task_id)
        if cancellation_event is not None:
            cancellation_event.set()
        handle = self._handles.get(task_id)
        if handle is not None and not handle.done():
            handle.cancel()

    async def decide_commit_aware_cancellation(
        self,
        task_id: str,
    ) -> TaskCommitDecision | None:
        context = self._execution_contexts.get(task_id)
        if context is None or not context.commit_coordinator.enabled:
            return None
        return await asyncio.to_thread(
            context.commit_coordinator.request_termination
        )

    async def wait_for_completion(self, task_id: str) -> None:
        handle = self._handles.get(task_id)
        if handle is None or handle.done():
            return
        await asyncio.shield(handle)

    async def shutdown(
        self,
        *,
        timeout_seconds: float | None = None,
    ) -> None:
        if self._state == "stopped":
            return
        if self._state == "new":
            self._state = "stopped"
            return

        wait_seconds = self._resolve_shutdown_wait(timeout_seconds)
        if self._state != "stopping":
            self._state = "stopping"
            active = self._active_handles()
            for handle in active:
                handle.cancel()
        else:
            active = self._active_handles()

        try:
            if active and wait_seconds > 0:
                await asyncio.wait(active, timeout=wait_seconds)
        finally:
            if not self._finalize_stopped_if_idle():
                pending_ids = sorted(
                    task_id
                    for task_id, handle in self._handles.items()
                    if not handle.done()
                )
                log.warning(
                    "任务执行器未在停机宽限期内完全停止，任务将由下次启动恢复",
                    extra={
                        "pending_task_count": len(pending_ids),
                        "pending_task_ids": pending_ids,
                        "grace_seconds": wait_seconds,
                    },
                )

    def is_scheduled(self, task_id: str) -> bool:
        handle = self._handles.get(task_id)
        return handle is not None and not handle.done()

    async def _run(
        self,
        task_id: str,
        cancellation_event: asyncio.Event,
        semaphore: asyncio.Semaphore,
    ) -> None:
        try:
            async with semaphore:
                await self._execute(task_id, cancellation_event)
        except asyncio.CancelledError:
            await self._handle_async_cancellation(task_id)
            raise
        except Exception:
            log.exception(
                "任务执行器发生未恢复异常",
                extra={"task_id": task_id},
            )

    async def _execute(
        self,
        task_id: str,
        cancellation_event: asyncio.Event,
    ) -> None:
        try:
            current = await _run_blocking_call(
                self._task_service.get_task,
                task_id,
            )
            if current.is_terminal:
                return
            if current.status is TaskStatus.CANCELLING:
                await _run_blocking_call(
                    self._task_service.complete_cancelled,
                    task_id,
                )
                return
            remaining = _remaining_seconds(current)
            if remaining <= 0:
                await self._fail_timeout(task_id)
                return

            definition = self._handler_registry.require(current.task_type)
            snapshot = self._snapshot_policy.load(
                current.config_snapshot_json,
                expected_handler_version=definition.handler_version,
            )
            if (
                snapshot.key_hash != current.idempotency_key_hash
                or snapshot.request_hash != current.request_hash
                or snapshot.handler_version != current.handler_version
            ):
                raise task_snapshot_invalid(
                    "任务显式摘要与持久快照不一致"
                )
            claimed = await _run_blocking_call(
                self._task_service.claim_running,
                task_id,
            )
            if claimed.is_terminal:
                return
            if claimed.status is TaskStatus.CANCELLING:
                await _run_blocking_call(
                    self._task_service.complete_cancelled,
                    task_id,
                )
                return
            if claimed.status is not TaskStatus.RUNNING:
                return

            context = _ExecutionContext(
                task_id=claimed.id,
                account_id=claimed.account_id,
                attempt=claimed.attempt,
                cancellation_event=cancellation_event,
                task_service=self._task_service,
                commit_coordinator=TaskCommitCoordinator(),
            )
            self._execution_contexts[task_id] = context
            remaining = _remaining_seconds(claimed)
            if remaining <= 0:
                await self._fail_timeout(task_id)
                return
            async with asyncio.timeout(remaining):
                result = await definition.handler(context, snapshot.payload)
                context.raise_if_cancelled()
            if result is not None and not isinstance(result, TaskExecutionResult):
                raise TypeError("任务处理器必须返回 TaskExecutionResult 或 None")
            await _run_blocking_call(
                self._task_service.complete_success,
                task_id,
                result_ref=None if result is None else result.result_ref,
            )
        except TaskCancellationRequested:
            await _run_blocking_call(
                self._task_service.complete_cancelled,
                task_id,
            )
        except TimeoutError:
            await self._fail_timeout(task_id)
        except asyncio.CancelledError:
            raise
        except DomainError as exc:
            log_id = f"log_{uuid4().hex}"
            log.exception(
                "任务处理器因领域错误失败",
                extra={
                    "task_id": task_id,
                    "error_code": exc.error_code,
                    "log_id": log_id,
                },
            )
            await _run_blocking_call(
                self._task_service.fail,
                task_id,
                failure_kind=TaskFailureKind.ERROR,
                error_code=exc.error_code,
                error_log_id=log_id,
            )
        except Exception:
            log_id = f"log_{uuid4().hex}"
            log.exception(
                "任务处理器执行失败",
                extra={"task_id": task_id, "log_id": log_id},
            )
            await _run_blocking_call(
                self._task_service.fail,
                task_id,
                failure_kind=TaskFailureKind.ERROR,
                error_code=ErrorCode.INTERNAL_ERROR.value,
                error_log_id=log_id,
            )

    async def _handle_async_cancellation(self, task_id: str) -> None:
        try:
            current = await _run_blocking_call(
                self._task_service.get_task,
                task_id,
            )
            if current.status is TaskStatus.CANCELLING:
                await _run_blocking_call(
                    self._task_service.complete_cancelled,
                    task_id,
                )
        except DomainError:
            log.exception(
                "处理任务异步取消时无法读取任务",
                extra={"task_id": task_id},
            )
        except Exception:
            log.exception(
                "处理任务异步取消失败",
                extra={"task_id": task_id},
            )

    async def _fail_timeout(self, task_id: str) -> None:
        await _run_blocking_call(
            self._task_service.fail,
            task_id,
            failure_kind=TaskFailureKind.TIMED_OUT,
            error_code=ErrorCode.TASK_TIMEOUT.value,
        )

    def _on_done(
        self,
        task_id: str,
        completed: asyncio.Task[None],
    ) -> None:
        if self._handles.get(task_id) is completed:
            self._handles.pop(task_id, None)
            self._cancellation_events.pop(task_id, None)
            self._execution_contexts.pop(task_id, None)
        if completed.cancelled():
            if self._state == "stopping":
                self._finalize_stopped_if_idle()
            return
        try:
            completed.exception()
        except Exception:
            log.exception(
                "回收任务执行器句柄失败",
                extra={"task_id": task_id},
            )
        finally:
            if self._state == "stopping":
                self._finalize_stopped_if_idle()

    def _active_handles(self) -> list[asyncio.Task[None]]:
        return [
            handle
            for handle in self._handles.values()
            if not handle.done()
        ]

    def _finalize_stopped_if_idle(self) -> bool:
        if self._active_handles():
            return False
        self._handles.clear()
        self._cancellation_events.clear()
        self._execution_contexts.clear()
        self._semaphore = None
        self._state = "stopped"
        return True

    def _resolve_shutdown_wait(self, timeout_seconds: float | None) -> float:
        if timeout_seconds is None:
            return self._shutdown_grace_seconds
        if not math.isfinite(timeout_seconds):
            raise ValueError("任务执行器停机等待时间必须是有限数")
        return max(0.0, timeout_seconds)


async def _run_blocking_call(
    callback: Callable[_P, _R],
    *args: _P.args,
    **kwargs: _P.kwargs,
) -> _R:
    """取消协程时受控等待数据库调用，超时后交由线程自行收尾。"""
    handle = asyncio.create_task(asyncio.to_thread(callback, *args, **kwargs))
    try:
        return await asyncio.shield(handle)
    except asyncio.CancelledError:
        try:
            completed, _ = await asyncio.wait(
                {handle},
                timeout=_BLOCKING_CANCEL_GRACE_SECONDS,
            )
        except asyncio.CancelledError:
            handle.add_done_callback(_consume_blocking_completion)
            raise
        if completed:
            _consume_blocking_completion(handle)
        else:
            log.warning(
                "取消期间任务数据库操作未在宽限期内收尾，将由后台线程完成",
                extra={
                    "callback": getattr(
                        callback,
                        "__name__",
                        type(callback).__name__,
                    ),
                    "grace_seconds": _BLOCKING_CANCEL_GRACE_SECONDS,
                },
            )
            handle.add_done_callback(_consume_blocking_completion)
        raise


def _consume_blocking_completion(handle: asyncio.Task[object]) -> None:
    if handle.cancelled():
        return
    try:
        error = handle.exception()
    except Exception:
        log.exception("读取任务数据库后台操作结果失败")
        return
    if error is not None:
        log.error(
            "任务数据库后台操作收尾失败",
            exc_info=(type(error), error, error.__traceback__),
        )


def _remaining_seconds(record: RuntimeTaskRecord) -> float:
    if record.timeout_at is None:
        return 0
    try:
        deadline = datetime.fromisoformat(record.timeout_at.replace("Z", "+00:00"))
    except ValueError:
        log.error(
            "持久任务超时时间格式无效",
            extra={"task_id": record.id},
        )
        return 0
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=UTC)
    return (deadline.astimezone(UTC) - datetime.now(UTC)).total_seconds()
