from __future__ import annotations

from datetime import timedelta

from sqlalchemy.exc import IntegrityError

from domain.models.runtime_task import RuntimeTask
from repositories.runtime_task_repository import RuntimeTaskRepository
from services.tasks.errors import (
    task_already_running,
    task_idempotency_conflict,
    task_snapshot_invalid,
)
from services.tasks.handler_registry import TaskHandlerRegistry
from services.tasks.service_support import TaskServiceSupport, to_utc_text
from services.tasks.snapshot import TaskSnapshotPolicy, task_id_for
from services.tasks.types import (
    CreateTaskCommand,
    FrozenTaskSnapshot,
    RuntimeTaskRecord,
    TaskHandlerDefinition,
    TaskRuntimePolicy,
    TaskStatus,
)


class TaskCreationOperations:
    """封装任务创建、活动态约束和持久幂等判断。"""

    def __init__(
        self,
        *,
        repository: RuntimeTaskRepository,
        handler_registry: TaskHandlerRegistry,
        snapshot_policy: TaskSnapshotPolicy,
        runtime_policy: TaskRuntimePolicy,
        support: TaskServiceSupport,
    ) -> None:
        self._repository = repository
        self._handler_registry = handler_registry
        self._snapshot_policy = snapshot_policy
        self._runtime_policy = runtime_policy
        self._support = support

    def create(self, command: CreateTaskCommand) -> RuntimeTaskRecord:
        definition = self._handler_registry.require(command.task_type)
        task_type = definition.task_type.strip()
        self._support.validate_scope(command.scope, command.account_id)
        if command.attempt < 1:
            raise task_snapshot_invalid(
                "任务尝试次数必须大于零",
                field="attempt",
            )
        timeout_seconds = self._resolve_timeout(command, definition)
        snapshot = self._snapshot_policy.freeze(
            command.payload,
            allowed_fields=definition.allowed_snapshot_fields,
            handler_version=definition.handler_version,
            idempotency_key=command.idempotency_key,
            request_id=command.request_id,
            operation_id=command.operation_id,
            attempt=command.attempt,
            retry_of_task_id=command.retry_of_task_id,
            requested_timeout_seconds=command.timeout_seconds,
        )
        task_id = task_id_for(
            scope_key=self._support.scope_key(
                command.scope,
                command.account_id,
            ),
            task_type=task_type,
            idempotency_key_hash=snapshot.key_hash,
        )
        now = self._support.now()
        now_text = to_utc_text(now)
        timeout_at = to_utc_text(
            now + timedelta(seconds=timeout_seconds)
        )
        task = RuntimeTask(
            id=task_id,
            scope=command.scope.value,
            account_id=command.account_id,
            task_type=task_type,
            status=TaskStatus.QUEUED.value,
            completion_kind=None,
            failure_kind=None,
            progress=0.0,
            cancellable=definition.cancellable,
            timeout_at=timeout_at,
            attempt=command.attempt,
            retry_of_task_id=command.retry_of_task_id,
            config_snapshot_json=snapshot.serialized,
            result_ref=None,
            error_code=None,
            error_log_id=None,
            revision=1,
            created_at=now_text,
            started_at=None,
            completed_at=None,
            updated_at=now_text,
            idempotency_key_hash=snapshot.key_hash,
            request_hash=snapshot.request_hash,
            handler_version=snapshot.handler_version,
        )

        try:
            with self._repository.transaction() as session:
                if definition.single_active_per_scope:
                    self._repository.acquire_write_lock(session)
                existing = self._repository.get_any(session, task_id)
                if existing is not None:
                    return self._resolve_idempotent_replay(
                        self._repository.to_record(existing),
                        command=command,
                        snapshot=snapshot,
                        active_conflict_error_code=(
                            definition.active_conflict_error_code
                        ),
                    )
                if definition.single_active_per_scope:
                    active = self._repository.find_active(
                        session,
                        scope=command.scope,
                        account_id=command.account_id,
                        task_type=task_type,
                    )
                    if active is not None:
                        raise task_already_running(
                            active.id,
                            error_code=definition.active_conflict_error_code,
                        )
                record = self._repository.add(session, task)
                self._support.append_event(session, record, "task.queued")
                return record
        except IntegrityError as exc:
            return self._resolve_create_race(
                task_id,
                command=command,
                snapshot=snapshot,
                active_conflict_error_code=(
                    definition.active_conflict_error_code
                ),
                integrity_error=exc,
            )

    def _resolve_create_race(
        self,
        task_id: str,
        *,
        command: CreateTaskCommand,
        snapshot: FrozenTaskSnapshot,
        active_conflict_error_code: str,
        integrity_error: IntegrityError,
    ) -> RuntimeTaskRecord:
        with self._repository.transaction() as session:
            existing = self._repository.get_any(session, task_id)
            if existing is None:
                raise integrity_error
            return self._resolve_idempotent_replay(
                self._repository.to_record(existing),
                command=command,
                snapshot=snapshot,
                active_conflict_error_code=active_conflict_error_code,
            )

    def _resolve_idempotent_replay(
        self,
        existing: RuntimeTaskRecord,
        *,
        command: CreateTaskCommand,
        snapshot: FrozenTaskSnapshot,
        active_conflict_error_code: str,
    ) -> RuntimeTaskRecord:
        stored = self._snapshot_policy.load(existing.config_snapshot_json)
        if (
            existing.scope is not command.scope
            or existing.account_id != command.account_id
            or existing.task_type != command.task_type.strip()
            or existing.idempotency_key_hash != snapshot.key_hash
            or existing.request_hash != snapshot.request_hash
            or existing.handler_version != snapshot.handler_version
            or stored.key_hash != snapshot.key_hash
            or stored.request_hash != snapshot.request_hash
            or stored.key_hash != existing.idempotency_key_hash
            or stored.request_hash != existing.request_hash
            or stored.handler_version != existing.handler_version
            or stored.creation_attempt != command.attempt
            or stored.retry_of_task_id != command.retry_of_task_id
            or stored.requested_timeout_seconds != command.timeout_seconds
            or stored.retry_of_task_id != existing.retry_of_task_id
        ):
            raise task_idempotency_conflict()
        if existing.status is not TaskStatus.QUEUED:
            raise task_already_running(
                existing.id,
                error_code=active_conflict_error_code,
            )
        return existing

    def _resolve_timeout(
        self,
        command: CreateTaskCommand,
        definition: TaskHandlerDefinition,
    ) -> int:
        if command.timeout_seconds is not None:
            timeout = command.timeout_seconds
        elif definition.timeout_seconds is not None:
            timeout = definition.timeout_seconds
        else:
            timeout = self._runtime_policy.default_timeout_seconds
        if timeout <= 0 or timeout > self._runtime_policy.max_timeout_seconds:
            raise task_snapshot_invalid(
                "任务超时必须位于配置总线允许范围内",
                field="timeoutSeconds",
            )
        return timeout
