from __future__ import annotations

from collections.abc import Mapping

from services.events import RuntimeEventDraft

from .constants import SYSTEM_AI_TOPIC
from .unit_of_work import AIConfigurationTransaction


def append_system_ai_event(
    transaction: AIConfigurationTransaction,
    *,
    event_type: str,
    resource_type: str,
    resource_id: str,
    revision: int,
    invalidations: tuple[str, ...],
    values: Mapping[str, object] | None = None,
) -> None:
    transaction.events.append(
        transaction.session,
        RuntimeEventDraft(
            event_type=event_type,
            topic=SYSTEM_AI_TOPIC,
            aggregate_type=resource_type,
            aggregate_id=resource_id,
            revision=revision,
            payload={
                "invalidations": list(invalidations),
                "values": dict(values or {}),
            },
        ),
    )


def append_account_ai_event(
    transaction: AIConfigurationTransaction,
    *,
    account_id: str,
    event_type: str,
    recipe_id: str,
    revision: int,
    invalidations: tuple[str, ...],
    values: Mapping[str, object] | None = None,
) -> None:
    transaction.events.append(
        transaction.session,
        RuntimeEventDraft(
            event_type=event_type,
            topic=f"account:{account_id}:ai-recipe",
            account_id=account_id,
            aggregate_type="account_ai_recipe",
            aggregate_id=recipe_id,
            revision=revision,
            payload={
                "invalidations": list(invalidations),
                "values": dict(values or {}),
            },
        ),
    )

