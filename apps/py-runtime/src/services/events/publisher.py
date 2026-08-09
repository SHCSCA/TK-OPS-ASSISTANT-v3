from __future__ import annotations

import asyncio
import logging
import math
from collections.abc import Awaitable, Callable
from typing import ParamSpec, TypeVar

from repositories.runtime_event_repository import (
    RuntimeEventRecord,
    RuntimeEventRepository,
)
from services.events.contracts import RuntimeEventDto
from services.events.service import RuntimeEventService

log = logging.getLogger(__name__)

EventDelivery = Callable[[RuntimeEventDto], Awaitable[None]]
_P = ParamSpec("_P")
_R = TypeVar("_R")


class RuntimeEventPublisher:
    """按 outbox 顺序投递事件，并在成功交给实时总线后标记已发布。"""

    def __init__(
        self,
        repository: RuntimeEventRepository,
        event_service: RuntimeEventService,
        deliver: EventDelivery,
        *,
        batch_size: int = 100,
        blocking_cancel_grace_seconds: float = 1.0,
    ) -> None:
        if batch_size < 1:
            raise ValueError("事件发布批次必须大于 0")
        if (
            not math.isfinite(blocking_cancel_grace_seconds)
            or blocking_cancel_grace_seconds <= 0
        ):
            raise ValueError("事件发布器同步调用取消宽限必须是大于零的有限数")
        self._repository = repository
        self._event_service = event_service
        self._deliver = deliver
        self._batch_size = batch_size
        self._blocking_cancel_grace_seconds = blocking_cancel_grace_seconds
        self._publish_lock = asyncio.Lock()

    async def publish_pending(
        self,
        *,
        timeout_seconds: float | None = None,
    ) -> int:
        deadline = _build_deadline(timeout_seconds)
        published = 0
        await _acquire_lock(self._publish_lock, deadline=deadline)
        try:
            records = await _run_blocking_call(
                self._repository.list_unpublished,
                limit=self._batch_size,
                deadline=deadline,
                cancellation_grace_seconds=(
                    self._blocking_cancel_grace_seconds
                ),
            )
            for record in records:
                try:
                    if _is_non_deliverable_legacy_migration_event(record):
                        log.warning(
                            "跳过旧迁移审计事件的实时投递",
                            extra={
                                "event_id": record.event_id,
                                "topic": record.topic,
                            },
                        )
                    else:
                        event = self._event_service.to_dto(record)
                        await _deliver_until(
                            self._deliver(event),
                            deadline=deadline,
                        )
                    await _run_blocking_call(
                        self._repository.mark_published,
                        [record.event_id],
                        deadline=deadline,
                        cancellation_grace_seconds=(
                            self._blocking_cancel_grace_seconds
                        ),
                    )
                    published += 1
                except TimeoutError:
                    log.warning(
                        "Runtime outbox 发布超时，未确认事件将在下次启动重放",
                        extra={
                            "event_id": record.event_id,
                            "topic": record.topic,
                            "sequence": record.sequence,
                        },
                    )
                    break
                except Exception:
                    log.exception(
                        "发布 Runtime outbox 事件失败",
                        extra={
                            "event_id": record.event_id,
                            "topic": record.topic,
                            "sequence": record.sequence,
                        },
                    )
                    break
        finally:
            self._publish_lock.release()
        return published


