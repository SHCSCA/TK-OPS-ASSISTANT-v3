from __future__ import annotations

import asyncio
import threading
from typing import cast

import pytest

from repositories.runtime_event_repository import (
    RuntimeEventRecord,
    RuntimeEventRepository,
)
from services.events import RuntimeEventDto, RuntimeEventPublisher, RuntimeEventService


class _PublisherRepository:
    def __init__(self, records: list[RuntimeEventRecord]) -> None:
        self.records = records
        self.marked_event_ids: list[str] = []

    def list_unpublished(self, *, limit: int) -> list[RuntimeEventRecord]:
        return self.records[:limit]

    def mark_published(self, event_ids: list[str]) -> None:
        self.marked_event_ids.extend(event_ids)


class _BlockingPublisherRepository(_PublisherRepository):
    def __init__(self) -> None:
        super().__init__([])
        self.started = threading.Event()
        self.release = threading.Event()

    def list_unpublished(self, *, limit: int) -> list[RuntimeEventRecord]:
        self.started.set()
        self.release.wait(timeout=2)
        return super().list_unpublished(limit=limit)


class _PublisherEventService:
    @staticmethod
    def to_dto(record: RuntimeEventRecord) -> RuntimeEventDto:
        return RuntimeEventDto.from_record(record)


@pytest.mark.asyncio
async def test_publisher_quarantines_only_the_known_legacy_migration_event() -> None:
    legacy_record = RuntimeEventRecord(
        event_id="migration:0016_p0_backfill",
        topic="system.migrations",
        sequence=1,
        event_type="migration.legacy_backfill_completed",
        account_id=None,
        aggregate_type=None,
        aggregate_id=None,
        task_id=None,
        log_id=None,
        revision=None,
        payload={},
        occurred_at="2026-07-26T00:00:00Z",
        published_at=None,
    )
    repository = _PublisherRepository([legacy_record])
    delivered: list[RuntimeEventDto] = []

    async def deliver(event: RuntimeEventDto) -> None:
        delivered.append(event)

    publisher = RuntimeEventPublisher(
        cast(RuntimeEventRepository, repository),
        cast(RuntimeEventService, object()),
        deliver,
    )

    assert await publisher.publish_pending() == 1
    assert delivered == []
    assert repository.marked_event_ids == ["migration:0016_p0_backfill"]


@pytest.mark.asyncio
async def test_publisher_cancellation_does_not_wait_for_stuck_database_thread(
) -> None:
    repository = _BlockingPublisherRepository()

    async def deliver(_event: RuntimeEventDto) -> None:
        return None

    publisher = RuntimeEventPublisher(
        cast(RuntimeEventRepository, repository),
        cast(RuntimeEventService, object()),
        deliver,
        blocking_cancel_grace_seconds=0.01,
    )
    handle = asyncio.create_task(publisher.publish_pending())
    async with asyncio.timeout(1):
        while not repository.started.is_set():
            await asyncio.sleep(0.01)

    handle.cancel()
    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(handle, timeout=0.2)

    assert not repository.release.is_set()
    repository.release.set()
    await asyncio.sleep(0.01)


@pytest.mark.asyncio
async def test_publisher_timeout_keeps_unconfirmed_event_for_replay() -> None:
    record = RuntimeEventRecord(
        event_id="evt_shutdown_timeout",
        topic="system:tasks",
        sequence=1,
        event_type="task.started",
        account_id=None,
        aggregate_type="runtime_task",
        aggregate_id="task_shutdown_timeout",
        task_id="task_shutdown_timeout",
        log_id=None,
        revision=2,
        payload={},
        occurred_at="2026-07-26T00:00:00Z",
        published_at=None,
    )
    repository = _PublisherRepository([record])
    delivery_started = asyncio.Event()

    async def deliver(_event: RuntimeEventDto) -> None:
        delivery_started.set()
        await asyncio.Future()

    publisher = RuntimeEventPublisher(
        cast(RuntimeEventRepository, repository),
        cast(RuntimeEventService, _PublisherEventService()),
        deliver,
    )

    published = await publisher.publish_pending(timeout_seconds=0.01)

    assert delivery_started.is_set()
    assert published == 0
    assert repository.marked_event_ids == []
