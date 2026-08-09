from __future__ import annotations

from services.accounts.events import append_account_event
from services.accounts.unit_of_work import AccountTransaction
from services.knowledge.support import knowledge_invalidations


def append_knowledge_index_event(
    transaction: AccountTransaction,
    *,
    account_id: str,
    source_id: str,
    source_status: str,
    base_status: str,
    account_revision: int,
    task_id: str | None,
    config_revision: int,
    error_code: str | None,
    error_log_id: str | None,
) -> None:
    values: dict[str, object] = {
        "sourceId": source_id,
        "sourceStatus": source_status,
        "knowledgeStatus": base_status,
        "configRevision": config_revision,
        "reconciled": task_id is None,
    }
    if task_id is not None:
        values["taskId"] = task_id
    if error_code is not None:
        values["errorCode"] = error_code
    if error_log_id is not None:
        values["logId"] = error_log_id
    append_account_event(
        transaction,
        account_id=account_id,
        event_type="knowledge.index.updated",
        aggregate_type="knowledge_source",
        aggregate_id=source_id,
        revision=account_revision,
        invalidations=knowledge_invalidations(account_id),
        values=values,
        topic_resource="knowledge",
    )
