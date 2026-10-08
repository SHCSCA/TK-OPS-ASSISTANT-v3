from __future__ import annotations

import logging
from dataclasses import dataclass

from services.tasks.types import TaskCompletionKind, TaskStatus

from .execution_state import AIExecutionStateService
from .unit_of_work import AIExecutionUnitOfWork

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AIExecutionRecoveryReport:
    checked_count: int
    cancelled_count: int
    interrupted_count: int
    result_unknown_count: int


@dataclass(frozen=True, slots=True)
class _RecoveryAction:
    account_id: str
    execution_id: str
    kind: str
    job_id: str | None


class AIExecutionStartupReconciler:
    """把重启遗留执行失败封闭，禁止自动重复外部调用。"""

    def __init__(
        self,
        unit_of_work: AIExecutionUnitOfWork,
        *,
        state: AIExecutionStateService,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._state = state

    def reconcile(self) -> AIExecutionRecoveryReport:
        actions = self._plan()
        cancelled = 0
        interrupted = 0
        result_unknown = 0
        for action in actions:
            if action.kind == "cancelled":
                self._state.complete_cancelled(
                    action.account_id,
                    action.execution_id,
                    job_id=action.job_id,
                )
                cancelled += 1
                continue
            unknown = action.kind == "result_unknown"
            self._state.recover_interrupted(
                action.account_id,
                action.execution_id,
                job_id=action.job_id,
                result_unknown=unknown,
            )
            if unknown:
                result_unknown += 1
            else:
                interrupted += 1
        report = AIExecutionRecoveryReport(
            checked_count=len(actions),
            cancelled_count=cancelled,
            interrupted_count=interrupted,
            result_unknown_count=result_unknown,
        )
        log.info(
            "AI 执行重启对账完成",
            extra={
                "checked_count": report.checked_count,
                "cancelled_count": report.cancelled_count,
                "interrupted_count": report.interrupted_count,
                "result_unknown_count": report.result_unknown_count,
            },
        )
        return report

    def _plan(self) -> tuple[_RecoveryAction, ...]:
        with self._unit_of_work.read() as transaction:
            actions: list[_RecoveryAction] = []
            for execution in transaction.executions.executions.list_non_terminal(
                transaction.session
            ):
                task = transaction.tasks.get_any(
                    transaction.session,
                    execution.runtime_task_id,
                )
                jobs = transaction.executions.evidence.list_jobs(
                    transaction.session,
                    execution.account_id,
                    execution.id,
                )
                active = next(
                    (
                        item
                        for item in reversed(jobs)
                        if item.status in {"running", "cancelling"}
                    ),
                    None,
                )
                if (
                    task is not None
                    and task.status == TaskStatus.COMPLETED.value
                    and task.completion_kind
                    == TaskCompletionKind.CANCELLED.value
                ):
                    kind = "cancelled"
                elif active is not None:
                    kind = "result_unknown"
                else:
                    kind = "restart_interrupted"
                actions.append(
                    _RecoveryAction(
                        account_id=execution.account_id,
                        execution_id=execution.id,
                        kind=kind,
                        job_id=active.id if active is not None else None,
                    )
                )
            return tuple(actions)


__all__ = [
    "AIExecutionRecoveryReport",
    "AIExecutionStartupReconciler",
]
