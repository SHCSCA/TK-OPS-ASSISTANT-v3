from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from uuid import uuid4

from domain.models.ai_execution import AIExecution
from domain.models.ai_execution_snapshot import (
    AIDependencySnapshot,
    AIExecutionCandidate,
    AIExecutionSnapshot,
)
from errors import DomainError, ErrorCode
from services.accounts.guards import require_account, require_revision
from services.ai_configuration_v1.json_codec import content_hash, dump_json
from services.ai_configuration_v1.mutation_helpers import utc_now
from services.tasks.coordinator import TaskCoordinator
from services.tasks.errors import task_idempotency_conflict
from services.tasks.types import CreateTaskCommand, RuntimeTaskRecord, TaskScope

from .content_store import AIExecutionContentStore
from .events import append_execution_event
from .snapshot_builder import ExecutionPlan
from .unit_of_work import AIExecutionTransaction, AIExecutionUnitOfWork

AI_EXECUTION_TASK_TYPE = "ai.execution"


@dataclass(frozen=True, slots=True)
class AIExecutionCreationResult:
    data: dict[str, object]
    meta: dict[str, object]


class AIExecutionCreationService:
    """把输入、执行快照、候选、RuntimeTask 与 outbox 原子落库。"""

    def __init__(
        self,
        unit_of_work: AIExecutionUnitOfWork,
        *,
        content_store: AIExecutionContentStore,
        task_coordinator: TaskCoordinator,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._content_store = content_store
        self._tasks = task_coordinator

    def create(
        self,
        account_id: str,
        *,
        plan: ExecutionPlan,
        capability_key: str,
        input_value: dict[str, object],
        idempotency_key: str,
        request_id: str,
        operation_id: str,
        retry_of_execution_id: str | None = None,
    ) -> AIExecutionCreationResult:
        key_hash = _sha256_text(idempotency_key.strip())
        request_hash = _request_hash(
            capability_key=capability_key,
            plan=plan,
            input_value=input_value,
            retry_of_execution_id=retry_of_execution_id,
        )
        replay = self._idempotent_replay(
            account_id,
            key_hash=key_hash,
            request_hash=request_hash,
        )
        if replay is not None:
            return replay
        execution_id = f"aiexec_{uuid4().hex}"
        stored_input = self._content_store.store_input(
            account_id,
            execution_id,
            input_value,
        )
        if plan.input_hash is None or stored_input.content_hash != plan.input_hash:
            self._content_store.remove_input(account_id, stored_input.reference)
            raise DomainError(
                ErrorCode.AI_EXECUTION_INVALID,
                "AI 执行输入摘要与受控内容不一致",
                status_code=409,
                loggable=True,
            )
        task_record: RuntimeTaskRecord | None = None
        created_execution = False
        try:
            with self._unit_of_work.write() as transaction:
                transaction.accounts.acquire_write_lock(
                    transaction.session,
                    account_id=account_id,
                )
                account = require_account(
                    account_id,
                    transaction.session,
                    transaction.accounts,
                )
                require_revision(account, int(plan.account.revision))
                existing = transaction.executions.executions.get_by_idempotency(
                    transaction.session,
                    account_id,
                    key_hash,
                )
                if existing is not None:
                    if existing.request_hash != request_hash:
                        raise task_idempotency_conflict()
                    return self._creation_result(
                        transaction,
                        existing,
                        idempotent_replay=True,
                    )
                now = utc_now()
                dependency = transaction.ai.dependency_snapshots.add(
                    transaction.session,
                    AIDependencySnapshot(
                        id=f"deps_{uuid4().hex}",
                        owner_type="execution_preflight",
                        owner_id=execution_id,
                        owner_revision=1,
                        status="valid",
                        graph_json=dump_json(plan.dependency_graph),
                        issues_json="[]",
                        repair_actions_json="[]",
                        content_hash=plan.dependency_hash,
                        created_at=now,
                    ),
                )
                snapshot = transaction.executions.snapshots.add_snapshot(
                    transaction.session,
                    _snapshot_row(
                        account_id=account_id,
                        plan=plan,
                        dependency_snapshot_id=dependency.id,
                        created_at=now,
                    ),
                )
                transaction.executions.snapshots.add_candidates(
                    transaction.session,
                    _candidate_rows(
                        account_id=account_id,
                        snapshot_id=snapshot.id,
                        plan=plan,
                    ),
                )
                task_record = self._tasks.create_task_in_session(
                    transaction.session,
                    CreateTaskCommand(
                        scope=TaskScope.ACCOUNT,
                        account_id=account_id,
                        task_type=AI_EXECUTION_TASK_TYPE,
                        payload={
                            "executionId": execution_id,
                            "snapshotHash": plan.snapshot_hash,
                        },
                        idempotency_key=f"ai-execution-task:{execution_id}",
                        request_id=request_id,
                        operation_id=operation_id,
                        timeout_seconds=max(
                            1,
                            math.ceil(plan.policy.timeout_ms / 1_000),
                        ),
                    ),
                )
                row = transaction.executions.executions.add(
                    transaction.session,
                    AIExecution(
                        id=execution_id,
                        account_id=account_id,
                        capability_key=capability_key,
                        status="queued",
                        completion_kind=None,
                        failure_kind=None,
                        snapshot_id=snapshot.id,
                        runtime_task_id=task_record.id,
                        active_job_id=None,
                        retry_of_execution_id=retry_of_execution_id,
                        input_ref=stored_input.reference,
                        input_hash=stored_input.content_hash,
                        idempotency_key_hash=key_hash,
                        request_hash=request_hash,
                        budget_limit_micros=plan.policy.max_cost_micros,
                        currency=plan.policy.currency,
                        usage_input_units=None,
                        usage_output_units=None,
                        usage_cached_units=None,
                        cost_micros=None,
                        cost_status=(
                            "estimated"
                            if plan.cost_maximum_micros is not None
                            else "unavailable"
                        ),
                        output_count=0,
                        error_code=None,
                        error_log_id=None,
                        revision=1,
                        created_at=now,
                        started_at=None,
                        completed_at=None,
                        updated_at=now,
                    ),
                )
                append_execution_event(
                    transaction,
                    account_id=account_id,
                    execution_id=row.id,
                    task_id=row.runtime_task_id,
                    event_type="ai.execution.queued",
                    revision=int(row.revision),
                    status=row.status,
                    progress=0.0,
                )
                result = self._creation_result(
                    transaction,
                    row,
                    idempotent_replay=False,
                )
                created_execution = True
        except Exception:
            raced = self._idempotent_replay(
                account_id,
                key_hash=key_hash,
                request_hash=request_hash,
            )
            if raced is not None:
                return raced
            raise
        finally:
            if not created_execution:
                self._content_store.remove_input(
                    account_id,
                    stored_input.reference,
                )
        assert task_record is not None
        self._tasks.schedule_created_task(task_record)
        return result

    def _idempotent_replay(
        self,
        account_id: str,
        *,
        key_hash: str,
        request_hash: str,
    ) -> AIExecutionCreationResult | None:
        with self._unit_of_work.read() as transaction:
            row = transaction.executions.executions.get_by_idempotency(
                transaction.session,
                account_id,
                key_hash,
            )
            if row is None:
                return None
            if row.request_hash != request_hash:
                raise task_idempotency_conflict()
            return self._creation_result(
                transaction,
                row,
                idempotent_replay=True,
            )

    @staticmethod
    def _creation_result(
        transaction: AIExecutionTransaction,
        row: AIExecution,
        *,
        idempotent_replay: bool,
    ) -> AIExecutionCreationResult:
        snapshot = transaction.executions.snapshots.get_snapshot(
            transaction.session,
            row.account_id,
            row.snapshot_id,
        )
        if snapshot is None:
            raise DomainError(
                ErrorCode.INTERNAL_ERROR,
                "AI 执行快照缺失",
                status_code=500,
                loggable=True,
            )
        return AIExecutionCreationResult(
            data={
                "executionId": row.id,
                "taskId": row.runtime_task_id,
                "accountId": row.account_id,
                "capabilityKey": row.capability_key,
                "status": row.status,
                "snapshotHash": snapshot.snapshot_hash,
                "revision": int(row.revision),
                "createdAt": row.created_at,
            },
            meta={
                "invalidations": [
                    f"account:{row.account_id}:ai-executions",
                    f"account:{row.account_id}:tasks",
                ],
                "idempotentReplay": idempotent_replay,
            },
        )


def _snapshot_row(
    *,
    account_id: str,
    plan: ExecutionPlan,
    dependency_snapshot_id: str,
    created_at: str,
) -> AIExecutionSnapshot:
    rendered = plan.rendered_prompt
    if rendered is None:
        raise DomainError(
            ErrorCode.AI_EXECUTION_INVALID,
            "创建 AI 执行前必须完成 Prompt 渲染",
            status_code=409,
        )
    positioning_hash = (
        _positioning_hash(plan.positioning)
        if plan.positioning is not None
        else None
    )
    return AIExecutionSnapshot(
        id=f"aisnap_{uuid4().hex}",
        account_id=account_id,
        capability_key=plan.route.capability_key,
        account_revision=int(plan.account.revision),
        ai_config_revision=plan.ai_config_revision,
        positioning_profile_id=(
            plan.positioning.id if plan.positioning is not None else None
        ),
        positioning_version=(
            int(plan.positioning.version)
            if plan.positioning is not None
            else None
        ),
        positioning_content_hash=positioning_hash,
        knowledge_snapshot_id=plan.knowledge_snapshot.id,
        knowledge_snapshot_version=int(plan.knowledge_snapshot.snapshot_version),
        knowledge_content_hash=plan.knowledge_snapshot.content_hash,
        account_recipe_id=plan.recipe.id,
        recipe_version=int(plan.recipe.version),
        recipe_revision=int(plan.recipe.revision),
        recipe_content_hash=plan.recipe.content_hash,
        capability_route_id=plan.route.capability_route_id,
        route_revision_id=plan.route.id,
        route_content_hash=plan.route.content_hash,
        prompt_profile_id=plan.prompt.id,
        prompt_version=int(plan.prompt.version),
        prompt_revision=int(plan.prompt.revision),
        prompt_content_hash=plan.prompt.content_hash,
        rendered_prompt_hash=rendered.rendered_hash,
        dependency_snapshot_id=dependency_snapshot_id,
        input_schema_hash=rendered.input_schema_hash,
        output_schema_hash=rendered.output_schema_hash,
        policy_json=dump_json(plan.policy.to_dict()),
        snapshot_hash=plan.snapshot_hash,
        context_manifest_hash=plan.knowledge.manifest_hash,
        created_at=created_at,
    )


def _candidate_rows(
    *,
    account_id: str,
    snapshot_id: str,
    plan: ExecutionPlan,
) -> tuple[AIExecutionCandidate, ...]:
    return tuple(
        AIExecutionCandidate(
            id=f"aicand_{uuid4().hex}",
            account_id=account_id,
            execution_snapshot_id=snapshot_id,
            ordinal=item.ordinal,
            provider_profile_id=item.provider_profile_id,
            provider_revision_id=item.provider_revision.id,
            adapter_type=item.provider_revision.adapter_type,
            credential_ref=item.provider_revision.credential_ref,
            model_profile_id=item.model_profile_id,
            model_revision_id=item.model_revision.id,
            model_id=item.model_revision.model_id,
            capability_contract_revision=item.capability_contract_revision,
            validation_run_id=item.validation.id,
            timeout_ms=item.timeout_ms,
            max_retries=item.max_retries,
            max_concurrency=item.max_concurrency,
            max_cost_micros=item.max_cost_micros,
            retry_policy_json=dump_json(item.retry_policy),
            extra_params_json=dump_json(item.extra_params),
            snapshot_hash=content_hash(item.safe_snapshot()),
        )
        for item in plan.candidates
    )


def _positioning_hash(row: object) -> str:
    return content_hash(
        {
            "id": row.id,
            "version": int(row.version),
            "audience": json.loads(row.audience_json),
            "contentPillars": json.loads(row.content_pillars_json),
            "voiceStyle": json.loads(row.voice_style_json),
            "prohibitedTerms": json.loads(row.prohibited_terms_json),
            "publishingConstraints": json.loads(row.publishing_constraints_json),
            "summary": row.summary,
        }
    )


def _request_hash(
    *,
    capability_key: str,
    plan: ExecutionPlan,
    input_value: dict[str, object],
    retry_of_execution_id: str | None,
) -> str:
    return _sha256_json(
        {
            "capabilityKey": capability_key,
            "snapshotHash": plan.snapshot_hash,
            "input": input_value,
            "retryOfExecutionId": retry_of_execution_id,
        }
    )


def _sha256_json(value: object) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


__all__ = [
    "AIExecutionCreationResult",
    "AIExecutionCreationService",
    "AI_EXECUTION_TASK_TYPE",
]
