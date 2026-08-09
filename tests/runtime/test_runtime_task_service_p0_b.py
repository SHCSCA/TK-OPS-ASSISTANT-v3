from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from domain.models.account import Account
from errors import DomainError, ErrorCode
from services.tasks.recovery import TaskRecoveryService
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
from services.tasks.events import TaskEvent
from services.tasks.task_service import TaskService
from tests.runtime.runtime_task_test_support import make_runtime_task_stack


async def _noop_handler(
    _context: TaskExecutionContext,
    _payload: Mapping[str, JsonValue],
) -> TaskExecutionResult:
    return TaskExecutionResult(result_ref="result://test")


class _RecordingScheduler:
    def __init__(self) -> None:
        self.task_ids: list[str] = []

    def schedule(self, task_id: str) -> None:
        self.task_ids.append(task_id)


class _FailingEventSink:
    def append(self, _session: Session, _event: TaskEvent) -> None:
        raise RuntimeError("模拟 outbox 写入失败")


def _command(
    *,
    idempotency_key: str,
    payload: Mapping[str, JsonValue] | None = None,
    scope: TaskScope = TaskScope.SYSTEM,
    account_id: str | None = None,
    retry_of_task_id: str | None = None,
    attempt: int = 1,
) -> CreateTaskCommand:
    return CreateTaskCommand(
        scope=scope,
        account_id=account_id,
        task_type="test.operation",
        payload=payload or {"resourceRef": "asset://owned/input"},
        idempotency_key=idempotency_key,
        request_id=f"req_{idempotency_key}",
        operation_id=f"op_{idempotency_key}",
        retry_of_task_id=retry_of_task_id,
        attempt=attempt,
    )


def test_task_creation_is_persistently_idempotent_and_detects_conflict(
    tmp_path: Path,
) -> None:
    stack = make_runtime_task_stack(
        tmp_path / "task-idempotency.db",
        handler=_noop_handler,
    )
    try:
        first = stack.task_service.create_task(
            _command(idempotency_key="idem_same")
        )
        replay = stack.task_service.create_task(
            _command(idempotency_key="idem_same")
        )

        assert replay.id == first.id
        assert replay.revision == first.revision
        assert first.idempotency_key_hash
        assert first.request_hash
        assert first.handler_version == 1
        with pytest.raises(DomainError) as caught:
            stack.task_service.create_task(
                _command(
                    idempotency_key="idem_same",
                    payload={"resourceRef": "asset://owned/other"},
                )
            )
        assert caught.value.error_code == ErrorCode.TASK_IDEMPOTENCY_CONFLICT.value
        with pytest.raises(DomainError) as attempt_conflict:
            stack.task_service.create_task(
                _command(
                    idempotency_key="idem_same",
                    retry_of_task_id="task-previous",
                    attempt=2,
                )
            )
        assert (
            attempt_conflict.value.error_code
            == ErrorCode.TASK_IDEMPOTENCY_CONFLICT.value
        )
    finally:
        stack.engine.dispose()


def test_single_active_task_is_enforced_inside_creation_transaction(
    tmp_path: Path,
) -> None:
    stack = make_runtime_task_stack(
        tmp_path / "task-single-active.db",
        handler=_noop_handler,
        single_active_per_scope=True,
        active_conflict_error_code=ErrorCode.SELF_CHECK_ALREADY_RUNNING.value,
    )
    try:
        first = stack.task_service.create_task(
            _command(idempotency_key="idem_first")
        )

        with pytest.raises(DomainError) as caught:
            stack.task_service.create_task(
                _command(idempotency_key="idem_second")
            )

        assert caught.value.error_code == ErrorCode.SELF_CHECK_ALREADY_RUNNING.value
        assert caught.value.meta["taskId"] == first.id
    finally:
        stack.engine.dispose()


def test_task_creation_only_replays_queued_task(tmp_path: Path) -> None:
    stack = make_runtime_task_stack(
        tmp_path / "task-terminal-replay.db",
        handler=_noop_handler,
        active_conflict_error_code=ErrorCode.SELF_CHECK_ALREADY_RUNNING.value,
    )
    try:
        created = stack.task_service.create_task(
            _command(idempotency_key="idem_terminal_replay")
        )
        stack.task_service.claim_running(created.id)
        stack.task_service.complete_success(
            created.id,
            result_ref="result://test",
        )

        with pytest.raises(DomainError) as caught:
            stack.task_service.create_task(
                _command(idempotency_key="idem_terminal_replay")
            )

        assert (
            caught.value.error_code
            == ErrorCode.SELF_CHECK_ALREADY_RUNNING.value
        )
        assert caught.value.meta["taskId"] == created.id
    finally:
        stack.engine.dispose()