async def _run_blocking_call(
    callback: Callable[_P, _R],
    *args: _P.args,
    deadline: float | None,
    cancellation_grace_seconds: float,
    **kwargs: _P.kwargs,
) -> _R:
    """按截止点等待 outbox 数据库调用，超时后保留持久事件。"""
    handle = asyncio.create_task(asyncio.to_thread(callback, *args, **kwargs))
    try:
        if deadline is None:
            return await asyncio.shield(handle)
        completed, _ = await asyncio.wait(
            {handle},
            timeout=_remaining_seconds(deadline),
        )
        if not completed:
            handle.add_done_callback(_consume_blocking_completion)
            raise TimeoutError
        return handle.result()
    except asyncio.CancelledError:
        wait_seconds = cancellation_grace_seconds
        if deadline is not None:
            wait_seconds = min(
                wait_seconds,
                _remaining_seconds(deadline),
            )
        try:
            completed, _ = await asyncio.wait(
                {handle},
                timeout=max(0.0, wait_seconds),
            )
        except asyncio.CancelledError:
            handle.add_done_callback(_consume_blocking_completion)
            raise
        if completed:
            _consume_blocking_completion(handle)
        else:
            log.warning(
                "取消期间 Runtime outbox 数据库操作未及时收尾，将由后台线程完成",
                extra={
                    "callback": getattr(
                        callback,
                        "__name__",
                        type(callback).__name__,
                    ),
                    "grace_seconds": max(0.0, wait_seconds),
                },
            )
            handle.add_done_callback(_consume_blocking_completion)
        raise


async def _acquire_lock(
    lock: asyncio.Lock,
    *,
    deadline: float | None,
) -> None:
    if deadline is None:
        await lock.acquire()
        return
    handle = asyncio.create_task(lock.acquire())
    try:
        completed, _ = await asyncio.wait(
            {handle},
            timeout=_remaining_seconds(deadline),
        )
        if not completed:
            _cancel_lock_waiter(handle, lock)
            raise TimeoutError
        handle.result()
    except asyncio.CancelledError:
        _cancel_lock_waiter(handle, lock)
        raise


async def _deliver_until(
    delivery: Awaitable[None],
    *,
    deadline: float | None,
) -> None:
    if deadline is None:
        await delivery
        return
    handle = asyncio.create_task(delivery)
    try:
        completed, _ = await asyncio.wait(
            {handle},
            timeout=_remaining_seconds(deadline),
        )
        if not completed:
            handle.cancel()
            handle.add_done_callback(_consume_delivery_completion)
            raise TimeoutError
        handle.result()
    except asyncio.CancelledError:
        handle.cancel()
        handle.add_done_callback(_consume_delivery_completion)
        raise


def _build_deadline(timeout_seconds: float | None) -> float | None:
    if timeout_seconds is None:
        return None
    if not math.isfinite(timeout_seconds):
        raise ValueError("事件发布等待时间必须是有限数")
    return asyncio.get_running_loop().time() + max(0.0, timeout_seconds)


def _remaining_seconds(deadline: float) -> float:
    return max(0.0, deadline - asyncio.get_running_loop().time())


def _consume_blocking_completion(handle: asyncio.Task[object]) -> None:
    _consume_completion(handle, action="Runtime outbox 数据库后台操作")


def _consume_delivery_completion(handle: asyncio.Task[object]) -> None:
    _consume_completion(handle, action="Runtime outbox 实时投递后台操作")


def _cancel_lock_waiter(
    handle: asyncio.Task[bool],
    lock: asyncio.Lock,
) -> None:
    if not handle.done():
        handle.cancel()
    if handle.done():
        _release_lock_if_acquired(handle, lock)
        return
    handle.add_done_callback(
        lambda completed: _release_lock_if_acquired(completed, lock)
    )


def _release_lock_if_acquired(
    handle: asyncio.Task[bool],
    lock: asyncio.Lock,
) -> None:
    if handle.cancelled():
        return
    try:
        acquired = handle.result()
    except Exception:
        log.exception("取消 Runtime outbox 锁等待失败")
        return
    if acquired and lock.locked():
        lock.release()


def _consume_completion(
    handle: asyncio.Task[object],
    *,
    action: str,
) -> None:
    if handle.cancelled():
        return
    try:
        error = handle.exception()
    except Exception:
        log.exception("读取%s结果失败", action)
        return
    if error is not None:
        log.error(
            "%s收尾失败",
            action,
            exc_info=(type(error), error, error.__traceback__),
        )


def _is_non_deliverable_legacy_migration_event(
    record: RuntimeEventRecord,
) -> bool:
    return (
        record.event_id == "migration:0016_p0_backfill"
        and record.topic == "system.migrations"
        and record.event_type == "migration.legacy_backfill_completed"
    )
