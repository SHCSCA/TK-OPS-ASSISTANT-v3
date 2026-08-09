from __future__ import annotations

from collections.abc import Mapping

from services.events import RuntimeEventDraft

from .constants import SYSTEM_AI_TOPIC
from .unit_of_work import AIConfigurationTransaction


def append_task_ai_event(
    transaction: AIConfigurationTransaction,
    *,
    event_type: str,
    resource_type: str,
    resource_id: str,
    task_id: str,
    revision: int,
    invalidations: tuple[str, ...],
    values: Mapping[str, object] | None = None,
    log_id: str | None = None,
) -> None:
    transaction.events.append(
        transaction.session,
        RuntimeEventDraft(
            event_type=event_type,
            topic=SYSTEM_AI_TOPIC,
            aggregate_type=resource_type,
            aggregate_id=resource_id,
            task_id=task_id,
            log_id=log_id,
            revision=revision,
            payload={
                "invalidations": list(invalidations),
                "values": dict(values or {}),
            },
        ),
    )


def append_task_ai_config_changed(
    transaction: AIConfigurationTransaction,
    *,
    resource_type: str,
    resource_id: str,
    task_id: str,
    revision: int,
    invalidations: tuple[str, ...],
    values: Mapping[str, object] | None = None,
    log_id: str | None = None,
) -> None:
    append_task_ai_event(
        transaction,
        event_type="ai.config.changed",
        resource_type=resource_type,
        resource_id=resource_id,
        task_id=task_id,
        revision=revision,
        invalidations=invalidations,
        values=values,
        log_id=log_id,
    )
