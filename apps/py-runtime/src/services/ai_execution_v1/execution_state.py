from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from domain.models.ai_execution import AIExecutionJob
from domain.models.ai_execution_evidence import (
    AIErrorEvidence,
    AIExecutionOutput,
    AIUsageRecord,
)
from domain.models.ai_execution_snapshot import AIExecutionCandidate
from errors import DomainError, ErrorCode
from services.ai_configuration_v1.json_codec import dump_json
from services.tasks.types import TaskCommitCoordinator

from .content_store import StoredExecutionContent
from .events import append_execution_event
from .execution_recovery_state import AIExecutionRecoveryStateMixin
from .output_validation import ValidatedAIOutput
from .policies import CostEstimate
from .redaction import assert_safe_evidence
from .types import AIProviderResult
from .unit_of_work import AIExecutionUnitOfWork


@dataclass(frozen=True, slots=True)
class StartedExecutionJob:
    id: str
    attempt: int
    candidate: AIExecutionCandidate


class AIExecutionStateService(AIExecutionRecoveryStateMixin):
    """集中维护 AIExecution/AIJob 状态机与脱敏证据。"""

    def __init__(self, unit_of_work: AIExecutionUnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    def start_execution(self, account_id: str, execution_id: str) -> None:
        with self._unit_of_work.write() as transaction:
            row = transaction.executions.executions.get_scoped(
                transaction.session,
                account_id,
                execution_id,
            )
            if row is None:
                raise _not_found()
            if row.status == "running":
                return
            now = _utc_now()
            updated = transaction.executions.executions.transition(
                transaction.session,
                account_id,
                execution_id,
                expected_statuses=("queued",),
                values={
                    "status": "running",
                    "started_at": now,
                    "updated_at": now,
                },
            )
            if updated is None:
                raise _state_conflict()
            append_execution_event(
                transaction,
                account_id=account_id,
                execution_id=execution_id,
                task_id=updated.runtime_task_id,
                event_type="ai.execution.started",
                revision=int(updated.revision),
                status=updated.status,
                progress=0.05,
            )

    def start_job(
        self,
        account_id: str,
        execution_id: str,
        candidate: AIExecutionCandidate,
        *,
        fallback_index: int,
        retry_index: int,
        planned_request_hash: str,
    ) -> StartedExecutionJob:
        with self._unit_of_work.write() as transaction:
            execution = transaction.executions.executions.get_scoped(
                transaction.session,
                account_id,
                execution_id,
            )
            if execution is None:
                raise _not_found()
            if execution.status != "running":
                raise _state_conflict()
            attempt = len(
                transaction.executions.evidence.list_jobs(
                    transaction.session,
                    account_id,
                    execution_id,
                )
            ) + 1
            now = datetime.now(UTC)
            row = transaction.executions.evidence.add_job(
                transaction.session,
                AIExecutionJob(
                    id=f"aijob_{uuid4().hex}",
                    account_id=account_id,
                    execution_id=execution_id,
                    candidate_snapshot_id=candidate.id,
                    attempt=attempt,
                    fallback_index=fallback_index,
                    retry_index=retry_index,
                    status="running",
                    completion_kind=None,
                    failure_kind=None,
                    provider_request_id_hash=None,
                    request_hash=planned_request_hash,
                    response_hash=None,
                    duration_ms=None,
                    timeout_at=_to_text(
                        now + timedelta(milliseconds=int(candidate.timeout_ms))
                    ),
                    error_evidence_id=None,
                    revision=1,
                    created_at=_to_text(now),
                    started_at=_to_text(now),
                    completed_at=None,
                ),
            )
            updated = transaction.executions.executions.transition(
                transaction.session,
                account_id,
                execution_id,
                expected_statuses=("running",),
                values={
                    "active_job_id": row.id,
                    "updated_at": _to_text(now),
                },
            )
            if updated is None:
                raise _state_conflict()
            append_execution_event(
                transaction,
                account_id=account_id,
                execution_id=execution_id,
                task_id=updated.runtime_task_id,
                event_type="ai.execution.job_started",
                revision=int(updated.revision),
                status=updated.status,
            )
            return StartedExecutionJob(
                id=row.id,
                attempt=attempt,
                candidate=candidate,
            )

    def record_job_failure(
        self,
        account_id: str,
        execution_id: str,
        job_id: str,
        *,
        error_code: str,
        safe_summary: str,
        failure_kind: str,
        retryable: bool,
        provider_status_code: int | None,
        provider_request_id_hash: str | None,
        response_hash: str | None,
        duration_ms: int | None,
        terminal: bool,
        terminal_error_code: str | None = None,
    ) -> str:
        log_id = f"log_{uuid4().hex}"
        with self._unit_of_work.write() as transaction:
            execution = transaction.executions.executions.get_scoped(
                transaction.session,
                account_id,
                execution_id,
            )
            job = transaction.executions.evidence.get_job(
                transaction.session,
                account_id,
                job_id,
            )
            if execution is None or job is None:
                raise _not_found()
            now = _utc_now()
            assert_safe_evidence(
                {
                    "stage": "provider_call",
                    "errorCode": error_code,
                    "safeSummary": safe_summary,
                    "logId": log_id,
                }
            )
            evidence = transaction.executions.evidence.add_error(
                transaction.session,
                AIErrorEvidence(
                    id=f"aierr_{uuid4().hex}",
                    account_id=account_id,
                    execution_id=execution_id,
                    job_id=job_id,
                    stage="provider_call",
                    error_code=error_code,
                    provider_status_code=provider_status_code,
                    retryable=retryable,
                    safe_summary=safe_summary,
                    provider_request_id_hash=provider_request_id_hash,
                    response_body_hash=response_hash,
                    log_id=log_id,
                    created_at=now,
                ),
            )
            updated_job = transaction.executions.evidence.transition_job(
                transaction.session,
                account_id,
                job_id,
                expected_statuses=("running", "cancelling"),
                values={
                    "status": "failed",
                    "completion_kind": None,
                    "failure_kind": failure_kind,
                    "provider_request_id_hash": provider_request_id_hash,
                    "response_hash": response_hash,
                    "duration_ms": duration_ms,
                    "error_evidence_id": evidence.id,
                    "completed_at": now,
                },
            )
            if updated_job is None:
                raise _state_conflict()
            values: dict[str, object] = {
                "active_job_id": None,
                "error_code": terminal_error_code or error_code,
                "error_log_id": log_id,
                "updated_at": now,
            }
            if terminal:
                values.update(
                    {
                        "status": "failed",
                        "failure_kind": failure_kind,
                        "completion_kind": None,
                        "completed_at": now,
                    }
                )
                if failure_kind == "result_unknown":
                    values["cost_status"] = "unavailable"
            updated = transaction.executions.executions.transition(
                transaction.session,
                account_id,
                execution_id,
                expected_statuses=("running", "cancelling"),
                values=values,
            )
            if updated is None:
                raise _state_conflict()
            append_execution_event(
                transaction,
                account_id=account_id,
                execution_id=execution_id,
                task_id=updated.runtime_task_id,
                event_type=(
                    "ai.execution.failed"
                    if terminal
                    else "ai.execution.job_failed"
                ),
                revision=int(updated.revision),
                status=updated.status,
                error_code=updated.error_code,
            )
        return log_id

    def record_fallback_started(
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
            if execution.status != "running":
                raise _state_conflict()
            append_execution_event(
                transaction,
                account_id=account_id,
                execution_id=execution_id,
                task_id=execution.runtime_task_id,
                event_type="ai.execution.fallback_started",
                revision=int(execution.revision),
                status=execution.status,
            )

    def complete_success(
        self,
        account_id: str,
        execution_id: str,
        job_id: str,
        *,
        candidate: AIExecutionCandidate,
        provider_result: AIProviderResult,
        validated_output: ValidatedAIOutput,
        stored_output: StoredExecutionContent,
        cost: CostEstimate,
        commit_coordinator: TaskCommitCoordinator,
    ) -> bool:
        with self._unit_of_work.write(
            commit_coordinator=commit_coordinator,
        ) as transaction:
            execution = transaction.executions.executions.get_scoped(
                transaction.session,
                account_id,
                execution_id,
            )
            if execution is None:
                raise _not_found()
            now = _utc_now()
            usage = provider_result.usage
            budget_limit = int(execution.budget_limit_micros)
            over_budget = (
                cost.maximum_micros is not None
                and budget_limit > 0
                and cost.maximum_micros > budget_limit
            )
            cost_source = (
                "estimated"
                if cost.maximum_micros is not None
                else "unavailable"
            )
            transaction.executions.evidence.add_usage(
                transaction.session,
                AIUsageRecord(
                    id=f"aiusage_{uuid4().hex}",
                    account_id=account_id,
                    execution_id=execution_id,
                    job_id=job_id,
                    provider_profile_id=candidate.provider_profile_id,
                    model_profile_id=candidate.model_profile_id,
                    input_units=usage.input_units,
                    output_units=usage.output_units,
                    cached_units=usage.cached_units,
                    total_units=usage.total_units,
                    cost_micros=cost.maximum_micros,
                    currency=execution.currency,
                    cost_source=cost_source,
                    pricing_revision=cost.pricing_revision,
                    raw_usage_hash=_sha256_json(usage.to_dict()),
                    created_at=now,
                ),
            )
            transaction.executions.evidence.add_output(
                transaction.session,
                AIExecutionOutput(
                    id=stored_output.reference.rsplit("/", 1)[-1],
                    account_id=account_id,
                    execution_id=execution_id,
                    job_id=job_id,
                    kind=validated_output.kind,
                    mime_type=validated_output.mime_type,
                    content_ref=stored_output.reference,
                    content_hash=stored_output.content_hash,
                    byte_size=stored_output.byte_size,
                    schema_status=validated_output.schema_status,
                    safe_summary_json=dump_json(validated_output.safe_summary),
                    quarantined=over_budget,
                    created_at=now,
                ),
            )
            budget_log_id: str | None = None
            if over_budget:
                budget_log_id = f"log_{uuid4().hex}"
                assert_safe_evidence(
                    {
                        "stage": "cost_guard",
                        "errorCode": ErrorCode.AI_COST_LIMIT_EXCEEDED.value,
                        "safeSummary": "Provider 实际用量超过本次预算上限",
                        "logId": budget_log_id,
                    }
                )
                transaction.executions.evidence.add_error(
                    transaction.session,
                    AIErrorEvidence(
                        id=f"aierr_{uuid4().hex}",
                        account_id=account_id,
                        execution_id=execution_id,
                        job_id=job_id,
                        stage="cost_guard",
                        error_code=ErrorCode.AI_COST_LIMIT_EXCEEDED.value,
                        provider_status_code=None,
                        retryable=False,
                        safe_summary="Provider 实际用量超过本次预算上限",
                        provider_request_id_hash=(
                            provider_result.response_id_hash
                        ),
                        response_body_hash=provider_result.response_hash,
                        log_id=budget_log_id,
                        created_at=now,
                    ),
                )
            job = transaction.executions.evidence.transition_job(
                transaction.session,
                account_id,
                job_id,
                expected_statuses=("running",),
                values={
                    "status": "completed",
                    "completion_kind": "succeeded",
                    "failure_kind": None,
                    "provider_request_id_hash": (
                        provider_result.response_id_hash
                    ),
                    "request_hash": provider_result.request_hash,
                    "response_hash": provider_result.response_hash,
                    "duration_ms": provider_result.duration_ms,
                    "completed_at": now,
                },
            )
            if job is None:
                raise _state_conflict()
            terminal_values: dict[str, object] = {
                "active_job_id": None,
                "usage_input_units": usage.input_units,
                "usage_output_units": usage.output_units,
                "usage_cached_units": usage.cached_units,
                "cost_micros": cost.maximum_micros,
                "cost_status": cost_source,
                "output_count": 1,
                "completed_at": now,
                "updated_at": now,
            }
            if over_budget:
                terminal_values.update(
                    {
                        "status": "failed",
                        "completion_kind": None,
                        "failure_kind": "error",
                        "error_code": ErrorCode.AI_COST_LIMIT_EXCEEDED.value,
                        "error_log_id": budget_log_id,
                    }
                )
            else:
                terminal_values.update(
                    {
                        "status": "completed",
                        "completion_kind": "succeeded",
                        "failure_kind": None,
                        "error_code": None,
                        "error_log_id": None,
                    }
                )
            updated = transaction.executions.executions.transition(
                transaction.session,
                account_id,
                execution_id,
                expected_statuses=("running",),
                values=terminal_values,
            )
            if updated is None:
                raise _state_conflict()
            append_execution_event(
                transaction,
                account_id=account_id,
                execution_id=execution_id,
                task_id=updated.runtime_task_id,
                event_type=(
                    "ai.execution.failed"
                    if over_budget
                    else "ai.execution.completed"
                ),
                revision=int(updated.revision),
                status=updated.status,
                error_code=updated.error_code,
                progress=1.0,
            )
        return over_budget

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
    return _to_text(datetime.now(UTC))


def _to_text(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _sha256_json(value: object) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


__all__ = ["AIExecutionStateService", "StartedExecutionJob"]
