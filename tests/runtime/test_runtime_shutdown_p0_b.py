from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import cast

import pytest

from app.runtime_background import RuntimeBackgroundServices
from app.runtime_kernel import RuntimeKernel


class _BlockingTaskRunner:
    def __init__(self) -> None:
        self.timeout_seconds: float | None = None

    async def shutdown(self, *, timeout_seconds: float | None = None) -> None:
        self.timeout_seconds = timeout_seconds
        await asyncio.Future()


class _UnreachedEventPublisher:
    def __init__(self) -> None:
        self.publish_count = 0

    async def publish_pending(
        self,
        *,
        timeout_seconds: float | None = None,
    ) -> int:
        self.publish_count += 1
        return 0


@pytest.mark.asyncio
async def test_runtime_background_shutdown_obeys_global_deadline() -> None:
    runner = _BlockingTaskRunner()
    publisher = _UnreachedEventPublisher()
    kernel = cast(
        RuntimeKernel,
        SimpleNamespace(
            task_runner=runner,
            event_publisher=publisher,
            policy=SimpleNamespace(shutdown_grace_seconds=0.02),
        ),
    )
    services = RuntimeBackgroundServices(kernel)
    before = asyncio.get_running_loop().time()

    await services.shutdown()
    await asyncio.sleep(0)

    elapsed = asyncio.get_running_loop().time() - before
    assert elapsed < 0.2
    assert runner.timeout_seconds is not None
    assert runner.timeout_seconds <= 0.02
    assert publisher.publish_count == 0
