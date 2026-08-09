from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Mapping, Sequence

from sqlalchemy import func, select, text, update
from sqlalchemy.orm import Session, sessionmaker

from domain.models.runtime_event import RuntimeEvent

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class RuntimeEventRecord:
    event_id: str
    topic: str
    sequence: int
    event_type: str
    account_id: str | None
    aggregate_type: str | None
    aggregate_id: str | None
    task_id: str | None
    log_id: str | None
    revision: int | None
    payload: dict[str, Any]
    occurred_at: str
    published_at: str | None


@dataclass(frozen=True, slots=True)
class ReplaySnapshot:
    topic: str
    current_sequence: int
    cursor_event: RuntimeEventRecord | None
    events_after_cursor: tuple[RuntimeEventRecord, ...]


class RuntimeEventRepository:
    """持久化 Runtime outbox，并把事务边界保留给调用方。"""

    def __init__(self, *, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def append(
        self,
        session: Session,
        *,
        event_id: str,
        topic: str,
        event_type: str,
        account_id: str | None,
        aggregate_type: str | None,
        aggregate_id: str | None,
        task_id: str | None,
        log_id: str | None,
        revision: int | None,
        payload: Mapping[str, Any],
        occurred_at: str,
    ) -> RuntimeEventRecord:
        """在调用方事务内分配 Topic sequence 并追加事件，不提交事务。"""

        try:
            payload_json = json.dumps(
                dict(payload),
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
                sort_keys=True,
            )
            self._acquire_sqlite_write_lock(session)
            sequence = self._next_sequence(session, topic)
            row = RuntimeEvent(
                event_id=event_id,
                topic=topic,
                sequence=sequence,
                event_type=event_type,
                account_id=account_id,
                aggregate_type=aggregate_type,
                aggregate_id=aggregate_id,
                task_id=task_id,
                log_id=log_id,
                revision=revision,
                payload_json=payload_json,
                occurred_at=occurred_at,
                published_at=None,
            )
            session.add(row)
            session.flush([row])
            return self._to_record(row)
        except Exception:
            log.exception(
                "追加 Runtime 事件失败",
                extra={"topic": topic, "event_type": event_type, "event_id": event_id},
            )
            raise

    def append_committed(self, **values: Any) -> RuntimeEventRecord:
        """为不依附业务写入的系统事件创建独立事务。"""

        try:
            with self._session_factory() as session:
                with session.begin():
                    return self.append(session, **values)
        except Exception:
            log.exception(
                "提交独立 Runtime 事件失败",
                extra={
                    "topic": values.get("topic"),
                    "event_type": values.get("event_type"),
                    "event_id": values.get("event_id"),
                },
            )
            raise

    def get(self, event_id: str) -> RuntimeEventRecord | None:
        try:
            with self._session_factory() as session:
                row = session.get(RuntimeEvent, event_id)
                return self._to_record(row) if row is not None else None
        except Exception:
            log.exception(
                "读取 Runtime 事件失败",
                extra={"event_id": event_id},
            )
            raise

    def load_replay_snapshot(
        self,
        *,
        topic: str,
        last_event_id: str | None,
        after_sequence: int | None,
        limit: int,
    ) -> ReplaySnapshot:
        try:
            with self._session_factory() as session:
                current_sequence = int(
                    session.scalar(
                        select(func.coalesce(func.max(RuntimeEvent.sequence), 0)).where(
                            RuntimeEvent.topic == topic
                        )
                    )
                    or 0
                )
                cursor_row = (
                    session.get(RuntimeEvent, last_event_id)
                    if last_event_id is not None
                    else None
                )
                replay_rows: Sequence[RuntimeEvent] = ()
                if after_sequence is not None:
                    replay_rows = session.scalars(
                        select(RuntimeEvent)
                        .where(
                            RuntimeEvent.topic == topic,
                            RuntimeEvent.sequence > after_sequence,
                        )
                        .order_by(RuntimeEvent.sequence.asc())
                        .limit(limit + 1)
                    ).all()
                return ReplaySnapshot(
                    topic=topic,
                    current_sequence=current_sequence,
                    cursor_event=(
                        self._to_record(cursor_row) if cursor_row is not None else None
                    ),
                    events_after_cursor=tuple(
                        self._to_record(row) for row in replay_rows
                    ),
                )
        except Exception:
            log.exception(
                "读取 Runtime 事件重放快照失败",
                extra={"topic": topic, "last_event_id": last_event_id},
            )
            raise

    def list_unpublished(self, *, limit: int) -> list[RuntimeEventRecord]:
        try:
            with self._session_factory() as session:
                rows = session.scalars(
                    select(RuntimeEvent)
                    .where(RuntimeEvent.published_at.is_(None))
                    .order_by(
                        RuntimeEvent.topic.asc(),
                        RuntimeEvent.sequence.asc(),
                    )
                    .limit(limit)
                ).all()
                return [self._to_record(row) for row in rows]
        except Exception:
            log.exception("读取待发布 Runtime 事件失败")
            raise

    def mark_published(
        self,
        event_ids: Sequence[str],
        *,
        published_at: str | None = None,
    ) -> None:
        if not event_ids:
            return
        resolved_time = published_at or _utc_now()
        try:
            with self._session_factory() as session:
                with session.begin():
                    session.execute(
                        update(RuntimeEvent)
                        .where(
                            RuntimeEvent.event_id.in_(tuple(event_ids)),
                            RuntimeEvent.published_at.is_(None),
                        )
                        .values(published_at=resolved_time)
                    )
        except Exception:
            log.exception(
                "标记 Runtime 事件已发布失败",
                extra={"event_count": len(event_ids)},
            )
            raise

    @staticmethod
    def _acquire_sqlite_write_lock(session: Session) -> None:
        # Runtime 当前固定使用 SQLite；先进入写事务，避免并发 MAX(sequence) 竞争。
        if session.get_bind().dialect.name == "sqlite":
            session.execute(text("UPDATE runtime_events SET sequence = sequence WHERE 0"))

    @staticmethod
    def _next_sequence(session: Session, topic: str) -> int:
        current = session.scalar(
            select(func.coalesce(func.max(RuntimeEvent.sequence), 0)).where(
                RuntimeEvent.topic == topic
            )
        )
        return int(current or 0) + 1

    @staticmethod
    def _to_record(row: RuntimeEvent) -> RuntimeEventRecord:
        payload = json.loads(row.payload_json)
        if not isinstance(payload, dict):
            raise ValueError("Runtime 事件 payload 必须是 JSON 对象")
        return RuntimeEventRecord(
            event_id=row.event_id,
            topic=row.topic,
            sequence=row.sequence,
            event_type=row.event_type,
            account_id=row.account_id,
            aggregate_type=row.aggregate_type,
            aggregate_id=row.aggregate_id,
            task_id=row.task_id,
            log_id=row.log_id,
            revision=row.revision,
            payload=payload,
            occurred_at=row.occurred_at,
            published_at=row.published_at,
        )


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
