from __future__ import annotations

import asyncio
from collections.abc import Mapping
from pathlib import Path

import pytest

from errors import ErrorCode
from services.tasks.recovery import TaskRecoveryService
from services.tasks.task_runner import TaskRunner
from services.tasks.types import (
    CreateTaskCommand,
    JsonValue,
    TaskExecutionContext,
    TaskExecutionResult,
    TaskFailureKind,
    TaskResumePolicy,
    TaskScope,
    TaskStatus,
)
from tests.runtime.runtime_task_test_support import make_runtime_task_stack


async def _success_handler(
    _context: TaskExecutionContext,
    _payload: Mapping[str, JsonValue],
) -> TaskExecutionResult:
    return TaskExecutionResult(result_ref="result://p0-g/recovered")


class _RecordingScheduler:
    def __init__(self) -> None:
        self.task_ids: list[str] = []

    def schedule(self, task_id: str) -> None:
        self.task_ids.append(task_id)


def _command(key: str) -> CreateTaskCommand:
    return CreateTaskCommand(
        scope=TaskScope.SYSTEM,
        account_id=None,
        task_type="test.operation",
        payload={"resourceRef": f"asset://owned/{key}"},
        idempotency_key=f"idem_{key}",
        request_id=f"req_{key}",
        operation_id=f"op_{key}",
    )


def test_all_task_terminal_outcomes_are_explicit(tmp_path: Path) -> None:
    stack = make_runtime_task_stack(
        tmp_path / "p0-g-terminal-outcomes.db",
        handler=_success_handler,
    )
    try:
        success = stack.task_service.create_task(_command("success"))
        stack.task_service.claim_running(success.id)
        succeeded = stack.task_service.complete_success(
            success.id,
            result_ref="result://success",
        )

        cancellation = stack.task_service.create_task(_command("cancelled"))
        stack.task_service.cancel_system_task(cancellation.id)
        cancelled = stack.task_service.complete_cancelled(cancellation.id)

        failures = []
        for suffix, kind, code in (
            ("error", TaskFailureKind.ERROR, ErrorCode.INTERNAL_ERROR.value),
            ("timeout", TaskFailureKind.TIMED_OUT, ErrorCode.TASK_TIMEOUT.value),
            (
                "restart",
                TaskFailureKind.RESTART_INTERRUPTED,
                ErrorCode.TASK_STATE_CONFLICT.value,
            ),
        ):
            created = stack.task_service.create_task(_command(suffix))
            stack.task_service.claim_running(created.id)
            failures.append(
                stack.task_service.fail(
                    created.id,
                    failure_kind=kind,
                    error_code=code,
                )
            )

        assert succeeded.status is TaskStatus.COMPLETED
        assert succeeded.completion_kind is not None
        assert succeeded.completion_kind.value == "succeeded"
        assert cancelled.status is TaskStatus.COMPLETED
        assert cancelled.completion_kind is not None
        assert cancelled.completion_kind.value == "cancelled"
        assert [item.failure_kind for item in failures] == [
            TaskFailureKind.ERROR,
            TaskFailureKind.TIMED_OUT,
            TaskFailureKind.RESTART_INTERRUPTED,
        ]
    finally:
        stack.engine.dispose()


@pytest.mark.asyncio
async def test_restart_resumes_task_and_writes_one_terminal_event(
    tmp_path: Path,
) -> None:
    stack = make_runtime_task_stack(
        tmp_path / "p0-g-resume.db",
        handler=_success_handler,
        resume_policy=TaskResumePolicy.RESUME,
    )
    scheduler = _RecordingScheduler()
    recovery = TaskRecoveryService(
        task_service=stack.task_service,
        handler_registry=stack.handler_registry,
        snapshot_policy=stack.snapshot_policy,
        scheduler=scheduler,
    )
    runner = TaskRunner(
        task_service=stack.task_service,
        handler_registry=stack.handler_registry,
        snapshot_policy=stack.snapshot_policy,
        runtime_policy=stack.runtime_policy,
    )
    try:
        created = stack.task_service.create_task(_command("resume"))
        stack.task_service.claim_running(created.id)

        plan = await recovery.prepare_recovery()
        assert plan.resumable_task_ids == (created.id,)
        recovered = stack.task_service.get_task(created.id)
        assert recovered.status is TaskStatus.QUEUED
        assert recovered.attempt == 2

        recovery.schedule_recovery(plan)
        for task_id in scheduler.task_ids:
            runner.schedule(task_id)
        async with asyncio.timeout(2):
            while not stack.task_service.get_task(created.id).is_terminal:
                await asyncio.sleep(0.01)

        completed = stack.task_service.get_task(created.id)
        terminal_events = [
            item
            for item in stack.event_repository.list_unpublished(limit=50)
            if item.event_type in {"task.completed", "task.failed"}
        ]
        assert completed.status is TaskStatus.COMPLETED
        assert completed.result_ref == "result://p0-g/recovered"
        assert len(terminal_events) == 1
    finally:
        await runner.shutdown()
        stack.engine.dispose()
