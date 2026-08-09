from __future__ import annotations

import logging
import math
from datetime import datetime

from errors import DomainError
from repositories.runtime_task_repository import RuntimeTaskRepository
from services.tasks.errors import (
    TaskCancellationRequested,
    task_not_found,
    task_snapshot_invalid,
    task_state_conflict,
)
from services.tasks.events import TaskEventSink
from services.tasks.handler_registry import TaskHandlerRegistry
from services.tasks.service_support import (
    Clock,
    TaskServiceSupport,
    to_utc_text,
    utc_now,
)
from services.tasks.snapshot import TaskSnapshotPolicy
from services.tasks.task_creation import TaskCreationOperations
from services.tasks.task_transitions import TaskTransitionOperations
from services.tasks.types import (
    CreateTaskCommand,
    RuntimeTaskRecord,
    TaskFailureKind,
    TaskRuntimePolicy,
    TaskScope,
    TaskStatus,
)

log = logging.getLogger(__name__)


class TaskService:
    """维护持久任务状态机，并在同一事务内追加 outbox 事件。"""

    def __init__(
        self,
        *,
        repository: RuntimeTaskRepository,
        handler_registry: TaskHandlerRegistry,
        snapshot_policy: TaskSnapshotPolicy,
        event_sink: TaskEventSink,
        runtime_policy: TaskRuntimePolicy,
        clock: Clock | None = None,
    ) -> None:
        self._repository = repository
        self._handler_registry = handler_registry
        self._snapshot_policy = snapshot_policy
        self._event_sink = event_sink
        self._runtime_policy = runtime_policy
        self._clock = clock or _utc_now
        self._support = TaskServiceSupport(
            repository=repository,
            event_sink=event_sink,
            clock=lambda: self._clock(),
        )
        self._creation = TaskCreationOperations(
            repository=repository,
            handler_registry=handler_registry,
            snapshot_policy=snapshot_policy,
            runtime_policy=runtime_policy,
            support=self._support,
        )
        self._transitions = TaskTransitionOperations(
            repository=repository,
            support=self._support,
        )

    def create_task(self, command: CreateTaskCommand) -> RuntimeTaskRecord:
        try:
            return self._create_task(command)
        except DomainError:
            raise
        except Exception:
            log.exception(
                "创建持久任务失败",
                extra={
                    "task_type": command.task_type,
                    "account_id": command.account_id,
                },
            )
            raise

    def get_system_task(self, task_id: str) -> RuntimeTaskRecord:
        return self._get_scoped_task(
            task_id,
            scope=TaskScope.SYSTEM,
            account_id=None,
        )

    def get_account_task(
        self,
        account_id: str,
        task_id: str,
    ) -> RuntimeTaskRecord:
        return self._get_scoped_task(
            task_id,
            scope=TaskScope.ACCOUNT,
            account_id=account_id,
        )

    def get_task(self, task_id: str) -> RuntimeTaskRecord:
        try:
            record = self._repository.get_record(task_id)
            if record is None:
                raise task_not_found()
            return record
        except DomainError:
            raise
        except Exception:
            log.exception("读取持久任务失败", extra={"task_id": task_id})
            raise

    def cancel_system_task(self, task_id: str) -> RuntimeTaskRecord:
        return self._cancel_task(
            task_id,
            scope=TaskScope.SYSTEM,
            account_id=None,
        )

    def cancel_account_task(
        self,
        account_id: str,
        task_id: str,
    ) -> RuntimeTaskRecord:
        return self._cancel_task(
            task_id,
            scope=TaskScope.ACCOUNT,
            account_id=account_id,
        )

    def claim_running(self, task_id: str) -> RuntimeTaskRecord:
        """由执行器原子领取 queued 任务。"""

        now = self._now_text()
        try:
            return self._transitions.claim_running(task_id, now=now)
        except DomainError:
            raise
        except Exception:
            log.exception("领取持久任务失败", extra={"task_id": task_id})
            raise

    def update_progress(
        self,
        task_id: str,
        progress: float,
    ) -> RuntimeTaskRecord:
        if not math.isfinite(progress) or not 0 <= progress <= 1:
            raise task_snapshot_invalid(
                "任务进度必须是 0 到 1 之间的有限数值",
                field="progress",
            )

        now = self._now_text()
        try:
            return self._transitions.update_progress(
                task_id,
                progress,
                now=now,
            )
        except (DomainError, TaskCancellationRequested):
            raise
        except Exception:
            log.exception("更新任务进度失败", extra={"task_id": task_id})
            raise

    def complete_success(
        self,
        task_id: str,
        *,
        result_ref: str | None,
    ) -> RuntimeTaskRecord:
        return self._finish_task(
            task_id,
            success_result_ref=result_ref,
            force_cancelled=False,
        )

    def complete_cancelled(self, task_id: str) -> RuntimeTaskRecord:
        return self._finish_task(
            task_id,
            success_result_ref=None,
            force_cancelled=True,
        )

    def fail(
        self,
        task_id: str,
        *,
        failure_kind: TaskFailureKind,
        error_code: str,
        error_log_id: str | None = None,
    ) -> RuntimeTaskRecord:
        now = self._now_text()
        try:
            return self._transitions.fail(
                task_id,
                failure_kind=failure_kind,
                error_code=error_code,
                error_log_id=error_log_id,
                now=now,
            )
        except DomainError:
            raise
        except Exception:
            log.exception(
                "持久任务失败态写入失败",
                extra={
                    "task_id": task_id,
                    "failure_kind": failure_kind.value,
                    "error_code": error_code,
                },
            )
            raise

    def requeue_for_recovery(self, task_id: str) -> RuntimeTaskRecord:
        now = self._now_text()
        try:
            return self._transitions.requeue_for_recovery(task_id, now=now)
        except DomainError:
            raise
        except Exception:
            log.exception("恢复任务重新排队失败", extra={"task_id": task_id})
            raise

    def list_non_terminal(self) -> list[RuntimeTaskRecord]:
        try:
            return self._repository.list_non_terminal()
        except Exception:
            log.exception("读取待恢复任务失败")
            raise

    def list_system_tasks(self, *, limit: int = 200) -> list[RuntimeTaskRecord]:
        if isinstance(limit, bool) or limit < 1 or limit > 200:
            raise ValueError("系统任务列表条数必须位于 1 到 200 之间")
        try:
            return self._repository.list_system_tasks(limit=limit)
        except Exception:
            log.exception("读取系统任务列表失败", extra={"limit": limit})
            raise

    def list_account_tasks(
        self,
        account_id: str,
        *,
        limit: int = 200,
    ) -> list[RuntimeTaskRecord]:
        if isinstance(limit, bool) or limit < 1 or limit > 200:
            raise ValueError("账号任务列表条数必须位于 1 到 200 之间")
        try:
            return self._repository.list_account_tasks(account_id, limit=limit)
        except Exception:
            log.exception(
                "读取账号任务列表失败",
                extra={"account_id": account_id, "limit": limit},
            )
            raise

    def retry_task(
        self,
        task_id: str,
        *,
        idempotency_key: str,
        request_id: str,
        operation_id: str,
    ) -> RuntimeTaskRecord:
        original = self.get_task(task_id)
        if original.status is not TaskStatus.FAILED:
            raise task_state_conflict("只有失败任务可以创建重试任务")
        definition = self._handler_registry.require(original.task_type)
        snapshot = self._snapshot_policy.load(
            original.config_snapshot_json,
            expected_handler_version=definition.handler_version,
        )
        if (
            snapshot.key_hash != original.idempotency_key_hash
            or snapshot.request_hash != original.request_hash
            or snapshot.handler_version != original.handler_version
        ):
            raise task_snapshot_invalid("任务显式摘要与持久快照不一致")
        return self.create_task(
            CreateTaskCommand(
                scope=original.scope,
                account_id=original.account_id,
                task_type=original.task_type,
                payload=snapshot.payload,
                idempotency_key=idempotency_key,
                request_id=request_id,
                operation_id=operation_id,
                retry_of_task_id=original.id,
                attempt=original.attempt + 1,
            )
        )

    def _create_task(self, command: CreateTaskCommand) -> RuntimeTaskRecord:
        return self._creation.create(command)

    def _get_scoped_task(
        self,
        task_id: str,
        *,
        scope: TaskScope,
        account_id: str | None,
    ) -> RuntimeTaskRecord:
        try:
            with self._repository.transaction() as session:
                return self._support.require_scoped_record(
                    session,
                    task_id,
                    scope=scope,
                    account_id=account_id,
                )
        except DomainError:
            raise
        except Exception:
            log.exception(
                "读取作用域任务失败",
                extra={"task_id": task_id, "account_id": account_id},
            )
            raise

    def _cancel_task(
        self,
        task_id: str,
        *,
        scope: TaskScope,
        account_id: str | None,
    ) -> RuntimeTaskRecord:
        now = self._now_text()
        try:
            return self._transitions.cancel_task(
                task_id,
                scope=scope,
                account_id=account_id,
                now=now,
            )
        except DomainError:
            raise
        except Exception:
            log.exception(
                "取消持久任务失败",
                extra={"task_id": task_id, "account_id": account_id},
            )
            raise

    def _finish_task(
        self,
        task_id: str,
        *,
        success_result_ref: str | None,
        force_cancelled: bool,
    ) -> RuntimeTaskRecord:
        now = self._now_text()
        try:
            return self._transitions.finish_task(
                task_id,
                success_result_ref=success_result_ref,
                force_cancelled=force_cancelled,
                now=now,
            )
        except DomainError:
            raise
        except Exception:
            log.exception("完成持久任务失败", extra={"task_id": task_id})
            raise

    def _now(self) -> datetime:
        return self._support.now()

    def _now_text(self) -> str:
        return self._support.now_text()


def _utc_now() -> datetime:
    return utc_now()


def _to_utc_text(value: datetime) -> str:
    return to_utc_text(value)
