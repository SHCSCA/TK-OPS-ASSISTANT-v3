from __future__ import annotations

from collections.abc import Mapping, Sequence

from services.accounts.unit_of_work import AccountTransaction
from services.events import RuntimeEventDraft
from services.events.topics import build_account_topic


def append_account_event(
    transaction: AccountTransaction,
    *,
    account_id: str,
    event_type: str,
    aggregate_type: str,
    aggregate_id: str,
    revision: int,
    invalidations: Sequence[str],
    values: Mapping[str, object] | None = None,
    topic_resource: str = "workspace",
) -> None:
    payload = dict(values or {})
    payload["invalidations"] = list(invalidations)
    transaction.events.append(
        transaction.session,
        RuntimeEventDraft(
            event_type=event_type,
            topic=build_account_topic(account_id, topic_resource),
            account_id=account_id,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            revision=revision,
            payload=payload,
        ),
    )
