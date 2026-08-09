from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol

from repositories.runtime_event_repository import RuntimeEventRecord


class RuntimeEventInput(Protocol):
    event_type: str
    topic: str
    account_id: str | None
    task_id: str | None
    revision: int | None
    payload: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class RuntimeEventDraft:
    event_type: str
    topic: str
    payload: Mapping[str, Any] = field(default_factory=dict)
    account_id: str | None = None
    aggregate_type: str | None = None
    aggregate_id: str | None = None
    task_id: str | None = None
    log_id: str | None = None
    revision: int | None = None
    event_id: str | None = None
    occurred_at: str | None = None


@dataclass(frozen=True, slots=True)
class RuntimeEventDto:
    event_id: str
    event_type: str
    topic: str
    sequence: int
    occurred_at: str
    account_id: str | None
    resource_type: str | None
    resource_id: str | None
    task_id: str | None
    revision: int | None
    payload: dict[str, Any]
    schema_version: int = 1

    @classmethod
    def from_record(cls, record: RuntimeEventRecord) -> RuntimeEventDto:
        return cls(
            event_id=record.event_id,
            event_type=record.event_type,
            topic=record.topic,
            sequence=record.sequence,
            occurred_at=record.occurred_at,
            account_id=record.account_id,
            resource_type=record.aggregate_type,
            resource_id=record.aggregate_id,
            task_id=record.task_id,
            revision=record.revision,
            payload=record.payload,
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "schemaVersion": self.schema_version,
            "eventId": self.event_id,
            "eventType": self.event_type,
            "topic": self.topic,
            "sequence": self.sequence,
            "occurredAt": self.occurred_at,
            "accountId": self.account_id,
            "resourceType": self.resource_type,
            "resourceId": self.resource_id,
            "taskId": self.task_id,
            "revision": self.revision,
            "payload": self.payload,
        }


@dataclass(frozen=True, slots=True)
class TopicCursor:
    topic: str
    last_event_id: str | None
    after_sequence: int | None


@dataclass(frozen=True, slots=True)
class ReplayResolution:
    topic: str
    current_sequence: int
    events: tuple[RuntimeEventDto, ...]
    sync_required: bool
    sync_reason: str | None = None
