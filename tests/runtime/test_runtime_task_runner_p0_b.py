from __future__ import annotations

import asyncio
import threading
from collections.abc import Mapping
from pathlib import Path
from typing import cast

import pytest
from sqlalchemy import text

from domain.models.account import Account
from errors import ErrorCode
from services.accounts.health_execution import AccountHealthExecutor
from services.accounts.task_handlers import build_account_health_handler
from services.tasks.coordinator import TaskCoordinator
from services.tasks.recovery import TaskRecoveryService
from services.tasks.task_runner import TaskRunner
from services.tasks.types import (
    CreateTaskCommand,
    JsonValue,
    TaskCommitCoordinator,
    TaskExecutionContext,
    TaskExecutionResult,
    TaskScope,
    TaskStatus,
)
from tests.runtime.runtime_task_test_support import (
    RuntimeTaskTestStack,
    make_runtime_task_stack,
)


async def _wait_for_terminal(
    coordinator: TaskCoordinator,
    task_id: str,
) -> None:
    async with asyncio.timeout(2):
        while True:
            record = await coordinator.get_system_task(task_id)
            if record.is_terminal:
                return
            await asyncio.sleep(0.01)


def _build_coordinator(stack: RuntimeTaskTestStack) -> TaskCoordinator:
    runner = TaskRunner(
        task_service=stack.task_service,
        handler_registry=stack.handler_registry,
        snapshot_policy=stack.snapshot_policy,
        runtime_policy=stack.runtime_policy,
    )
    recovery = TaskRecoveryService(
        task_service=stack.task_service,
        handler_registry=stack.handler_registry,
        snapshot_policy=stack.snapshot_policy,
        scheduler=runner,
    )
    return TaskCoordinator(
        task_service=stack.task_service,
        task_runner=runner,
        recovery_service=recovery,
    )


@pytest.mark.asyncio
async def test_runner_persists_progress_and_success_result(tmp_path: Path) -> None:
    async def handler(
        context: TaskExecutionContext,
        _payload: Mapping[str, JsonValue],
    ) -> TaskExecutionResult:
        await context.report_progress(0.5)
        return TaskExecutionResult(result_ref="result://task/success")

    stack = make_runtime_task_stack(
        tmp_path / "task-runner-success.db",
        handler=handler,
    )
    coordinator = _build_coordinator(stack)
    try:
        accepted = await coordinator.submit_system_task(
            task_type="test.operation",
            payload={"resourceRef": "asset://owned/input"},
            idempotency_key="idem_runner_success",
            request_id="req_runner_success",
            operation_id="op_runner_success",
        )
        await _wait_for_terminal(coordinator, accepted.id)
        completed = await coordinator.get_system_task(accepted.id)

        assert completed.status is TaskStatus.COMPLETED
        assert completed.completion_kind is not None
        assert completed.completion_kind.value == "succeeded"
        assert completed.progress == 1
        assert completed.result_ref == "result://task/success"
        assert [
            event.event_type
            for event in stack.event_repository.list_unpublished(limit=10)
        ] == [
            "task.queued",
            "task.started",
            "task.progress",
            "task.completed",
        ]
    finally:
        await coordinator.shutdown()
        stack.engine.dispose()


@pytest.mark.asyncio
async def test_runner_rejects_explicit_snapshot_drift(tmp_path: Path) -> None:
    async def handler(
        _context: TaskExecutionContext,
        _payload: Mapping[str, JsonValue],
    ) -> None:
        return None

    stack = make_runtime_task_stack(
        tmp_path / "task-runner-snapshot-drift.db",
        handler=handler,
    )
    runner = TaskRunner(
        task_service=stack.task_service,
        handler_registry=stack.handler_registry,
        snapshot_policy=stack.snapshot_policy,
        runtime_policy=stack.runtime_policy,
    )
    try:
        created = stack.task_service.create_task(
            CreateTaskCommand(
                scope=TaskScope.SYSTEM,
                account_id=None,
                task_type="test.operation",
                payload={"resourceRef": "asset://owned/input"},
                idempotency_key="idem_runner_snapshot_drift",
                request_id="req_runner_snapshot_drift",
                operation_id="op_runner_snapshot_drift",
            )
        )
        with stack.session_factory.begin() as session:
            session.execute(
                text(
                    """
                    UPDATE runtime_tasks
                    SET request_hash = :request_hash
                    WHERE id = :task_id
                    """
                ),
                {
                    "task_id": created.id,
                    "request_hash": "c" * 64,
                },
            )

        runner.schedule(created.id)
        async with asyncio.timeout(2):
            while True:
                failed = stack.task_service.get_task(created.id)
                if failed.is_terminal:
                    break
                await asyncio.sleep(0.01)

        assert failed.status is TaskStatus.FAILED
        assert failed.error_code == ErrorCode.TASK_SNAPSHOT_INVALID.value
    finally:
        await runner.shutdown()
        stack.engine.dispose()


