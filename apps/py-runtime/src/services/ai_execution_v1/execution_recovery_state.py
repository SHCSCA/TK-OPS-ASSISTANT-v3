from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from domain.models.ai_execution_evidence import AIErrorEvidence
from errors import DomainError, ErrorCode
from services.tasks.types import TaskStatus

from .events import append_execution_event
from .redaction import assert_safe_evidence
from .unit_of_work import AIExecutionTransaction, AIExecutionUnitOfWork


class AIExecutionRecoveryStateMixin:
    """集中处理取消、重启恢复与无 Job 失败终态。"""

    _unit_of_work: AIExecutionUnitOfWork

    def complete_cancelled(
        self,
        account_id: str,
        execution_id: str,
        *,
        job_id: str | None,
    ) -> None:
        with self._unit_of_work.write() as transaction:
            execution = transaction.executions.executions.get_scoped(
                transaction.session,
                account_id,
                execution_id,
            )
            if execution is None or execution.status in {"failed", "completed"}:
                return
            now = _utc_now()
            if job_id is not None:
                transaction.executions.evidence.transition_job(
                    transaction.session,
                    account_id,
                    job_id,
                    expected_statuses=("running", "cancelling", "queued"),
                    values={
                        "status": "completed",
                        "completion_kind": "cancelled",
                        "failure_kind": None,
                        "completed_at": now,
                    },
                )
            updated = transaction.executions.executions.transition(
                transaction.session,
                account_id,
                execution_id,
                expected_statuses=("queued", "running", "cancelling"),
                values={
                    "status": "completed",
                    "completion_kind": "cancelled",
                    "failure_kind": None,
                    "active_job_id": None,
                    "cost_status": (
                        "unavailable"
                        if job_id is not None or execution.active_job_id is not None
                        else execution.cost_status
                    ),
                    "completed_at": now,
                    "updated_at": now,
                },
            )
            if updated is not None:
                append_execution_event(
                    transaction,
                    account_id=account_id,
                    execution_id=execution_id,
                    task_id=updated.runtime_task_id,
                    event_type="ai.execution.completed",
                    revision=int(updated.revision),
                    status=updated.status,
                    progress=1.0,
                )

    def request_cancellation(
        self,
        account_id: str,
        execution_id: str,
    ) -> None:
        with self._unit_of_work.write() as transaction:
            execution = transaction.executions.executions.get_scoped(
                transaction.session,
                account_id,
                execution_id,
            )
            if execution is None:
                raise _not_found()
            if execution.status in {"failed", "completed", "cancelling"}:
                return
            updated = transaction.executions.executions.transition(
                transaction.session,
                account_id,
                execution_id,
                expected_statuses=("queued", "running"),
                values={"status": "cancelling", "updated_at": _utc_now()},
            )
            if updated is None:
                raise _state_conflict()
            append_execution_event(
                transaction,
                account_id=account_id,
                execution_id=execution_id,
                task_id=updated.runtime_task_id,
                event_type="ai.execution.cancelling",
                revision=int(updated.revision),
                status=updated.status,
            )

    def recover_interrupted(
        self,
        account_id: str,
        execution_id: str,
        *,
        job_id: str | None,
        result_unknown: bool,
    ) -> None:
        error_code = (
            ErrorCode.AI_PROVIDER_RESULT_UNKNOWN.value
            if result_unknown
            else ErrorCode.TASK_STATE_CONFLICT.value
        )
        failure_kind = (
            "result_unknown" if result_unknown else "restart_interrupted"
        )
        summary = (
            "Runtime 重启时 Provider 终态与费用无法确认"
            if result_unknown
            else "Runtime 重启前尚未开始可证明的 Provider 调用"
        )
        with self._unit_of_work.write() as transaction:
            execution = transaction.executions.executions.get_scoped(
                transaction.session,
                account_id,
                execution_id,
            )
            if execution is None or execution.status in {"failed", "completed"}:
                return
            now = _utc_now()
            effective_job_id: str | None = None
            if job_id is not None:
                job = transaction.executions.evidence.get_job(
                    transaction.session,
                    account_id,
                    job_id,
                )
                if job is not None:
                    effective_job_id = job.id
                    transaction.executions.evidence.transition_job(
                        transaction.session,
                        account_id,
                        job.id,
                        expected_statuses=("queued", "running", "cancelling"),
                        values={
                            "status": "failed",
                            "completion_kind": None,
                            "failure_kind": failure_kind,
                            "completed_at": now,
                        },
                    )
            log_id = _add_error_evidence(
                transaction,
                account_id=account_id,
                execution_id=execution_id,
                job_id=effective_job_id,
                stage="restart_recovery",
                error_code=error_code,
                safe_summary=summary,
            )
            transaction.tasks.transition(
                transaction.session,
                execution.runtime_task_id,
                expected_statuses=(
                    TaskStatus.QUEUED,
                    TaskStatus.RUNNING,
                    TaskStatus.CANCELLING,
                ),
                values={
                    "status": TaskStatus.FAILED.value,
                    "completion_kind": None,
                    "failure_kind": "restart_interrupted",
                    "error_code": error_code,
                    "error_log_id": log_id,
                    "completed_at": now,
                    "updated_at": now,
                },
            )
            values: dict[str, object] = {
                "status": "failed",
                "completion_kind": None,
                "failure_kind": failure_kind,
                "active_job_id": None,
                "error_code": error_code,
                "error_log_id": log_id,
                "completed_at": now,
                "updated_at": now,
            }
            if result_unknown:
                values["cost_status"] = "unavailable"
            updated = transaction.executions.executions.transition(
                transaction.session,
                account_id,
                execution_id,
                expected_statuses=("queued", "running", "cancelling"),
                values=values,
            )
            if updated is None:
                raise _state_conflict()
            append_execution_event(
                transaction,
                account_id=account_id,
                execution_id=execution_id,
                task_id=updated.runtime_task_id,
                event_type="ai.execution.failed",
                revision=int(updated.revision),
                status=updated.status,
                error_code=error_code,
            )

    def fail_without_job(
        self,
        account_id: str,
        execution_id: str,
        *,
        error_code: str,
        safe_summary: str = "AI 执行未能开始 Provider 调用",
        failure_kind: str = "error",
    ) -> None:
        with self._unit_of_work.write() as transaction:
            row = transaction.executions.executions.get_scoped(
                transaction.session,
                account_id,
                execution_id,
            )
            if row is None or row.status in {"failed", "completed"}:
                return
            now = _utc_now()
            log_id = _add_error_evidence(
                transaction,
                account_id=account_id,
                execution_id=execution_id,
                job_id=None,
                stage="execution_preflight",
                error_code=error_code,
                safe_summary=safe_summary,
            )
            values: dict[str, object] = {
                "status": "failed",
                "completion_kind": None,
                "failure_kind": failure_kind,
                "active_job_id": None,
                "error_code": error_code,
                "error_log_id": log_id,
                "completed_at": now,
                "updated_at": now,
            }
            if failure_kind == "result_unknown":
                values["cost_status"] = "unavailable"
            updated = transaction.executions.executions.transition(
                transaction.session,
                account_id,
                execution_id,
                expected_statuses=("queued", "running", "cancelling"),
                values=values,
            )
            if updated is not None:
                append_execution_event(
                    transaction,
                    account_id=account_id,
                    execution_id=execution_id,
                    task_id=updated.runtime_task_id,
                    event_type="ai.execution.failed",
                    revision=int(updated.revision),
                    status=updated.status,
                    error_code=error_code,
                )


