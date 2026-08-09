from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Protocol

from errors import DomainError, ErrorCode
from services.tasks.handler_registry import TaskHandlerRegistry
from services.tasks.snapshot import TaskSnapshotPolicy
from services.tasks.task_service import TaskService
from services.tasks.types import (
    RuntimeTaskRecord,
    TaskFailureKind,
    TaskRecoveryPlan,
    TaskResumePolicy,
    TaskStatus,
)

log = logging.getLogger(__name__)


class TaskScheduler(Protocol):
    def schedule(self, task_id: str) -> None: ...


class TaskRecoveryService:
    """把 Runtime 重启时遗留的非终态任务转换为明确可审计状态。"""

    def __init__(
        self,
        *,
        task_service: TaskService,
        handler_registry: TaskHandlerRegistry,
        snapshot_policy: TaskSnapshotPolicy,
        scheduler: TaskScheduler,
    ) -> None:
        self._task_service = task_service
        self._handler_registry = handler_registry
        self._snapshot_policy = snapshot_policy
        self._scheduler = scheduler

    async def recover(self) -> TaskRecoveryPlan:
        plan = await self.prepare_recovery()
        self.schedule_recovery(plan)
        return plan

    async def prepare_recovery(self) -> TaskRecoveryPlan:
        """只整理持久任务状态，不让可恢复任务提前开始执行。"""

        plan = await asyncio.to_thread(self._prepare_recovery)
        return plan

    def schedule_recovery(self, plan: TaskRecoveryPlan) -> None:
        """在启动对账完成后统一调度已确认可恢复的任务。"""

        for task_id in plan.resumable_task_ids:
            self._scheduler.schedule(task_id)

    def _prepare_recovery(self) -> TaskRecoveryPlan:
        resumable: list[str] = []
        interrupted: list[str] = []
        timed_out: list[str] = []
        cancelled: list[str] = []
        failed_recoveries: list[str] = []

        for record in self._task_service.list_non_terminal():
            try:
                if _is_timed_out(record):
                    self._task_service.fail(
                        record.id,
                        failure_kind=TaskFailureKind.TIMED_OUT,
                        error_code=ErrorCode.TASK_TIMEOUT.value,
                    )
                    timed_out.append(record.id)
                    continue
                if record.status is TaskStatus.CANCELLING:
                    self._task_service.complete_cancelled(record.id)
                    cancelled.append(record.id)
                    continue

                definition = self._handler_registry.get(record.task_type)
                if definition is None:
                    self._mark_interrupted(
                        record,
                        error_code=ErrorCode.TASK_HANDLER_NOT_FOUND.value,
                    )
                    interrupted.append(record.id)
                    continue
                if record.handler_version != definition.handler_version:
                    self._mark_interrupted(
                        record,
                        error_code=ErrorCode.TASK_SNAPSHOT_INVALID.value,
                    )
                    interrupted.append(record.id)
                    continue
                try:
                    snapshot = self._snapshot_policy.load(
                        record.config_snapshot_json,
                        expected_handler_version=definition.handler_version,
                    )
                    if (
                        snapshot.key_hash != record.idempotency_key_hash
                        or snapshot.request_hash != record.request_hash
                        or snapshot.handler_version != record.handler_version
                    ):
                        raise ValueError("任务显式摘要与持久快照不一致")
                except DomainError as exc:
                    log.exception(
                        "持久任务快照无法用于重启恢复",
                        extra={
                            "task_id": record.id,
                            "error_code": exc.error_code,
                        },
                    )
                    self._mark_interrupted(
                        record,
                        error_code=exc.error_code,
                    )
                    interrupted.append(record.id)
                    continue
                except ValueError:
                    log.exception(
                        "持久任务显式摘要与快照不一致",
                        extra={
                            "task_id": record.id,
                            "error_code": ErrorCode.TASK_SNAPSHOT_INVALID.value,
                        },
                    )
                    self._mark_interrupted(
                        record,
                        error_code=ErrorCode.TASK_SNAPSHOT_INVALID.value,
                    )
                    interrupted.append(record.id)
                    continue
                if record.status is TaskStatus.QUEUED:
                    resumable.append(record.id)
                    continue
                if definition.resume_policy is TaskResumePolicy.RESUME:
                    recovered = self._task_service.requeue_for_recovery(record.id)
                    resumable.append(recovered.id)
                    continue
                self._mark_interrupted(
                    record,
                    error_code=ErrorCode.TASK_STATE_CONFLICT.value,
                )
                interrupted.append(record.id)
            except DomainError as exc:
                log.exception(
                    "恢复持久任务时遇到领域错误",
                    extra={
                        "task_id": record.id,
                        "error_code": exc.error_code,
                    },
                )
                failed_recoveries.append(record.id)
            except Exception:
                log.exception(
                    "恢复持久任务失败",
                    extra={"task_id": record.id},
                )
                failed_recoveries.append(record.id)

        if failed_recoveries:
            joined_ids = ",".join(failed_recoveries)
            raise RuntimeError(f"以下持久任务恢复失败：{joined_ids}")
        return TaskRecoveryPlan(
            resumable_task_ids=tuple(resumable),
            interrupted_task_ids=tuple(interrupted),
            timed_out_task_ids=tuple(timed_out),
            cancelled_task_ids=tuple(cancelled),
        )

    def _mark_interrupted(
        self,
        record: RuntimeTaskRecord,
        *,
        error_code: str,
    ) -> None:
        self._task_service.fail(
            record.id,
            failure_kind=TaskFailureKind.RESTART_INTERRUPTED,
            error_code=error_code,
        )


def _is_timed_out(record: RuntimeTaskRecord) -> bool:
    if record.timeout_at is None:
        return True
    try:
        deadline = datetime.fromisoformat(record.timeout_at.replace("Z", "+00:00"))
    except ValueError:
        return True
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=UTC)
    return deadline.astimezone(UTC) <= datetime.now(UTC)