@pytest.mark.asyncio
async def test_runner_cancel_persists_completed_cancelled(tmp_path: Path) -> None:
    started = asyncio.Event()

    async def handler(
        _context: TaskExecutionContext,
        _payload: Mapping[str, JsonValue],
    ) -> None:
        started.set()
        await asyncio.Future()

    stack = make_runtime_task_stack(
        tmp_path / "task-runner-cancel.db",
        handler=handler,
    )
    coordinator = _build_coordinator(stack)
    try:
        accepted = await coordinator.submit_system_task(
            task_type="test.operation",
            payload={"resourceRef": "asset://owned/input"},
            idempotency_key="idem_runner_cancel",
            request_id="req_runner_cancel",
            operation_id="op_runner_cancel",
        )
        await asyncio.wait_for(started.wait(), timeout=2)
        cancelling = await coordinator.cancel_system_task(
            accepted.id,
            idempotency_key="idem_cancel_request",
        )
        await _wait_for_terminal(coordinator, accepted.id)
        completed = await coordinator.get_system_task(accepted.id)

        assert cancelling.status is TaskStatus.CANCELLING
        assert completed.status is TaskStatus.COMPLETED
        assert completed.completion_kind is not None
        assert completed.completion_kind.value == "cancelled"
    finally:
        await coordinator.shutdown()
        stack.engine.dispose()


@pytest.mark.asyncio
async def test_commit_aware_cancel_returns_succeeded_when_commit_wins(
    tmp_path: Path,
) -> None:
    executor = _CommitWindowHealthExecutor()
    handler = build_account_health_handler(
        cast(AccountHealthExecutor, executor)
    )
    stack = make_runtime_task_stack(
        tmp_path / "task-runner-commit-wins.db",
        handler=handler,
        task_type="account.health_check",
        allowed_fields=frozenset({"checks"}),
    )
    coordinator = _build_coordinator(stack)
    try:
        with stack.session_factory.begin() as session:
            session.add(
                Account(
                    id="acc_commit_wins",
                    name="提交裁决测试账号",
                    platform="tiktok",
                    status="ready",
                    revision=1,
                    created_at="2026-07-26T00:00:00Z",
                    updated_at="2026-07-26T00:00:00Z",
                )
            )
        accepted = await coordinator.submit_account_task(
            "acc_commit_wins",
            task_type="account.health_check",
            payload={"checks": ["connection"]},
            idempotency_key="idem_commit_wins",
            request_id="req_commit_wins",
            operation_id="op_commit_wins",
        )
        assert await asyncio.to_thread(executor.commit_started.wait, 1)

        cancellation = asyncio.create_task(
            coordinator.cancel_account_task(
                "acc_commit_wins",
                accepted.id,
                idempotency_key="idem_cancel_after_commit_started",
            )
        )
        await asyncio.sleep(0)
        assert not cancellation.done()
        executor.release_commit.set()
        cancel_response = await cancellation
        completed = await coordinator.get_account_task(
            "acc_commit_wins",
            accepted.id,
        )

        assert executor.committed is True
        assert cancel_response.status is TaskStatus.COMPLETED
        assert cancel_response.completion_kind is not None
        assert cancel_response.completion_kind.value == "succeeded"
        assert completed.status is TaskStatus.COMPLETED
        assert completed.completion_kind is not None
        assert completed.completion_kind.value == "succeeded"
    finally:
        executor.release_commit.set()
        await coordinator.shutdown()
        stack.engine.dispose()


