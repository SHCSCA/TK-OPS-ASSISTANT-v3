from __future__ import annotations

import hashlib
import json
import math
from uuid import uuid4

from domain.models.ai_execution import AIExecution
from domain.models.ai_execution_snapshot import (
    AIDependencySnapshot,
    AIExecutionCandidate,
    AIExecutionSnapshot,
)
from errors import DomainError, ErrorCode
from services.ai_configuration_v1.mutation_helpers import utc_now
from services.tasks.coordinator import TaskCoordinator
from services.tasks.errors import task_idempotency_conflict
from services.tasks.types import CreateTaskCommand, RuntimeTaskRecord, TaskScope

from .content_store import AIExecutionContentStore
from .creation import (
    AIExecutionCreationResult,
    AI_EXECUTION_TASK_TYPE,
)
from .events import append_execution_event
from .policies import execution_policy_from_snapshot
from .unit_of_work import AIExecutionTransaction, AIExecutionUnitOfWork


class AIExecutionRetryService:
    """创建严格复用原输入、配置和知识哈希的新执行。"""

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

    def retry_same_snapshot(
        self,
        account_id: str,
        execution_id: str,
        *,
        idempotency_key: str,
        request_id: str,
        operation_id: str,
    ) -> AIExecutionCreationResult:
        key_hash = _sha256_text(idempotency_key.strip())
        source, source_snapshot = self._load_source(account_id, execution_id)
        request_hash = _sha256_json(
            {
                "mode": "same_snapshot",
                "sourceExecutionId": execution_id,
                "snapshotHash": source_snapshot.snapshot_hash,
            }
        )
        replay = self._idempotent_replay(
            account_id,
            key_hash=key_hash,
            request_hash=request_hash,
        )
        if replay is not None:
            return replay
        input_value, input_hash = self._content_store.read_input(
            account_id,
            source.input_ref,
        )
        if input_hash != source.input_hash:
            raise _damaged()
        new_execution_id = f"aiexec_{uuid4().hex}"
        stored_input = self._content_store.store_input(
            account_id,
            new_execution_id,
            input_value,
        )
        if stored_input.content_hash != source.input_hash:
            self._content_store.remove_input(account_id, stored_input.reference)
            raise _damaged()
        task_record: RuntimeTaskRecord | None = None
        created = False
        try:
            with self._unit_of_work.write() as transaction:
                transaction.accounts.acquire_write_lock(
                    transaction.session,
                    account_id=account_id,
                )
                existing = transaction.executions.executions.get_by_idempotency(
                    transaction.session,
                    account_id,
                    key_hash,
                )
                if existing is not None:
                    if existing.request_hash != request_hash:
                        raise task_idempotency_conflict()
                    return _accepted(
                        transaction,
                        existing,
                        idempotent_replay=True,
                    )
                current = transaction.executions.executions.get_scoped(
                    transaction.session,
                    account_id,
                    execution_id,
                )
                if current is None:
                    raise _not_found()
                if current.status not in {"failed", "completed"}:
                    raise DomainError(
                        ErrorCode.AI_EXECUTION_STATE_CONFLICT,
                        "只有终态 AI 执行可以按原快照重试",
                        status_code=409,
                    )
                snapshot = transaction.executions.snapshots.get_snapshot(
                    transaction.session,
                    account_id,
                    current.snapshot_id,
                )
                if snapshot is None or snapshot.snapshot_hash != source_snapshot.snapshot_hash:
                    raise _damaged()
                dependency = transaction.session.get(
                    AIDependencySnapshot,
                    snapshot.dependency_snapshot_id,
                )
                candidates = transaction.executions.snapshots.list_candidates(
                    transaction.session,
                    account_id,
                    snapshot.id,
                )
                if dependency is None or not candidates:
                    raise _damaged()
                now = utc_now()
                cloned_dependency = transaction.ai.dependency_snapshots.add(
                    transaction.session,
                    AIDependencySnapshot(
                        id=f"deps_{uuid4().hex}",
                        owner_type="execution_preflight",
                        owner_id=new_execution_id,
                        owner_revision=1,
                        status=dependency.status,
                        graph_json=dependency.graph_json,
                        issues_json=dependency.issues_json,
                        repair_actions_json=dependency.repair_actions_json,
                        content_hash=dependency.content_hash,
                        created_at=now,
                    ),
                )
                cloned_snapshot = transaction.executions.snapshots.add_snapshot(
                    transaction.session,
                    _clone_snapshot(
                        snapshot,
                        dependency_snapshot_id=cloned_dependency.id,
                        created_at=now,
                    ),
                )
                transaction.executions.snapshots.add_candidates(
                    transaction.session,
                    tuple(
                        _clone_candidate(
                            item,
                            snapshot_id=cloned_snapshot.id,
                        )
                        for item in candidates
                    ),
                )
                policy = execution_policy_from_snapshot(snapshot.policy_json)
                task_record = self._tasks.create_task_in_session(
                    transaction.session,
                    CreateTaskCommand(
                        scope=TaskScope.ACCOUNT,
                        account_id=account_id,
                        task_type=AI_EXECUTION_TASK_TYPE,
                        payload={
                            "executionId": new_execution_id,
                            "snapshotHash": snapshot.snapshot_hash,
                        },
                        idempotency_key=(
                            f"ai-execution-task:{new_execution_id}"
                        ),
                        request_id=request_id,
                        operation_id=operation_id,
                        timeout_seconds=max(
                            1,
                            math.ceil(policy.timeout_ms / 1_000),
                        ),
                        retry_of_task_id=current.runtime_task_id,
                        attempt=1,
                    ),
                )
                row = transaction.executions.executions.add(
                    transaction.session,
                    AIExecution(
                        id=new_execution_id,
                        account_id=account_id,
                        capability_key=current.capability_key,
                        status="queued",
                        completion_kind=None,
                        failure_kind=None,
                        snapshot_id=cloned_snapshot.id,
                        runtime_task_id=task_record.id,
                        active_job_id=None,
                        retry_of_execution_id=current.id,
                        input_ref=stored_input.reference,
                        input_hash=stored_input.content_hash,
                        idempotency_key_hash=key_hash,
                        request_hash=request_hash,
                        budget_limit_micros=int(current.budget_limit_micros),
                        currency=current.currency,
                        usage_input_units=None,
                        usage_output_units=None,
                        usage_cached_units=None,
                        cost_micros=None,
                        cost_status=(
                            "unavailable"
                            if current.cost_status == "unavailable"
                            else "estimated"
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
                result = _accepted(
                    transaction,
                    row,
                    idempotent_replay=False,
                )
                created = True
        except Exception:
            replay = self._idempotent_replay(
                account_id,
                key_hash=key_hash,
                request_hash=request_hash,
            )
            if replay is not None:
                return replay
            raise
        finally:
            if not created:
                self._content_store.remove_input(
                    account_id,
                    stored_input.reference,
                )
        assert task_record is not None
        self._tasks.schedule_created_task(task_record)
        return result

    def _load_source(
        self,
        account_id: str,
        execution_id: str,
    ) -> tuple[AIExecution, AIExecutionSnapshot]:
        with self._unit_of_work.read() as transaction:
            execution = transaction.executions.executions.get_scoped(
                transaction.session,
                account_id,
                execution_id,
            )
            if execution is None:
                raise _not_found()
            if execution.status not in {"failed", "completed"}:
                raise DomainError(
                    ErrorCode.AI_EXECUTION_STATE_CONFLICT,
                    "只有终态 AI 执行可以按原快照重试",
                    status_code=409,
                )
            snapshot = transaction.executions.snapshots.get_snapshot(
                transaction.session,
                account_id,
                execution.snapshot_id,
            )
            if snapshot is None:
                raise _damaged()
            return execution, snapshot

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
            return _accepted(transaction, row, idempotent_replay=True)


def _clone_snapshot(
    row: AIExecutionSnapshot,
    *,
    dependency_snapshot_id: str,
    created_at: str,
) -> AIExecutionSnapshot:
    return AIExecutionSnapshot(
        id=f"aisnap_{uuid4().hex}",
        account_id=row.account_id,
        capability_key=row.capability_key,
        account_revision=int(row.account_revision),
        ai_config_revision=int(row.ai_config_revision),
        positioning_profile_id=row.positioning_profile_id,
        positioning_version=row.positioning_version,
        positioning_content_hash=row.positioning_content_hash,
        knowledge_snapshot_id=row.knowledge_snapshot_id,
        knowledge_snapshot_version=int(row.knowledge_snapshot_version),
        knowledge_content_hash=row.knowledge_content_hash,
        account_recipe_id=row.account_recipe_id,
        recipe_version=int(row.recipe_version),
        recipe_revision=int(row.recipe_revision),
        recipe_content_hash=row.recipe_content_hash,
        capability_route_id=row.capability_route_id,
        route_revision_id=row.route_revision_id,
        route_content_hash=row.route_content_hash,
        prompt_profile_id=row.prompt_profile_id,
        prompt_version=int(row.prompt_version),
        prompt_revision=int(row.prompt_revision),
        prompt_content_hash=row.prompt_content_hash,
        rendered_prompt_hash=row.rendered_prompt_hash,
        dependency_snapshot_id=dependency_snapshot_id,
        input_schema_hash=row.input_schema_hash,
        output_schema_hash=row.output_schema_hash,
        policy_json=row.policy_json,
        snapshot_hash=row.snapshot_hash,
        context_manifest_hash=row.context_manifest_hash,
        created_at=created_at,
    )


def _clone_candidate(
    row: AIExecutionCandidate,
    *,
    snapshot_id: str,
) -> AIExecutionCandidate:
    return AIExecutionCandidate(
        id=f"aicand_{uuid4().hex}",
        account_id=row.account_id,
        execution_snapshot_id=snapshot_id,
        ordinal=int(row.ordinal),
        provider_profile_id=row.provider_profile_id,
        provider_revision_id=row.provider_revision_id,
        adapter_type=row.adapter_type,
        credential_ref=row.credential_ref,
        model_profile_id=row.model_profile_id,
        model_revision_id=row.model_revision_id,
        model_id=row.model_id,
        capability_contract_revision=int(row.capability_contract_revision),
        validation_run_id=row.validation_run_id,
        timeout_ms=int(row.timeout_ms),
        max_retries=int(row.max_retries),
        max_concurrency=int(row.max_concurrency),
        max_cost_micros=int(row.max_cost_micros),
        retry_policy_json=row.retry_policy_json,
        extra_params_json=row.extra_params_json,
        snapshot_hash=row.snapshot_hash,
    )


def _accepted(
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
        raise _damaged()
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


def _not_found() -> DomainError:
    return DomainError(
        ErrorCode.AI_EXECUTION_NOT_FOUND,
        "AI 执行不存在",
        status_code=404,
    )


def _damaged() -> DomainError:
    return DomainError(
        ErrorCode.AI_EXECUTION_INVALID,
        "AI 执行原快照不完整，不能安全重试",
        status_code=409,
        loggable=True,
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


__all__ = ["AIExecutionRetryService"]
