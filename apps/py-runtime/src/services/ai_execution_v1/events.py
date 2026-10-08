from __future__ import annotations

from services.events import RuntimeEventDraft

from .unit_of_work import AIExecutionTransaction


def append_execution_event(
    transaction: AIExecutionTransaction,
    *,
    account_id: str,
    execution_id: str,
    task_id: str,
    event_type: str,
    revision: int,
    status: str,
    error_code: str | None = None,
    progress: float | None = None,
) -> None:
    payload: dict[str, object] = {
        "executionId": execution_id,
        "taskId": task_id,
        "status": status,
        "revision": revision,
        "invalidations": [
            f"account:{account_id}:ai-executions",
            f"account:{account_id}:tasks",
        ],
    }
    if error_code is not None:
        payload["errorCode"] = error_code
    if progress is not None:
        payload["progress"] = progress
    transaction.events.append_and_get(
        transaction.session,
        RuntimeEventDraft(
            topic=f"account:{account_id}:ai-executions",
            event_type=event_type,
            account_id=account_id,
            aggregate_type="ai_execution",
            aggregate_id=execution_id,
            task_id=task_id,
            revision=revision,
            payload=payload,
        ),
    )


__all__ = ["append_execution_event"]
