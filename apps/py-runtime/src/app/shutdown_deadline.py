from __future__ import annotations

import asyncio
import math
from dataclasses import dataclass
from typing import TypeVar

_T = TypeVar("_T")


@dataclass(frozen=True, slots=True)
class ShutdownDeadline:
    """用单调时钟统一约束 Runtime 停机阶段的剩余预算。"""

    expires_at: float

    @classmethod
    def start(cls, timeout_seconds: float) -> ShutdownDeadline:
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError("Runtime 停机宽限时间必须是大于零的有限数")
        return cls(
            expires_at=asyncio.get_running_loop().time() + timeout_seconds
        )

    def remaining_seconds(self) -> float:
        return max(
            0.0,
            self.expires_at - asyncio.get_running_loop().time(),
        )

    def capped(self, timeout_seconds: float) -> ShutdownDeadline:
        if not math.isfinite(timeout_seconds) or timeout_seconds < 0:
            raise ValueError("Runtime 停机阶段预算必须是非负有限数")
        now = asyncio.get_running_loop().time()
        return ShutdownDeadline(
            expires_at=min(self.expires_at, now + timeout_seconds)
        )


async def wait_task_until(
    handle: asyncio.Task[_T],
    deadline: ShutdownDeadline,
) -> bool:
    """等待任务至统一截止点，不向待处理任务传播超时取消。"""

    if handle.done():
        return True
    remaining = deadline.remaining_seconds()
    if remaining <= 0:
        return handle.done()
    completed, _ = await asyncio.wait({handle}, timeout=remaining)
    return bool(completed)
