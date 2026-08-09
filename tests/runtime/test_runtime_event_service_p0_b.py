from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest
from sqlalchemy.orm import Session

from repositories.runtime_event_repository import RuntimeEventRecord
from services.events import (
    AccountScopeMismatchError,
    CursorMismatchError,
    EventValidationError,
    RuntimeEventDraft,
    RuntimeEventService,
    TopicCursor,
)
from services.tasks.events import TaskEvent, TaskEventSink
from tests.runtime.runtime_event_test_support import make_runtime_event_stack


class _CapturingEventRepository:
    def __init__(self) -> None:
        self.values: dict[str, Any] | None = None

    def append(self, session: Session, **values: Any) -> RuntimeEventRecord:
        self.values = dict(values)
        return RuntimeEventRecord(
            event_id=str(values["event_id"]),
            topic=str(values["topic"]),
            sequence=1,
            event_type=str(values["event_type"]),
            account_id=cast(str | None, values["account_id"]),
            aggregate_type=cast(str | None, values["aggregate_type"]),
            aggregate_id=cast(str | None, values["aggregate_id"]),
            task_id=cast(str | None, values["task_id"]),
            log_id=cast(str | None, values["log_id"]),
            revision=cast(int | None, values["revision"]),
            payload=dict(cast(dict[str, Any], values["payload"])),
            occurred_at=str(values["occurred_at"]),
            published_at=None,
        )


def test_runtime_event_service_implements_task_event_sink_contract() -> None:
    repository = _CapturingEventRepository()
    service = RuntimeEventService(
        cast(Any, repository),
        replay_limit=100,
    )
    sink: TaskEventSink = service

    sink.append(
        cast(Session, object()),
        TaskEvent(
            event_type="task.progress",
            topic="system:tasks",
            account_id=None,
            task_id="task_01",
            revision=2,
            payload={"progress": 0.5},
        ),
    )

    assert repository.values is not None
    assert repository.values["task_id"] == "task_01"
    assert repository.values["revision"] == 2
    assert repository.values["payload"] == {"progress": 0.5}


def test_event_service_replays_each_topic_and_rejects_mismatched_cursor(
    tmp_path: Path,
) -> None:
    stack = make_runtime_event_stack(
        tmp_path / "runtime-replay.db",
        replay_limit=4,
    )
    try:
        health_events = []
        for sequence in range(1, 4):
            health_events.append(
                stack.service.append_standalone(
                    RuntimeEventDraft(
                        event_id=f"evt_health_{sequence}",
                        event_type="runtime.health.updated",
                        topic="system:health",
                        payload={"revision": sequence},
                    )
                )
            )
        config_event = stack.service.append_standalone(
            RuntimeEventDraft(
                event_id="evt_config_1",
                event_type="config.changed",
                topic="system:config",
                payload={"revision": 1},
            )
        )

        replay = stack.service.resolve_replay(
            TopicCursor(
                topic="system:health",
                last_event_id=health_events[0].event_id,
                after_sequence=health_events[0].sequence,
            )
        )

        assert replay.current_sequence == 3
        assert [item.event_id for item in replay.events] == [
            "evt_health_2",
            "evt_health_3",
        ]
        assert replay.sync_required is False

        with pytest.raises(CursorMismatchError):
            stack.service.resolve_replay(
                TopicCursor(
                    topic="system:health",
                    last_event_id=health_events[1].event_id,
                    after_sequence=health_events[0].sequence,
                )
            )

        with pytest.raises(AccountScopeMismatchError):
            stack.service.resolve_replay(
                TopicCursor(
                    topic="system:health",
                    last_event_id=config_event.event_id,
                    after_sequence=config_event.sequence,
                )
            )
    finally:
        stack.engine.dispose()


def test_expired_topic_cursor_requires_http_resynchronization(
    tmp_path: Path,
) -> None:
    stack = make_runtime_event_stack(
        tmp_path / "runtime-replay-expired.db",
        replay_limit=2,
    )
    try:
        events = [
            stack.service.append_standalone(
                RuntimeEventDraft(
                    event_id=f"evt_health_{sequence}",
                    event_type="runtime.health.updated",
                    topic="system:health",
                    payload={"revision": sequence},
                )
            )
            for sequence in range(1, 5)
        ]

        resolution = stack.service.resolve_replay(
            TopicCursor(
                topic="system:health",
                last_event_id=events[0].event_id,
                after_sequence=events[0].sequence,
            )
        )

        assert resolution.sync_required is True
        assert resolution.sync_reason == "WS_EVENT_GAP"
        assert resolution.current_sequence == 4
        assert resolution.events == ()
    finally:
        stack.engine.dispose()


@pytest.mark.parametrize(
    ("topic", "account_id"),
    [
        ("system:health", "acc_a"),
        ("account:acc_a:tasks", None),
        ("account:acc_a:tasks", "acc_b"),
    ],
)
def test_event_topic_scope_is_enforced(
    topic: str,
    account_id: str | None,
) -> None:
    service = RuntimeEventService(cast(Any, object()), replay_limit=10)

    with pytest.raises(AccountScopeMismatchError):
        service.append_and_get(
            cast(Session, object()),
            RuntimeEventDraft(
                event_type="task.progress",
                topic=topic,
                account_id=account_id,
                payload={},
            ),
        )


def test_event_topic_rejects_silent_whitespace_normalization() -> None:
    service = RuntimeEventService(cast(Any, object()), replay_limit=10)

    with pytest.raises(EventValidationError):
        service.append_and_get(
            cast(Session, object()),
            RuntimeEventDraft(
                event_type="runtime.health.updated",
                topic=" system:health ",
                payload={},
            ),
        )
