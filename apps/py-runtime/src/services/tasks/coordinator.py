from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping

from services.tasks.errors import idempotency_key_required
from services.tasks.recovery import TaskRecoveryService
from services.tasks.task_runner import TaskRunner
from services.tasks.task_service import TaskService
from services.tasks.types import (
    CreateTaskCommand,
    JsonValue,
    RuntimeTaskRecord,
    TaskCommitDecision,
    TaskRecoveryPlan,
    TaskScope,
    TaskStatus,
)

log = logging.getLogger(__name__)


class TaskCoordinator:
    """为 HTTP 服务提供异步任务提交、读取、取消与恢复入口。"""

    def __init__(
        self,
        *,
        task_service: TaskService,
        task_runner: TaskRunner,
        recovery_service: TaskRecoveryService,
    ) -> None:
        self._task_service = task_service
        self._task_runner = task_runner
        self._recovery_service = recovery_service

    async def submit_system_task(
        self,
        *,
        task_type: str,
        payload: Mapping[str, JsonValue],
        idempotency_key: str,
        request_id: str,
        operation_id: str,
        timeout_seconds: int | None = None,
    ) -> RuntimeTaskRecord:
        return await self._submit_task(
            CreateTaskCommand(
                scope=TaskScope.SYSTEM,
                account_id=None,
                task_type=task_type,
                payload=payload,
                idempotency_key=idempotency_key,
                request_id=request_id,
                operation_id=operation_id,
                timeout_seconds=timeout_seconds,
            )
        )

    async def submit_account_task(
        self,
        account_id: str,
        *,
        task_type: str,
        payload: Mapping[str, JsonValue],
        idempotency_key: str,
        request_id: str,
        operation_id: str,
        timeout_seconds: int | None = None,
    ) -> RuntimeTaskRecord:
        return await self._submit_task(
            CreateTaskCommand(
                scope=TaskScope.ACCOUNT,
                account_id=account_id,
                task_type=task_type,
                payload=payload,
                idempotency_key=idempotency_key,
                request_id=request_id,
                operation_id=operation_id,
                timeout_seconds=timeout_seconds,
            )
        )

    async def get_system_task(self, task_id: str) -> RuntimeTaskRecord:
        return await asyncio.to_thread(
            self._task_service.get_system_task,
            task_id,
        )

    async def list_system_tasks(
        self,
        *,
        limit: int = 200,
    ) -> list[RuntimeTaskRecord]:
        return await asyncio.to_thread(
            self._task_service.list_system_tasks,
            limit=limit,
        )

    async def list_account_tasks(
        self,
        account_id: str,
        *,
        limit: int = 200,
    ) -> list[RuntimeTaskRecord]:
        return await asyncio.to_thread(
            self._task_service.list_account_tasks,
            account_id,
            limit=limit,
        )

    async def get_account_task(
        self,
        account_id: str,
        task_id: str,
    ) -> RuntimeTaskRecord:
        return await asyncio.to_thread(
            self._task_service.get_account_task,
            account_id,
            task_id,
        )

    async def cancel_system_task(
        self,
        task_id: str,
        *,
        idempotency_key: str,
    ) -> RuntimeTaskRecord:
        self._require_idempotency_key(idempotency_key)
        decision = (
            await self._task_runner.decide_commit_aware_cancellation(task_id)
        )
        if decision is TaskCommitDecision.COMMIT_WON:
            await self._task_runner.wait_for_completion(task_id)
            return await self.get_system_task(task_id)
        record = await asyncio.to_thread(
            self._task_service.cancel_system_task,
            task_id,
        )
        self._notify_cancellation(record)
        return record

    async def cancel_account_task(
        self,
        account_id: str,
        task_id: str,
        *,
        idempotency_key: str,
    ) -> RuntimeTaskRecord:
        self._require_idempotency_key(idempotency_key)
        decision = (
            await self._task_runner.decide_commit_aware_cancellation(task_id)
        )
        if decision is TaskCommitDecision.COMMIT_WON:
            await self._task_runner.wait_for_completion(task_id)
            return await self.get_account_task(account_id, task_id)
        record = await asyncio.to_thread(
            self._task_service.cancel_account_task,
            account_id,
            task_id,
        )
        self._notify_cancellation(record)
        return record

    async def retry_system_task(
        self,
        task_id: str,
        *,
        idempotency_key: str,
        request_id: str,
        operation_id: str,
    ) -> RuntimeTaskRecord:
        await self.get_system_task(task_id)
        return await self._retry_task(
            task_id,
            idempotency_key=idempotency_key,
            request_id=request_id,
            operation_id=operation_id,
        )

    async def retry_account_task(
        self,
        account_id: str,
        task_id: str,
        *,
        idempotency_key: str,
        request_id: str,
        operation_id: str,
    ) -> RuntimeTaskRecord:
        await self.get_account_task(account_id, task_id)
        return await self._retry_task(
            task_id,
            idempotency_key=idempotency_key,
            request_id=request_id,
            operation_id=operation_id,
        )

    async def recover(self) -> TaskRecoveryPlan:
        return await self._recovery_service.recover()

    async def shutdown(self) -> None:
        await self._task_runner.shutdown()

    async def cancel_other_account_tasks(
        self,
        account_id: str,
        *,
        excluded_task_id: str,
    ) -> tuple[str, ...]:
        records = await asyncio.to_thread(self._task_service.list_non_terminal)
        cancelled: list[str] = []
        for record in records:
            if record.account_id != account_id or record.id == excluded_task_id:
                continue
            try:
                result = await self.cancel_account_task(
                    account_id,
                    record.id,
                    idempotency_key=f"archive-cleanup:{excluded_task_id}:{record.id}",
                )
            except Exception:
                log.exception(
                    "账号归档时取消关联任务失败",
                    extra={
                        "account_id": account_id,
                        "task_id": record.id,
                        "archive_task_id": excluded_task_id,
                    },
                )
                raise
            if result.status in {TaskStatus.CANCELLING, TaskStatus.COMPLETED}:
                cancelled.append(result.id)
        return tuple(cancelled)

    async def _submit_task(
        self,
        command: CreateTaskCommand,
    ) -> RuntimeTaskRecord:
        self._require_idempotency_key(command.idempotency_key)
        record = await asyncio.to_thread(
            self._task_service.create_task,
            command,
        )
        self._schedule_if_queued(record)
        return record

    async def _retry_task(
        self,
        task_id: str,
        *,
        idempotency_key: str,
        request_id: str,
        operation_id: str,
    ) -> RuntimeTaskRecord:
        self._require_idempotency_key(idempotency_key)
        record = await asyncio.to_thread(
            self._task_service.retry_task,
            task_id,
            idempotency_key=idempotency_key,
            request_id=request_id,
            operation_id=operation_id,
        )
        self._schedule_if_queued(record)
        return record

    def _schedule_if_queued(self, record: RuntimeTaskRecord) -> None:
        if record.status is TaskStatus.QUEUED:
            self._task_runner.schedule(record.id)

    def _notify_cancellation(self, record: RuntimeTaskRecord) -> None:
        if record.status is TaskStatus.CANCELLING:
            self._task_runner.request_cancel(record.id)

    @staticmethod
    def _require_idempotency_key(idempotency_key: str) -> None:
        if not idempotency_key.strip():
            raise idempotency_key_required()
