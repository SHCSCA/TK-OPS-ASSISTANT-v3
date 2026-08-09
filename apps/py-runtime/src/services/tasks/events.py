from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from sqlalchemy.orm import Session

from services.tasks.types import JsonValue


@dataclass(frozen=True, slots=True)
class TaskEvent:
    event_type: str
    topic: str
    account_id: str | None
    task_id: str
    revision: int
    payload: dict[str, JsonValue]


class TaskEventSink(Protocol):
    """在调用方事务内追加任务 outbox 事件。"""

    def append(self, session: Session, event: TaskEvent) -> None: ...