def _add_error_evidence(
    transaction: AIExecutionTransaction,
    *,
    account_id: str,
    execution_id: str,
    job_id: str | None,
    stage: str,
    error_code: str,
    safe_summary: str,
) -> str:
    log_id = f"log_{uuid4().hex}"
    assert_safe_evidence(
        {
            "stage": stage,
            "errorCode": error_code,
            "safeSummary": safe_summary,
            "logId": log_id,
        }
    )
    transaction.executions.evidence.add_error(
        transaction.session,
        AIErrorEvidence(
            id=f"aierr_{uuid4().hex}",
            account_id=account_id,
            execution_id=execution_id,
            job_id=job_id,
            stage=stage,
            error_code=error_code,
            provider_status_code=None,
            retryable=False,
            safe_summary=safe_summary,
            provider_request_id_hash=None,
            response_body_hash=None,
            log_id=log_id,
            created_at=_utc_now(),
        ),
    )
    return log_id


def _not_found() -> DomainError:
    return DomainError(
        ErrorCode.AI_EXECUTION_NOT_FOUND,
        "AI 执行不存在",
        status_code=404,
    )


def _state_conflict() -> DomainError:
    return DomainError(
        ErrorCode.AI_EXECUTION_STATE_CONFLICT,
        "AI 执行状态已变化，请刷新后重试",
        status_code=409,
    )


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = ["AIExecutionRecoveryStateMixin"]