def test_cancel_is_idempotent_and_terminal_kind_is_explicit(
    tmp_path: Path,
) -> None:
    stack = make_runtime_task_stack(
        tmp_path / "task-cancel.db",
        handler=_noop_handler,
    )
    try:
        created = stack.task_service.create_task(
            _command(idempotency_key="idem_cancel")
        )
        cancelling = stack.task_service.cancel_system_task(created.id)
        replay = stack.task_service.cancel_system_task(created.id)
        completed = stack.task_service.complete_cancelled(created.id)
        terminal_replay = stack.task_service.cancel_system_task(created.id)

        assert cancelling.status is TaskStatus.CANCELLING
        assert replay.revision == cancelling.revision
        assert completed.status is TaskStatus.COMPLETED
        assert completed.completion_kind is not None
        assert completed.completion_kind.value == "cancelled"
        assert terminal_replay.revision == completed.revision
        assert [
            event.event_type
            for event in stack.event_repository.list_unpublished(limit=10)
        ] == ["task.queued", "task.cancelling", "task.completed"]
    finally:
        stack.engine.dispose()


def test_account_task_cannot_be_read_through_system_or_other_account_scope(
    tmp_path: Path,
) -> None:
    stack = make_runtime_task_stack(
        tmp_path / "task-scope.db",
        handler=_noop_handler,
    )
    try:
        with stack.session_factory.begin() as session:
            session.add(
                Account(
                    id="acc_a",
                    name="测试账号",
                    platform="tiktok",
                    status="ready",
                    created_at="2026-07-26T00:00:00Z",
                    updated_at="2026-07-26T00:00:00Z",
                )
            )
        created = stack.task_service.create_task(
            _command(
                idempotency_key="idem_account",
                scope=TaskScope.ACCOUNT,
                account_id="acc_a",
            )
        )

        with pytest.raises(DomainError) as system_error:
            stack.task_service.get_system_task(created.id)
        with pytest.raises(DomainError) as account_error:
            stack.task_service.get_account_task("acc_b", created.id)

        assert system_error.value.error_code == ErrorCode.ACCOUNT_SCOPE_MISMATCH.value
        assert account_error.value.error_code == ErrorCode.ACCOUNT_SCOPE_MISMATCH.value
    finally:
        stack.engine.dispose()


def test_system_task_list_never_includes_account_tasks(tmp_path: Path) -> None:
    stack = make_runtime_task_stack(
        tmp_path / "task-system-list.db",
        handler=_noop_handler,
    )
    try:
        with stack.session_factory.begin() as session:
            session.add(
                Account(
                    id="acc_list",
                    name="列表隔离账号",
                    platform="tiktok",
                    status="ready",
                    created_at="2026-07-26T00:00:00Z",
                    updated_at="2026-07-26T00:00:00Z",
                )
            )
        system_task = stack.task_service.create_task(
            _command(idempotency_key="idem_system_list")
        )
        stack.task_service.create_task(
            _command(
                idempotency_key="idem_account_list",
                scope=TaskScope.ACCOUNT,
                account_id="acc_list",
            )
        )

        records = stack.task_service.list_system_tasks()

        assert [record.id for record in records] == [system_task.id]
        assert all(record.scope is TaskScope.SYSTEM for record in records)
        assert all(record.account_id is None for record in records)
    finally:
        stack.engine.dispose()


