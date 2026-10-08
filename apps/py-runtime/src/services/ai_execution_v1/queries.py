from __future__ import annotations

from hashlib import sha256

from common.pagination import CursorPosition
from domain.models.ai_execution import AIExecution
from domain.models.ai_execution_evidence import AIProviderValidationRun
from domain.models.ai_execution_snapshot import (
    AIExecutionCandidate,
    AIExecutionSnapshot,
)
from errors import DomainError, ErrorCode
from schemas.v1.ai_executions import (
    AIExecutionDetailDto,
    AIExecutionEvidenceDto,
    AIExecutionOutputDto,
    AIExecutionPageDto,
)
from services.tasks.types import TaskScope

from .content_store import AIExecutionContentStore
from .presentation import (
    error_summary,
    execution_detail,
    execution_summary,
    job_summary,
    output_summary,
    usage_summary,
)
from .redaction import assert_safe_evidence
from .unit_of_work import AIExecutionTransaction, AIExecutionUnitOfWork


class AIExecutionQueryService:
    """提供账号隔离的执行、输出与证据投影。"""

    def __init__(
        self,
        unit_of_work: AIExecutionUnitOfWork,
        *,
        content_store: AIExecutionContentStore,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._content_store = content_store

    def list_page(
        self,
        account_id: str,
        *,
        limit: int,
        cursor: CursorPosition | None,
        statuses: tuple[str, ...] | None,
        capability_key: str | None,
    ) -> tuple[AIExecutionPageDto, CursorPosition | None]:
        with self._unit_of_work.read() as transaction:
            rows, next_position = (
                transaction.executions.executions.list_page(
                    transaction.session,
                    account_id,
                    limit=limit,
                    cursor=cursor,
                    statuses=statuses,
                    capability_key=capability_key,
                )
            )
            items = [
                execution_summary(
                    row,
                    self._require_snapshot(transaction, row),
                )
                for row in rows
            ]
            return (
                AIExecutionPageDto(items=items, totalKnown=None),
                next_position,
            )

    def get_detail(
        self,
        account_id: str,
        execution_id: str,
    ) -> AIExecutionDetailDto:
        with self._unit_of_work.read() as transaction:
            execution = self._require_execution(
                transaction,
                account_id,
                execution_id,
            )
            return AIExecutionDetailDto.model_validate(
                self._detail(transaction, execution)
            )

    def get_output(
        self,
        account_id: str,
        execution_id: str,
        output_id: str,
    ) -> AIExecutionOutputDto:
        with self._unit_of_work.read() as transaction:
            self._require_execution(transaction, account_id, execution_id)
            row = transaction.executions.evidence.get_output(
                transaction.session,
                account_id,
                execution_id,
                output_id,
            )
            if row is None:
                raise _not_found()
            if row.quarantined:
                raise DomainError(
                    ErrorCode.AI_COST_LIMIT_EXCEEDED,
                    "该输出因成本越界已隔离，不能读取正文",
                    status_code=409,
                )
            content, digest = self._content_store.read_output(
                account_id,
                row.content_ref,
            )
            if digest != row.content_hash:
                raise DomainError(
                    ErrorCode.AI_EXECUTION_INVALID,
                    "AI 执行输出完整性校验失败",
                    status_code=409,
                    loggable=True,
                )
            payload = output_summary(row)
            payload.update({"executionId": execution_id, "content": content})
            return AIExecutionOutputDto.model_validate(payload)

    def get_evidence(
        self,
        account_id: str,
        execution_id: str,
    ) -> AIExecutionEvidenceDto:
        with self._unit_of_work.read() as transaction:
            execution = self._require_execution(
                transaction,
                account_id,
                execution_id,
            )
            snapshot = self._require_snapshot(transaction, execution)
            errors = transaction.executions.evidence.list_errors(
                transaction.session,
                account_id,
                execution_id,
            )
            errors_by_job = {
                item.job_id: item for item in errors if item.job_id is not None
            }
            jobs = transaction.executions.evidence.list_jobs(
                transaction.session,
                account_id,
                execution_id,
            )
            usage = transaction.executions.evidence.list_usage(
                transaction.session,
                account_id,
                execution_id,
            )
            candidates = transaction.executions.snapshots.list_candidates(
                transaction.session,
                account_id,
                snapshot.id,
            )
            successful_job = next(
                (
                    item
                    for item in reversed(jobs)
                    if item.status == "completed"
                    and item.completion_kind == "succeeded"
                ),
                None,
            )
            successful_candidate = next(
                (
                    item
                    for item in candidates
                    if successful_job is not None
                    and item.id == successful_job.candidate_snapshot_id
                ),
                None,
            )
            validation_run = (
                None
                if successful_candidate is None
                else transaction.ai.validation_runs.get(
                    transaction.session,
                    successful_candidate.validation_run_id,
                )
            )
            payload = {
                "executionId": execution_id,
                "accountId": account_id,
                "capabilityKey": execution.capability_key,
                "finalStatus": _final_status(execution),
                "snapshotHash": snapshot.snapshot_hash,
                "provider": _provider_evidence(
                    successful_candidate,
                    validation_run,
                ),
                "responseIdHash": (
                    None
                    if successful_job is None
                    else successful_job.provider_request_id_hash
                ),
                "durationMs": (
                    None if successful_job is None else successful_job.duration_ms
                ),
                "usageReported": bool(usage)
                and all(item.raw_usage_hash is not None for item in usage),
                "jobs": [
                    job_summary(item, error=errors_by_job.get(item.id))
                    for item in jobs
                ],
                "usage": [usage_summary(item) for item in usage],
                "outputs": [
                    output_summary(item)
                    for item in transaction.executions.evidence.list_outputs(
                        transaction.session,
                        account_id,
                        execution_id,
                    )
                ],
                "errors": [error_summary(item) for item in errors],
            }
            assert_safe_evidence(payload)
            return AIExecutionEvidenceDto.model_validate(payload)

    def _detail(
        self,
        transaction: AIExecutionTransaction,
        execution: AIExecution,
    ) -> dict[str, object]:
        account_id = execution.account_id
        execution_id = execution.id
        task = transaction.tasks.get_scoped(
            transaction.session,
            execution.runtime_task_id,
            scope=TaskScope.ACCOUNT,
            account_id=account_id,
        )
        if task is None:
            raise _damaged()
        return execution_detail(
            execution,
            self._require_snapshot(transaction, execution),
            task,
            candidates=transaction.executions.snapshots.list_candidates(
                transaction.session,
                account_id,
                execution.snapshot_id,
            ),
            jobs=transaction.executions.evidence.list_jobs(
                transaction.session,
                account_id,
                execution_id,
            ),
            usage=transaction.executions.evidence.list_usage(
                transaction.session,
                account_id,
                execution_id,
            ),
            outputs=transaction.executions.evidence.list_outputs(
                transaction.session,
                account_id,
                execution_id,
            ),
            errors=transaction.executions.evidence.list_errors(
                transaction.session,
                account_id,
                execution_id,
            ),
        )

    @staticmethod
    def _require_execution(
        transaction: AIExecutionTransaction,
        account_id: str,
        execution_id: str,
    ) -> AIExecution:
        row = transaction.executions.executions.get_scoped(
            transaction.session,
            account_id,
            execution_id,
        )
        if row is None:
            raise _not_found()
        return row

    @staticmethod
    def _require_snapshot(
        transaction: AIExecutionTransaction,
        execution: AIExecution,
    ) -> AIExecutionSnapshot:
        row = transaction.executions.snapshots.get_snapshot(
            transaction.session,
            execution.account_id,
            execution.snapshot_id,
        )
        if row is None:
            raise _damaged()
        return row


def _not_found() -> DomainError:
    return DomainError(
        ErrorCode.AI_EXECUTION_NOT_FOUND,
        "AI 执行不存在",
        status_code=404,
    )


def _damaged() -> DomainError:
    return DomainError(
        ErrorCode.INTERNAL_ERROR,
        "AI 执行记录不完整，请查看诊断日志",
        status_code=500,
        loggable=True,
    )


def _final_status(execution: AIExecution) -> str:
    if execution.status == "completed":
        return execution.completion_kind or "failed"
    return execution.status


def _provider_evidence(
    candidate: AIExecutionCandidate | None,
    validation_run: AIProviderValidationRun | None,
) -> dict[str, str] | None:
    if candidate is None or validation_run is None:
        return None
    if (
        candidate.adapter_type != "openai_compatible"
        or validation_run.stage != "real_small_call"
        or validation_run.status != "verified"
    ):
        return None
    return {
        "adapterType": "openai_compatible",
        "providerRefHash": _stable_hash(candidate.provider_profile_id),
        "modelIdHash": _stable_hash(candidate.model_id),
        "validationRunHash": _stable_hash(validation_run.id),
        "validationStage": "real_small_call",
        "validationStatus": "verified",
    }


def _stable_hash(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


__all__ = ["AIExecutionQueryService"]
