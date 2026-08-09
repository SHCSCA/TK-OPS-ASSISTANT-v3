from __future__ import annotations

from typing import Any

from services.events.contracts import RuntimeEventDto
from services.events.topics import (
    SYSTEM_AI_TOPIC,
    SYSTEM_BOOTSTRAP_TOPIC,
    SYSTEM_CONFIG_TOPIC,
    SYSTEM_HEALTH_TOPIC,
    SYSTEM_TASKS_TOPIC,
)

LEGACY_SYSTEM_EVENT_ALLOWLIST: dict[str, frozenset[str]] = {
    SYSTEM_BOOTSTRAP_TOPIC: frozenset(
        {
            "bootstrap.license.changed",
            "bootstrap.directories.changed",
        }
    ),
    SYSTEM_HEALTH_TOPIC: frozenset({"runtime.health.updated"}),
    SYSTEM_CONFIG_TOPIC: frozenset({"config.changed"}),
    SYSTEM_AI_TOPIC: frozenset(
        {
            "provider.updated",
            "provider.credential.updated",
            "provider.health.updated",
            "model.updated",
            "model.capability.updated",
            "prompt.profile.updated",
            "prompt.profile.activated",
            "composition.template.updated",
            "composition.template.activated",
            "ai.config.changed",
        }
    ),
    SYSTEM_TASKS_TOPIC: frozenset(
        {
            "task.queued",
            "task.started",
            "task.progress",
            "task.cancelling",
            "task.completed",
            "task.failed",
        }
    ),
}

LEGACY_SAFE_PAYLOAD_FIELDS: dict[str, frozenset[str]] = {
    "bootstrap.license.changed": frozenset({"status", "revision"}),
    "bootstrap.directories.changed": frozenset({"status", "revision"}),
    "runtime.health.updated": frozenset(
        {"status", "version", "checkedAt", "revision"}
    ),
    "config.changed": frozenset(
        {"scope", "revision", "updatedAt", "changedKeys"}
    ),
    "provider.updated": frozenset(
        {"providerId", "enabled", "healthStatus", "revision"}
    ),
    "provider.credential.updated": frozenset(
        {"providerId", "configured", "revision"}
    ),
    "provider.health.updated": frozenset(
        {"providerId", "healthStatus", "checkedAt", "revision"}
    ),
    "model.updated": frozenset(
        {"modelProfileId", "providerProfileId", "enabled", "revision"}
    ),
    "model.capability.updated": frozenset(
        {"modelProfileId", "capabilityKey", "availability", "revision"}
    ),
    "prompt.profile.updated": frozenset(
        {"profileKey", "version", "status", "revision"}
    ),
    "prompt.profile.activated": frozenset(
        {"profileKey", "version", "revision"}
    ),
    "composition.template.updated": frozenset(
        {"templateKey", "version", "status", "revision"}
    ),
    "composition.template.activated": frozenset(
        {"templateKey", "version", "revision"}
    ),
    "ai.config.changed": frozenset(
        {
            "configVersion",
            "revision",
            "reason",
            "providerIds",
            "capabilityIds",
        }
    ),
    "task.queued": frozenset(
        {"taskId", "taskType", "status", "progress", "revision"}
    ),
    "task.started": frozenset(
        {"taskId", "taskType", "status", "progress", "revision"}
    ),
    "task.progress": frozenset(
        {"taskId", "taskType", "status", "progress", "revision"}
    ),
    "task.cancelling": frozenset(
        {"taskId", "taskType", "status", "progress", "revision"}
    ),
    "task.completed": frozenset(
        {
            "taskId",
            "taskType",
            "status",
            "progress",
            "completionKind",
            "revision",
        }
    ),
    "task.failed": frozenset(
        {
            "taskId",
            "taskType",
            "status",
            "progress",
            "failureKind",
            "errorCode",
            "revision",
        }
    ),
}


def is_legacy_system_event(event: RuntimeEventDto) -> bool:
    if event.account_id is not None:
        return False
    return event.event_type in LEGACY_SYSTEM_EVENT_ALLOWLIST.get(
        event.topic,
        frozenset(),
    )


def to_legacy_payload(event: RuntimeEventDto) -> dict[str, Any]:
    if not is_legacy_system_event(event):
        raise ValueError("该事件不在 legacy 系统事件白名单内")
    allowed_fields = LEGACY_SAFE_PAYLOAD_FIELDS[event.event_type]
    return {
        "schema_version": 1,
        "type": event.event_type,
        **{
            key: value
            for key, value in event.payload.items()
            if key in allowed_fields
        },
    }
