from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from typing import Any, Mapping
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from repositories.runtime_event_repository import (
    RuntimeEventRecord,
    RuntimeEventRepository,
)
from services.events.contracts import (
    ReplayResolution,
    RuntimeEventDraft,
    RuntimeEventDto,
    RuntimeEventInput,
    TopicCursor,
)
from services.events.errors import (
    AccountScopeMismatchError,
    CursorMismatchError,
    EventValidationError,
)
from services.events.topics import validate_stable_id, validate_topic_scope

log = logging.getLogger(__name__)

_EVENT_TYPE_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$")
_MAX_EVENT_TYPE_LENGTH = 128
_MAX_STABLE_ID_LENGTH = 128


class RuntimeEventService:
    """统一追加、验证和重放 Runtime 事件。"""

    def __init__(
        self,
        repository: RuntimeEventRepository,
        *,
        replay_limit: int,
    ) -> None:
        if replay_limit < 1:
            raise ValueError("事件重放上限必须大于 0")
        self._repository = repository
        self._replay_limit = replay_limit

    def append(self, session: Session, event: RuntimeEventInput) -> None:
        """实现任务服务的 EventSink 协议，事务由调用方持有。"""

        self.append_and_get(session, event)

    def append_and_get(
        self,
        session: Session,
        event: RuntimeEventInput,
    ) -> RuntimeEventDto:
        draft = self._coerce_input(event)
        values = self._validated_values(draft)
        record = self._repository.append(session, **values)
        return RuntimeEventDto.from_record(record)

    def append_standalone(self, event: RuntimeEventDraft) -> RuntimeEventDto:
        values = self._validated_values(event)
        record = self._repository.append_committed(**values)
        return RuntimeEventDto.from_record(record)

    def append_standalone_idempotent(
        self,
        event: RuntimeEventDraft,
    ) -> RuntimeEventDto:
        """使用稳定事件 ID 重放可恢复的文件或安全存储操作。"""

        if event.event_id is None:
            raise EventValidationError("幂等事件必须提供稳定事件 ID。")
        values = self._validated_values(event)
        existing = self._repository.get(event.event_id)
        if existing is not None:
            return self._match_idempotent_event(existing, values)
        try:
            record = self._repository.append_committed(**values)
        except IntegrityError:
            raced = self._repository.get(event.event_id)
            if raced is None:
                raise
            return self._match_idempotent_event(raced, values)
        return RuntimeEventDto.from_record(record)

    def resolve_replay(self, cursor: TopicCursor) -> ReplayResolution:
        validate_topic_scope_from_cursor(cursor.topic)
        if (cursor.last_event_id is None) != (cursor.after_sequence is None):
            raise CursorMismatchError("事件 ID 与 sequence 必须同时提供或同时为空。")
        if cursor.after_sequence is not None and cursor.after_sequence < 0:
            raise CursorMismatchError("事件 sequence 不得小于 0。")

        snapshot = self._repository.load_replay_snapshot(
            topic=cursor.topic,
            last_event_id=cursor.last_event_id,
            after_sequence=cursor.after_sequence,
            limit=self._replay_limit,
        )
        if cursor.after_sequence is None:
            return ReplayResolution(
                topic=cursor.topic,
                current_sequence=snapshot.current_sequence,
                events=(),
                sync_required=False,
            )

        assert cursor.last_event_id is not None
        cursor_event = snapshot.cursor_event
        minimum_after_sequence = max(
            0,
            snapshot.current_sequence - self._replay_limit,
        )
        if cursor_event is None:
            if cursor.after_sequence < minimum_after_sequence:
                return self._sync_required(cursor.topic, snapshot.current_sequence)
            raise CursorMismatchError()
        if cursor_event.topic != cursor.topic:
            raise AccountScopeMismatchError()
        if cursor_event.sequence != cursor.after_sequence:
            raise CursorMismatchError()
        if cursor.after_sequence > snapshot.current_sequence:
            raise CursorMismatchError("事件 sequence 超出当前 Topic 位置。")
        if cursor.after_sequence < minimum_after_sequence:
            return self._sync_required(cursor.topic, snapshot.current_sequence)

        rows = snapshot.events_after_cursor
        if len(rows) > self._replay_limit:
            return self._sync_required(cursor.topic, snapshot.current_sequence)
        expected_sequence = cursor.after_sequence + 1
        for row in rows:
            if row.sequence != expected_sequence:
                return self._sync_required(cursor.topic, snapshot.current_sequence)
            expected_sequence += 1
        if expected_sequence - 1 != snapshot.current_sequence:
            return self._sync_required(cursor.topic, snapshot.current_sequence)

        return ReplayResolution(
            topic=cursor.topic,
            current_sequence=snapshot.current_sequence,
            events=tuple(RuntimeEventDto.from_record(row) for row in rows),
            sync_required=False,
        )

    @staticmethod
    def to_dto(record: RuntimeEventRecord) -> RuntimeEventDto:
        validate_topic_scope(record.topic, record.account_id)
        return RuntimeEventDto.from_record(record)

    @staticmethod
    def _match_idempotent_event(
        record: RuntimeEventRecord,
        values: Mapping[str, Any],
    ) -> RuntimeEventDto:
        expected = {
            "event_id": values["event_id"],
            "topic": values["topic"],
            "event_type": values["event_type"],
            "account_id": values["account_id"],
            "aggregate_type": values["aggregate_type"],
            "aggregate_id": values["aggregate_id"],
            "task_id": values["task_id"],
            "log_id": values["log_id"],
            "revision": values["revision"],
            "payload": values["payload"],
        }
        actual = {
            "event_id": record.event_id,
            "topic": record.topic,
            "event_type": record.event_type,
            "account_id": record.account_id,
            "aggregate_type": record.aggregate_type,
            "aggregate_id": record.aggregate_id,
            "task_id": record.task_id,
            "log_id": record.log_id,
            "revision": record.revision,
            "payload": record.payload,
        }
        if actual != expected:
            raise EventValidationError(
                "同一幂等事件 ID 对应了不同的事件内容。"
            )
        return RuntimeEventDto.from_record(record)

    @staticmethod
    def _sync_required(topic: str, current_sequence: int) -> ReplayResolution:
        return ReplayResolution(
            topic=topic,
            current_sequence=current_sequence,
            events=(),
            sync_required=True,
            sync_reason="WS_EVENT_GAP",
        )

    def _validated_values(self, event: RuntimeEventDraft) -> dict[str, Any]:
        event_type = event.event_type.strip()
        if (
            len(event_type) > _MAX_EVENT_TYPE_LENGTH
            or not _EVENT_TYPE_PATTERN.fullmatch(event_type)
        ):
            raise EventValidationError("事件类型格式无效。")
        if event_type != event.event_type:
            raise EventValidationError("事件类型不得包含首尾空白。")
        parsed_topic = validate_topic_scope(event.topic, event.account_id)
        if parsed_topic.value != event.topic:
            raise EventValidationError("Topic 不得包含首尾空白。")
        self._validate_optional_id(event.event_id, "事件 ID")
        self._validate_optional_id(event.aggregate_type, "资源类型")
        self._validate_optional_id(event.aggregate_id, "资源 ID")
        self._validate_optional_id(event.task_id, "任务 ID")
        self._validate_optional_id(event.log_id, "日志 ID")
        if event.revision is not None and (
            isinstance(event.revision, bool)
            or not isinstance(event.revision, int)
            or event.revision < 1
        ):
            raise EventValidationError("事件修订号必须大于 0。")
        if not isinstance(event.payload, Mapping):
            raise EventValidationError("事件 payload 必须是对象。")
        payload = dict(event.payload)
        if any(not isinstance(key, str) for key in payload):
            raise EventValidationError("事件 payload 的字段名必须是字符串。")
        try:
            json.dumps(payload, ensure_ascii=False, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise EventValidationError("事件 payload 必须是有效 JSON 对象。") from exc

        return {
            "event_id": event.event_id or f"evt_{uuid4().hex}",
            "topic": parsed_topic.value,
            "event_type": event_type,
            "account_id": event.account_id,
            "aggregate_type": event.aggregate_type,
            "aggregate_id": event.aggregate_id,
            "task_id": event.task_id,
            "log_id": event.log_id,
            "revision": event.revision,
            "payload": payload,
            "occurred_at": event.occurred_at or _utc_now(),
        }

    @staticmethod
    def _coerce_input(event: RuntimeEventInput) -> RuntimeEventDraft:
        return RuntimeEventDraft(
            event_type=event.event_type,
            topic=event.topic,
            account_id=event.account_id,
            aggregate_type=getattr(event, "aggregate_type", None),
            aggregate_id=getattr(event, "aggregate_id", None),
            task_id=event.task_id,
            log_id=getattr(event, "log_id", None),
            revision=event.revision,
            payload=event.payload,
            event_id=getattr(event, "event_id", None),
            occurred_at=getattr(event, "occurred_at", None),
        )

    @staticmethod
    def _validate_optional_id(value: str | None, label: str) -> None:
        if value is None:
            return
        if len(value) > _MAX_STABLE_ID_LENGTH:
            raise EventValidationError(f"{label} 格式无效。")
        validate_stable_id(value, label)


def validate_topic_scope_from_cursor(topic: str) -> None:
    parsed = validate_topic_scope(topic, _account_id_from_topic(topic))
    if parsed.value != topic:
        raise EventValidationError("Topic 不得包含首尾空白。")


def _account_id_from_topic(topic: str) -> str | None:
    if not topic.startswith("account:"):
        return None
    parts = topic.split(":", 2)
    return parts[1] if len(parts) == 3 else None


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
