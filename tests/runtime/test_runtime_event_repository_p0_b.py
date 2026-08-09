from __future__ import annotations

from pathlib import Path

from sqlalchemy import func, select

from domain.models.runtime_event import RuntimeEvent
from services.events import RuntimeEventDraft
from tests.runtime.runtime_event_test_support import make_runtime_event_stack


def test_append_uses_caller_transaction_and_allocates_sequence_per_topic(
    tmp_path: Path,
) -> None:
    stack = make_runtime_event_stack(tmp_path / "runtime-events.db")
    try:
        with stack.session_factory() as session:
            with session.begin():
                first = stack.service.append_and_get(
                    session,
                    RuntimeEventDraft(
                        event_id="evt_health_1",
                        event_type="runtime.health.updated",
                        topic="system:health",
                        payload={"status": "ready"},
                    ),
                )
                second = stack.service.append_and_get(
                    session,
                    RuntimeEventDraft(
                        event_id="evt_health_2",
                        event_type="runtime.health.updated",
                        topic="system:health",
                        payload={"status": "attention"},
                    ),
                )
                other_topic = stack.service.append_and_get(
                    session,
                    RuntimeEventDraft(
                        event_id="evt_config_1",
                        event_type="config.changed",
                        topic="system:config",
                        payload={"revision": 2},
                    ),
                )

        assert (first.sequence, second.sequence, other_topic.sequence) == (1, 2, 1)

        try:
            with stack.session_factory() as session:
                with session.begin():
                    stack.service.append_and_get(
                        session,
                        RuntimeEventDraft(
                            event_id="evt_rolled_back",
                            event_type="runtime.health.updated",
                            topic="system:health",
                            payload={"status": "failed"},
                        ),
                    )
                    raise RuntimeError("触发事务回滚")
        except RuntimeError:
            pass

        with stack.session_factory() as session:
            rolled_back_count = session.scalar(
                select(func.count())
                .select_from(RuntimeEvent)
                .where(RuntimeEvent.event_id == "evt_rolled_back")
            )
            persisted_count = session.scalar(
                select(func.count()).select_from(RuntimeEvent)
            )

        assert rolled_back_count == 0
        assert persisted_count == 3
    finally:
        stack.engine.dispose()


def test_outbox_marks_only_successfully_published_events(
    tmp_path: Path,
) -> None:
    stack = make_runtime_event_stack(tmp_path / "runtime-outbox.db")
    try:
        event = stack.service.append_standalone(
            RuntimeEventDraft(
                event_id="evt_outbox_1",
                event_type="runtime.health.updated",
                topic="system:health",
                payload={"status": "ready"},
                occurred_at="2026-07-26T00:00:02Z",
            )
        )
        second_event = stack.service.append_standalone(
            RuntimeEventDraft(
                event_id="evt_outbox_2",
                event_type="runtime.health.updated",
                topic="system:health",
                payload={"status": "attention"},
                occurred_at="2026-07-26T00:00:01Z",
            )
        )

        pending = stack.repository.list_unpublished(limit=10)
        assert [item.event_id for item in pending] == [
            event.event_id,
            second_event.event_id,
        ]

        stack.repository.mark_published([event.event_id])

        assert [
            item.event_id for item in stack.repository.list_unpublished(limit=10)
        ] == [second_event.event_id]
    finally:
        stack.engine.dispose()