def test_outbox_failure_rolls_back_task_creation(tmp_path: Path) -> None:
    stack = make_runtime_task_stack(
        tmp_path / "task-outbox-rollback.db",
        handler=_noop_handler,
    )
    failing_service = TaskService(
        repository=stack.task_repository,
        handler_registry=stack.handler_registry,
        snapshot_policy=stack.snapshot_policy,
        event_sink=_FailingEventSink(),
        runtime_policy=stack.runtime_policy,
    )
    try:
        with pytest.raises(RuntimeError, match="模拟 outbox 写入失败"):
            failing_service.create_task(
                _command(idempotency_key="idem_rollback")
            )
        assert stack.task_repository.list_non_terminal() == []
    finally:
        stack.engine.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("resume_policy", "expected_status", "expected_bucket"),
    [
        (
            TaskResumePolicy.INTERRUPT,
            TaskStatus.FAILED,
            "interrupted_task_ids",
        ),
        (
            TaskResumePolicy.RESUME,
            TaskStatus.QUEUED,
            "resumable_task_ids",
        ),
    ],
)
async def test_restart_recovery_uses_handler_resume_policy(
    tmp_path: Path,
    resume_policy: TaskResumePolicy,
    expected_status: TaskStatus,
    expected_bucket: str,
) -> None:
    stack = make_runtime_task_stack(
        tmp_path / f"task-recovery-{resume_policy.value}.db",
        handler=_noop_handler,
        resume_policy=resume_policy,
    )
    scheduler = _RecordingScheduler()
    recovery = TaskRecoveryService(
        task_service=stack.task_service,
        handler_registry=stack.handler_registry,
        snapshot_policy=stack.snapshot_policy,
        scheduler=scheduler,
    )
    try:
        created = stack.task_service.create_task(
            _command(idempotency_key=f"idem_{resume_policy.value}")
        )
        stack.task_service.claim_running(created.id)

        plan = await recovery.recover()
        recovered = stack.task_service.get_task(created.id)

        assert recovered.status is expected_status
        assert created.id in cast(tuple[str, ...], getattr(plan, expected_bucket))
        if resume_policy is TaskResumePolicy.INTERRUPT:
            assert recovered.failure_kind is TaskFailureKind.RESTART_INTERRUPTED
            assert scheduler.task_ids == []
        else:
            assert recovered.attempt == 2
            assert scheduler.task_ids == [created.id]
            replay = stack.task_service.create_task(
                _command(idempotency_key=f"idem_{resume_policy.value}")
            )
            assert replay.id == created.id
            assert replay.attempt == 2
    finally:
        stack.engine.dispose()


@pytest.mark.asyncio
async def test_expired_queued_task_recovers_as_timed_out(tmp_path: Path) -> None:
    fixed_clock = lambda: datetime(2020, 1, 1, tzinfo=UTC)
    stack = make_runtime_task_stack(
        tmp_path / "task-recovery-timeout.db",
        handler=_noop_handler,
        clock=fixed_clock,
    )
    scheduler = _RecordingScheduler()
    recovery = TaskRecoveryService(
        task_service=stack.task_service,
        handler_registry=stack.handler_registry,
        snapshot_policy=stack.snapshot_policy,
        scheduler=scheduler,
    )
    try:
        created = stack.task_service.create_task(
            _command(idempotency_key="idem_timeout")
        )
        plan = await recovery.recover()
        recovered = stack.task_service.get_task(created.id)

        assert plan.timed_out_task_ids == (created.id,)
        assert recovered.status is TaskStatus.FAILED
        assert recovered.failure_kind is TaskFailureKind.TIMED_OUT
        assert recovered.error_code == ErrorCode.TASK_TIMEOUT.value
        assert scheduler.task_ids == []
    finally:
        stack.engine.dispose()


@pytest.mark.asyncio
async def test_recovery_rejects_explicit_handler_version_drift(
    tmp_path: Path,
) -> None:
    stack = make_runtime_task_stack(
        tmp_path / "task-recovery-version-drift.db",
        handler=_noop_handler,
    )
    scheduler = _RecordingScheduler()
    recovery = TaskRecoveryService(
        task_service=stack.task_service,
        handler_registry=stack.handler_registry,
        snapshot_policy=stack.snapshot_policy,
        scheduler=scheduler,
    )
    try:
        created = stack.task_service.create_task(
            _command(idempotency_key="idem_version_drift")
        )
        with stack.session_factory.begin() as session:
            session.execute(
                text(
                    """
                    UPDATE runtime_tasks
                    SET handler_version = 2
                    WHERE id = :task_id
                    """
                ),
                {"task_id": created.id},
            )

        plan = await recovery.recover()
        recovered = stack.task_service.get_task(created.id)

        assert plan.interrupted_task_ids == (created.id,)
        assert recovered.status is TaskStatus.FAILED
        assert recovered.failure_kind is TaskFailureKind.RESTART_INTERRUPTED
        assert recovered.error_code == ErrorCode.TASK_SNAPSHOT_INVALID.value
        assert scheduler.task_ids == []
    finally:
        stack.engine.dispose()