@pytest.mark.asyncio
async def test_runner_requires_explicit_restart_after_shutdown(
    tmp_path: Path,
) -> None:
    async def handler(
        _context: TaskExecutionContext,
        _payload: Mapping[str, JsonValue],
    ) -> TaskExecutionResult:
        return TaskExecutionResult(result_ref="result://task/restarted")

    stack = make_runtime_task_stack(
        tmp_path / "task-runner-restart.db",
        handler=handler,
    )
    runner = TaskRunner(
        task_service=stack.task_service,
        handler_registry=stack.handler_registry,
        snapshot_policy=stack.snapshot_policy,
        runtime_policy=stack.runtime_policy,
    )
    recovery = TaskRecoveryService(
        task_service=stack.task_service,
        handler_registry=stack.handler_registry,
        snapshot_policy=stack.snapshot_policy,
        scheduler=runner,
    )
    coordinator = TaskCoordinator(
        task_service=stack.task_service,
        task_runner=runner,
        recovery_service=recovery,
    )
    runner.start()
    try:
        first = await coordinator.submit_system_task(
            task_type="test.operation",
            payload={"resourceRef": "asset://owned/first"},
            idempotency_key="idem_runner_first_lifecycle",
            request_id="req_runner_first_lifecycle",
            operation_id="op_runner_first_lifecycle",
        )
        await _wait_for_terminal(coordinator, first.id)
        await coordinator.shutdown()

        with pytest.raises(RuntimeError, match="显式重新启动"):
            runner.schedule(first.id)

        runner.start()
        second = await coordinator.submit_system_task(
            task_type="test.operation",
            payload={"resourceRef": "asset://owned/second"},
            idempotency_key="idem_runner_second_lifecycle",
            request_id="req_runner_second_lifecycle",
            operation_id="op_runner_second_lifecycle",
        )
        await _wait_for_terminal(coordinator, second.id)
        completed = await coordinator.get_system_task(second.id)

        assert completed.status is TaskStatus.COMPLETED
        assert completed.result_ref == "result://task/restarted"
    finally:
        await coordinator.shutdown()
        stack.engine.dispose()


@pytest.mark.asyncio
async def test_runner_shutdown_timeout_preserves_task_for_recovery(
    tmp_path: Path,
) -> None:
    started = asyncio.Event()
    release = asyncio.Event()

    async def handler(
        _context: TaskExecutionContext,
        _payload: Mapping[str, JsonValue],
    ) -> None:
        started.set()
        try:
            await asyncio.Future()
        except asyncio.CancelledError:
            await release.wait()
            raise

    stack = make_runtime_task_stack(
        tmp_path / "task-runner-bounded-shutdown.db",
        handler=handler,
    )
    runner = TaskRunner(
        task_service=stack.task_service,
        handler_registry=stack.handler_registry,
        snapshot_policy=stack.snapshot_policy,
        runtime_policy=stack.runtime_policy,
        shutdown_grace_seconds=0.01,
    )
    created = stack.task_service.create_task(
        CreateTaskCommand(
            scope=TaskScope.SYSTEM,
            account_id=None,
            task_type="test.operation",
            payload={"resourceRef": "asset://owned/shutdown"},
            idempotency_key="idem_runner_bounded_shutdown",
            request_id="req_runner_bounded_shutdown",
            operation_id="op_runner_bounded_shutdown",
        )
    )
    runner.schedule(created.id)
    try:
        await asyncio.wait_for(started.wait(), timeout=2)
        before = asyncio.get_running_loop().time()

        await runner.shutdown(timeout_seconds=0.01)

        elapsed = asyncio.get_running_loop().time() - before
        persisted = stack.task_service.get_task(created.id)
        assert elapsed < 0.2
        assert runner.is_scheduled(created.id)
        assert persisted.status is TaskStatus.RUNNING
        assert not persisted.is_terminal
    finally:
        release.set()
        async with asyncio.timeout(2):
            while runner.is_scheduled(created.id):
                await asyncio.sleep(0.01)
        await runner.shutdown(timeout_seconds=0.01)
        stack.engine.dispose()


class _CommitWindowHealthExecutor:
    def __init__(self) -> None:
        self.commit_started = threading.Event()
        self.release_commit = threading.Event()
        self.committed = False

    def run(
        self,
        _account_id: str,
        *,
        checks: tuple[str, ...],
        restore: bool,
        expected_revision: int | None,
        require_connection: bool,
        commit_coordinator: TaskCommitCoordinator,
    ) -> int:
        assert checks == ("connection",)
        assert restore is False
        assert expected_revision is None
        assert require_connection is False

        def commit() -> None:
            self.commit_started.set()
            if not self.release_commit.wait(timeout=2):
                raise RuntimeError("测试未释放业务提交")
            self.committed = True

        commit_coordinator.commit(commit)
        return 2
