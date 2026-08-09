from __future__ import annotations

from repositories.runtime_task_repository import RuntimeTaskRepository
from services.tasks.errors import (
    TaskCancellationRequested,
    task_not_cancellable,
    task_state_conflict,
)
from services.tasks.service_support import TaskServiceSupport
from services.tasks.types import (
    NON_TERMINAL_STATUSES,
    RuntimeTaskRecord,
    TaskCompletionKind,
    TaskFailureKind,
    TaskScope,
    TaskStatus,
)


class TaskTransitionOperations:
    """封装持久任务状态转换及其事务内事件。"""

    def __init__(
        self,
        *,
        repository: RuntimeTaskRepository,
        support: TaskServiceSupport,
    ) -> None:
        self._repository = repository
        self._support = support

    def claim_running(
        self,
        task_id: str,
        *,
        now: str,
    ) -> RuntimeTaskRecord:
        with self._repository.transaction() as session:
            task = self._support.require_any(session, task_id)
            current = self._repository.to_record(task)
            if current.status is TaskStatus.CANCELLING or current.is_terminal:
                return current
            if current.status is not TaskStatus.QUEUED:
                raise task_state_conflict("任务当前不能进入运行态")
            updated = self._repository.transition(
                session,
                task_id,
                expected_statuses=(TaskStatus.QUEUED,),
                expected_revision=current.revision,
                values={
                    "status": TaskStatus.RUNNING.value,
                    "started_at": now,
                    "updated_at": now,
                },
            )
            record = self._support.require_transition(updated)
            self._support.append_event(session, record, "task.started")
            return record

    def update_progress(
        self,
        task_id: str,
        progress: float,
        *,
        now: str,
    ) -> RuntimeTaskRecord:
        with self._repository.transaction() as session:
            task = self._support.require_any(session, task_id)
            current = self._repository.to_record(task)
            if current.status is TaskStatus.CANCELLING:
                raise TaskCancellationRequested()
            if current.status is not TaskStatus.RUNNING:
                raise task_state_conflict("仅运行中的任务可以更新进度")
            if progress <= current.progress:
                return current
            updated = self._repository.transition(
                session,
                task_id,
                expected_statuses=(TaskStatus.RUNNING,),
                expected_revision=current.revision,
                values={"progress": progress, "updated_at": now},
            )
            if updated is None:
                latest = self._support.require_any_record(session, task_id)
                if latest.status is TaskStatus.CANCELLING:
                    raise TaskCancellationRequested()
                if latest.progress >= progress:
                    return latest
                raise task_state_conflict()
            self._support.append_event(session, updated, "task.progress")
            return updated

    def fail(
        self,
        task_id: str,
        *,
        failure_kind: TaskFailureKind,
        error_code: str,
        error_log_id: str | None,
        now: str,
    ) -> RuntimeTaskRecord:
        with self._repository.transaction() as session:
            task = self._support.require_any(session, task_id)
            current = self._repository.to_record(task)
            if current.is_terminal:
                return current
            updated = self._repository.transition(
                session,
                task_id,
                expected_statuses=tuple(NON_TERMINAL_STATUSES),
                expected_revision=current.revision,
                values={
                    "status": TaskStatus.FAILED.value,
                    "completion_kind": None,
                    "failure_kind": failure_kind.value,
                    "result_ref": None,
                    "error_code": error_code,
                    "error_log_id": error_log_id,
                    "completed_at": now,
                    "updated_at": now,
                },
            )
            if updated is None:
                latest = self._support.require_any_record(session, task_id)
                if latest.is_terminal:
                    return latest
                raise task_state_conflict()
            self._support.append_event(session, updated, "task.failed")
            return updated

    def requeue_for_recovery(
        self,
        task_id: str,
        *,
        now: str,
    ) -> RuntimeTaskRecord:
        with self._repository.transaction() as session:
            task = self._support.require_any(session, task_id)
            current = self._repository.to_record(task)
            if current.status is TaskStatus.QUEUED:
                return current
            if current.status is not TaskStatus.RUNNING:
                raise task_state_conflict("仅中断的运行任务可以恢复排队")
            updated = self._repository.transition(
                session,
                task_id,
                expected_statuses=(TaskStatus.RUNNING,),
                expected_revision=current.revision,
                values={
                    "status": TaskStatus.QUEUED.value,
                    "progress": 0.0,
                    "attempt": current.attempt + 1,
                    "started_at": None,
                    "updated_at": now,
                },
            )
            record = self._support.require_transition(updated)
            self._support.append_event(session, record, "task.queued")
            return record

    def cancel_task(
        self,
        task_id: str,
        *,
        scope: TaskScope,
        account_id: str | None,
        now: str,
    ) -> RuntimeTaskRecord:
        with self._repository.transaction() as session:
            current = self._support.require_scoped_record(
                session,
                task_id,
                scope=scope,
                account_id=account_id,
            )
            if current.is_terminal or current.status is TaskStatus.CANCELLING:
                return current
            if not current.cancellable:
                raise task_not_cancellable()
            updated = self._repository.transition(
                session,
                task_id,
                expected_statuses=(TaskStatus.QUEUED, TaskStatus.RUNNING),
                expected_revision=current.revision,
                values={
                    "status": TaskStatus.CANCELLING.value,
                    "updated_at": now,
                },
            )
            if updated is None:
                latest = self._support.require_scoped_record(
                    session,
                    task_id,
                    scope=scope,
                    account_id=account_id,
                )
                if latest.is_terminal or latest.status is TaskStatus.CANCELLING:
                    return latest
                raise task_state_conflict()
            self._support.append_event(session, updated, "task.cancelling")
            return updated

    def finish_task(
        self,
        task_id: str,
        *,
        success_result_ref: str | None,
        force_cancelled: bool,
        now: str,
    ) -> RuntimeTaskRecord:
        with self._repository.transaction() as session:
            task = self._support.require_any(session, task_id)
            current = self._repository.to_record(task)
            if current.is_terminal:
                return current
            cancelled = (
                force_cancelled or current.status is TaskStatus.CANCELLING
            )
            expected_statuses = (
                tuple(NON_TERMINAL_STATUSES)
                if cancelled
                else (TaskStatus.RUNNING,)
            )
            if not cancelled and current.status is not TaskStatus.RUNNING:
                raise task_state_conflict("仅运行中的任务可以成功完成")
            updated = self._repository.transition(
                session,
                task_id,
                expected_statuses=expected_statuses,
                expected_revision=current.revision,
                values={
                    "status": TaskStatus.COMPLETED.value,
                    "completion_kind": (
                        TaskCompletionKind.CANCELLED.value
                        if cancelled
                        else TaskCompletionKind.SUCCEEDED.value
                    ),
                    "failure_kind": None,
                    "progress": current.progress if cancelled else 1.0,
                    "result_ref": None if cancelled else success_result_ref,
                    "error_code": None,
                    "error_log_id": None,
                    "completed_at": now,
                    "updated_at": now,
                },
            )
            if updated is None:
                latest = self._support.require_any_record(session, task_id)
                if latest.is_terminal:
                    return latest
                raise task_state_conflict()
            self._support.append_event(session, updated, "task.completed")
            return updated
