from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from domain.models.runtime_task import RuntimeTask
from repositories.runtime_task_repository import RuntimeTaskRepository
from services.tasks.errors import (
    task_not_found,
    task_scope_mismatch,
    task_state_conflict,
)
from services.tasks.events import TaskEvent, TaskEventSink
from services.tasks.types import (
    JsonValue,
    RuntimeTaskRecord,
    TaskScope,
)

Clock = Callable[[], datetime]


class TaskServiceSupport:
    """集中维护任务事务内查询、事件和时钟辅助。"""

    def __init__(
        self,
        *,
        repository: RuntimeTaskRepository,
        event_sink: TaskEventSink,
        clock: Clock,
    ) -> None:
        self._repository = repository
        self._event_sink = event_sink
        self._clock = clock

    def now(self) -> datetime:
        now = self._clock()
        if now.tzinfo is None:
            return now.replace(tzinfo=UTC)
        return now.astimezone(UTC)

    def now_text(self) -> str:
        return to_utc_text(self.now())

    def require_scoped_record(
        self,
        session: Session,
        task_id: str,
        *,
        scope: TaskScope,
        account_id: str | None,
    ) -> RuntimeTaskRecord:
        task = self._repository.get_scoped(
            session,
            task_id,
            scope=scope,
            account_id=account_id,
        )
        if task is not None:
            return self._repository.to_record(task)
        if self._repository.get_any(session, task_id) is not None:
            raise task_scope_mismatch()
        raise task_not_found()

    def require_any(self, session: Session, task_id: str) -> RuntimeTask:
        task = self._repository.get_any(session, task_id)
        if task is None:
            raise task_not_found()
        return task

    def require_any_record(
        self,
        session: Session,
        task_id: str,
    ) -> RuntimeTaskRecord:
        return self._repository.to_record(self.require_any(session, task_id))

    @staticmethod
    def require_transition(
        record: RuntimeTaskRecord | None,
    ) -> RuntimeTaskRecord:
        if record is None:
            raise task_state_conflict()
        return record

    def append_event(
        self,
        session: Session,
        record: RuntimeTaskRecord,
        event_type: str,
    ) -> None:
        self._event_sink.append(
            session,
            TaskEvent(
                event_type=event_type,
                topic=self.topic_for(record),
                account_id=record.account_id,
                task_id=record.id,
                revision=record.revision,
                payload=self.event_payload(record),
            ),
        )

    @staticmethod
    def event_payload(record: RuntimeTaskRecord) -> dict[str, JsonValue]:
        return {
            "taskId": record.id,
            "scope": record.scope.value,
            "accountId": record.account_id,
            "taskType": record.task_type,
            "status": record.status.value,
            "completionKind": (
                record.completion_kind.value
                if record.completion_kind is not None
                else None
            ),
            "failureKind": (
                record.failure_kind.value
                if record.failure_kind is not None
                else None
            ),
            "progress": record.progress,
            "cancellable": record.cancellable,
            "resultRef": record.result_ref,
            "errorCode": record.error_code,
            "logId": record.error_log_id,
            "attempt": record.attempt,
            "retryOfTaskId": record.retry_of_task_id,
            "revision": record.revision,
            "createdAt": record.created_at,
            "startedAt": record.started_at,
            "completedAt": record.completed_at,
            "updatedAt": record.updated_at,
        }

    @staticmethod
    def topic_for(record: RuntimeTaskRecord) -> str:
        if record.scope is TaskScope.SYSTEM:
            return "system:tasks"
        assert record.account_id is not None
        return f"account:{record.account_id}:tasks"

    @staticmethod
    def validate_scope(scope: TaskScope, account_id: str | None) -> None:
        if scope is TaskScope.SYSTEM and account_id is not None:
            raise task_scope_mismatch()
        if scope is TaskScope.ACCOUNT and not (account_id or "").strip():
            raise task_scope_mismatch()

    @staticmethod
    def scope_key(scope: TaskScope, account_id: str | None) -> str:
        return "system" if scope is TaskScope.SYSTEM else f"account:{account_id}"


def utc_now() -> datetime:
    return datetime.now(UTC)


def to_utc_text(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
