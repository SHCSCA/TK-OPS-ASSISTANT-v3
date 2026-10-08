from __future__ import annotations

from common.pagination import CursorPosition
from errors import DomainError, ErrorCode
from schemas.v1.ai_executions import (
    AIExecutionAcceptedDto,
    AIExecutionCreateInput,
    AIExecutionDetailDto,
    AIExecutionEvidenceDto,
    AIExecutionOutputDto,
    AIExecutionPageDto,
    AIExecutionPreflightDto,
    AIExecutionPreflightInput,
)
from services.tasks.coordinator import TaskCoordinator
from services.tasks.types import TaskCompletionKind, TaskStatus

from .creation import AIExecutionCreationService
from .execution_state import AIExecutionStateService
from .queries import AIExecutionQueryService
from .retry import AIExecutionRetryService
from .snapshot_builder import AIExecutionSnapshotBuilder


class AIExecutionGateway:
    """统一编排 AI 预检、创建、查询、取消与同快照重试。"""

    def __init__(
        self,
        *,
        snapshot_builder: AIExecutionSnapshotBuilder,
        creation: AIExecutionCreationService,
        retry: AIExecutionRetryService,
        queries: AIExecutionQueryService,
        state: AIExecutionStateService,
        task_coordinator: TaskCoordinator,
    ) -> None:
        self._snapshots = snapshot_builder
        self._creation = creation
        self._retry = retry
        self._queries = queries
        self._state = state
        self._tasks = task_coordinator

    def preflight(
        self,
        account_id: str,
        payload: AIExecutionPreflightInput,
        *,
        expected_revision: int,
    ) -> AIExecutionPreflightDto:
        plan = self._snapshots.preflight(
            account_id,
            expected_revision=expected_revision,
            capability_key=payload.capabilityKey,
            recipe_version_id=payload.recipeVersionId,
            knowledge_snapshot_id=payload.knowledgeSnapshotId,
            input_summary=payload.inputSummary.model_dump(mode="json"),
            requested_policy=payload.executionPolicy.model_dump(
                mode="json",
                exclude_none=True,
            ),
        )
        return AIExecutionPreflightDto(
            accountId=account_id,
            capabilityKey=payload.capabilityKey,
            ready=True,
            candidateCount=len(plan.candidates),
            blockingIssues=[],
            repairActions=[],
            costEstimate={
                "currency": plan.policy.currency,
                "minimumMicros": plan.cost_minimum_micros,
                "maximumMicros": plan.cost_maximum_micros,
                "budgetLimitMicros": plan.policy.max_cost_micros,
            },
            snapshotPreviewHash=plan.snapshot_hash,
        )

    def create(
        self,
        account_id: str,
        payload: AIExecutionCreateInput,
        *,
        expected_revision: int,
        idempotency_key: str,
        request_id: str,
        operation_id: str,
    ) -> tuple[AIExecutionAcceptedDto, dict[str, object]]:
        input_value = dict(payload.input)
        plan = self._snapshots.build(
            account_id,
            expected_revision=expected_revision,
            capability_key=payload.capabilityKey,
            recipe_version_id=payload.recipeVersionId,
            knowledge_snapshot_id=payload.knowledgeSnapshotId,
            input_value=input_value,
            requested_policy=payload.executionPolicy.model_dump(
                mode="json",
                exclude_none=True,
            ),
        )
        result = self._creation.create(
            account_id,
            plan=plan,
            capability_key=payload.capabilityKey,
            input_value=input_value,
            idempotency_key=idempotency_key,
            request_id=request_id,
            operation_id=operation_id,
        )
        return AIExecutionAcceptedDto.model_validate(result.data), result.meta

    def list_page(
        self,
        account_id: str,
        *,
        limit: int,
        cursor: CursorPosition | None,
        statuses: tuple[str, ...] | None,
        capability_key: str | None,
    ) -> tuple[AIExecutionPageDto, CursorPosition | None]:
        return self._queries.list_page(
            account_id,
            limit=limit,
            cursor=cursor,
            statuses=statuses,
            capability_key=capability_key,
        )

    def get_detail(
        self,
        account_id: str,
        execution_id: str,
    ) -> AIExecutionDetailDto:
        return self._queries.get_detail(account_id, execution_id)

    async def cancel(
        self,
        account_id: str,
        execution_id: str,
        *,
        idempotency_key: str,
    ) -> AIExecutionDetailDto:
        current = self._queries.get_detail(account_id, execution_id)
        if current.status in {"failed", "completed"}:
            return current
        task = await self._tasks.cancel_account_task(
            account_id,
            current.taskId,
            idempotency_key=idempotency_key,
        )
        if (
            task.status is TaskStatus.COMPLETED
            and task.completion_kind is TaskCompletionKind.CANCELLED
        ):
            self._state.complete_cancelled(
                account_id,
                execution_id,
                job_id=None,
            )
        elif task.status is TaskStatus.CANCELLING:
            self._state.request_cancellation(account_id, execution_id)
        elif task.status is TaskStatus.FAILED:
            self._state.fail_without_job(
                account_id,
                execution_id,
                error_code=task.error_code or ErrorCode.TASK_STATE_CONFLICT.value,
                failure_kind=(
                    task.failure_kind.value
                    if task.failure_kind is not None
                    else "error"
                ),
            )
        return self._queries.get_detail(account_id, execution_id)

    def retry_same_snapshot(
        self,
        account_id: str,
        execution_id: str,
        *,
        idempotency_key: str,
        request_id: str,
        operation_id: str,
    ) -> tuple[AIExecutionAcceptedDto, dict[str, object]]:
        result = self._retry.retry_same_snapshot(
            account_id,
            execution_id,
            idempotency_key=idempotency_key,
            request_id=request_id,
            operation_id=operation_id,
        )
        return AIExecutionAcceptedDto.model_validate(result.data), result.meta

    def get_output(
        self,
        account_id: str,
        execution_id: str,
        output_id: str,
    ) -> AIExecutionOutputDto:
        return self._queries.get_output(account_id, execution_id, output_id)

    def get_evidence(
        self,
        account_id: str,
        execution_id: str,
    ) -> AIExecutionEvidenceDto:
        return self._queries.get_evidence(account_id, execution_id)


__all__ = ["AIExecutionGateway"]
