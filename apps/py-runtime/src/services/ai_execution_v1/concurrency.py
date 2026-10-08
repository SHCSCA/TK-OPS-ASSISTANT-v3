from __future__ import annotations

import asyncio
import time
from collections import deque
from collections.abc import Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator

from .types import ProviderCallError, ProviderFailureCategory


@dataclass(frozen=True, slots=True)
class _Waiter:
    marker: object
    account_id: str
    route_provider_key: str
    limit: int


class AIExecutionConcurrencyGate:
    """统一约束全局与 Route/Provider 并发，并按账号交替放行。"""

    def __init__(self, global_limit: int) -> None:
        if global_limit < 1:
            raise ValueError("AI 执行全局并发上限无效")
        self._global_limit = global_limit
        self._condition = asyncio.Condition()
        self._waiters: deque[_Waiter] = deque()
        self._active_global = 0
        self._active_by_key: dict[str, int] = {}
        self._last_account_id: str | None = None

    @asynccontextmanager
    async def lease(
        self,
        *,
        account_id: str,
        route_provider_key: str,
        limit: int,
        timeout_seconds: float,
        cancellation_probe: Callable[[], None],
    ) -> AsyncIterator[None]:
        if limit < 1 or timeout_seconds <= 0:
            raise _queue_timeout()
        waiter = _Waiter(
            marker=object(),
            account_id=account_id,
            route_provider_key=route_provider_key,
            limit=limit,
        )
        acquired = False
        deadline = time.monotonic() + timeout_seconds
        async with self._condition:
            self._waiters.append(waiter)
            try:
                while not acquired:
                    cancellation_probe()
                    if self._selected(waiter):
                        self._waiters.remove(waiter)
                        self._active_global += 1
                        self._active_by_key[route_provider_key] = (
                            self._active_by_key.get(route_provider_key, 0) + 1
                        )
                        self._last_account_id = account_id
                        acquired = True
                        break
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise _queue_timeout()
                    try:
                        await asyncio.wait_for(
                            self._condition.wait(),
                            timeout=min(0.1, remaining),
                        )
                    except TimeoutError:
                        continue
            finally:
                if not acquired and waiter in self._waiters:
                    self._waiters.remove(waiter)
                    self._condition.notify_all()
        try:
            yield
        finally:
            async with self._condition:
                self._active_global -= 1
                active = self._active_by_key.get(route_provider_key, 0) - 1
                if active > 0:
                    self._active_by_key[route_provider_key] = active
                else:
                    self._active_by_key.pop(route_provider_key, None)
                self._condition.notify_all()

    def _selected(self, waiter: _Waiter) -> bool:
        runnable = [item for item in self._waiters if self._has_capacity(item)]
        if not runnable:
            return False
        alternate = [
            item
            for item in runnable
            if item.account_id != self._last_account_id
        ]
        selected = alternate[0] if alternate else runnable[0]
        return selected.marker is waiter.marker

    def _has_capacity(self, waiter: _Waiter) -> bool:
        return (
            self._active_global < self._global_limit
            and self._active_by_key.get(waiter.route_provider_key, 0)
            < waiter.limit
        )


def _queue_timeout() -> ProviderCallError:
    return ProviderCallError(
        ProviderFailureCategory.TIMEOUT,
        "AI 执行等待并发名额超时",
        request_sent=False,
    )


__all__ = ["AIExecutionConcurrencyGate"]
