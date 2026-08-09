from __future__ import annotations

import asyncio
import logging

from app.runtime_kernel import RuntimeKernel
from app.shutdown_deadline import ShutdownDeadline, wait_task_until

log = logging.getLogger(__name__)


class RuntimeBackgroundServices:
    """统一管理持久任务恢复与事件 outbox 生命周期。"""

    def __init__(self, kernel: RuntimeKernel) -> None:
        self._kernel = kernel
        self._stop_event = asyncio.Event()
        self._publisher_handle: asyncio.Task[None] | None = None
        self._shutdown_handle: asyncio.Task[None] | None = None

    async def start(self) -> None:
        if (
            self._shutdown_handle is not None
            and not self._shutdown_handle.done()
        ):
            raise RuntimeError("Runtime 后台服务正在关闭，不能重新启动")
        if (
            self._publisher_handle is not None
            and not self._publisher_handle.done()
        ):
            return
        self._stop_event = asyncio.Event()
        try:
            self._kernel.task_runner.start()
            recovery = await self._kernel.task_coordinator.recover()
            log.info(
                "Runtime 持久任务恢复完成",
                extra={
                    "resumable_count": len(recovery.resumable_task_ids),
                    "interrupted_count": len(recovery.interrupted_task_ids),
                    "timed_out_count": len(recovery.timed_out_task_ids),
                    "cancelled_count": len(recovery.cancelled_task_ids),
                },
            )
            await self._kernel.event_publisher.publish_pending()
        except Exception:
            log.exception("启动 Runtime 后台服务失败")
            try:
                await self._kernel.task_runner.shutdown(
                    timeout_seconds=(
                        self._kernel.policy.shutdown_grace_seconds
                    ),
                )
            except Exception:
                log.exception("启动失败后关闭 Runtime 持久任务执行器失败")
            raise
        self._publisher_handle = asyncio.create_task(
            self._publisher_loop(),
            name="runtime-event-publisher",
        )

    async def shutdown(
        self,
        *,
        deadline: ShutdownDeadline | None = None,
    ) -> None:
        shutdown_deadline = deadline or ShutdownDeadline.start(
            self._kernel.policy.shutdown_grace_seconds
        )
        handle = self._shutdown_handle
        if handle is not None and handle.done():
            if self._shutdown_handle is handle:
                self._shutdown_handle = None
            handle.result()
            return
        if handle is None:
            handle = asyncio.create_task(
                self._shutdown(shutdown_deadline),
                name="runtime-background-shutdown",
            )
            self._shutdown_handle = handle
            handle.add_done_callback(self._on_shutdown_done)
        try:
            completed = await wait_task_until(handle, shutdown_deadline)
        except asyncio.CancelledError:
            raise
        if completed:
            handle.result()
            return
        log.error(
            "Runtime 后台服务未在统一停机预算内完成，将保留持久状态供下次恢复",
            extra={
                "grace_seconds": self._kernel.policy.shutdown_grace_seconds
            },
        )
        handle.cancel()

    async def _shutdown(self, deadline: ShutdownDeadline) -> None:
        self._stop_event.set()
        handle = self._publisher_handle
        try:
            if handle is not None:
                publisher_budget = deadline.remaining_seconds() * 0.25
                await self._stop_publisher(
                    handle,
                    deadline=deadline.capped(publisher_budget),
                    grace_seconds=publisher_budget,
                )
        finally:
            self._publisher_handle = None

        try:
            task_budget = deadline.remaining_seconds() * 0.65
            await self._kernel.task_runner.shutdown(
                timeout_seconds=task_budget,
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("关闭 Runtime 持久任务执行器失败")
        try:
            await self._kernel.event_publisher.publish_pending(
                timeout_seconds=deadline.remaining_seconds(),
            )
        except TimeoutError:
            log.warning("关闭 Runtime 时刷新事件 outbox 超时，事件将在下次启动重放")
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("关闭 Runtime 时刷新事件 outbox 失败")

    async def _stop_publisher(
        self,
        handle: asyncio.Task[None],
        *,
        deadline: ShutdownDeadline,
        grace_seconds: float,
    ) -> None:
        if handle.done():
            self._consume_publisher_result(handle)
            return

        try:
            completed = await wait_task_until(handle, deadline)
        except asyncio.CancelledError:
            raise
        if completed:
            self._consume_publisher_result(handle)
        else:
            log.warning(
                "Runtime 事件 outbox 未在宽限期内停止，将请求取消",
                extra={"grace_seconds": grace_seconds},
            )
            handle.cancel()
            handle.add_done_callback(self._consume_publisher_result)

    def _on_shutdown_done(self, handle: asyncio.Task[None]) -> None:
        if self._shutdown_handle is handle:
            self._shutdown_handle = None
        if handle.cancelled():
            return
        try:
            error = handle.exception()
        except Exception:
            log.exception("回收 Runtime 后台停机任务失败")
            return
        if error is not None:
            log.error(
                "Runtime 后台停机任务异常退出",
                exc_info=(type(error), error, error.__traceback__),
            )

    @staticmethod
    def _consume_publisher_result(handle: asyncio.Task[None]) -> None:
        if handle.cancelled():
            return
        try:
            error = handle.exception()
        except Exception:
            log.exception("读取 Runtime 事件 outbox 后台任务结果失败")
            return
        if error is not None:
            log.error(
                "Runtime 事件 outbox 后台任务异常退出",
                exc_info=(type(error), error, error.__traceback__),
            )

    async def _publisher_loop(self) -> None:
        interval = self._kernel.policy.event_publish_interval_seconds
        try:
            while not self._stop_event.is_set():
                try:
                    await self._kernel.event_publisher.publish_pending()
                except Exception:
                    log.exception("Runtime 事件 outbox 后台发布失败")
                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(),
                        timeout=interval,
                    )
                except TimeoutError:
                    continue
        except asyncio.CancelledError:
            raise
