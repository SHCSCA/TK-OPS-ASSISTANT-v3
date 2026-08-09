from __future__ import annotations

import asyncio
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, select
from sqlalchemy.orm import Session

import services.accounts.health_execution as health_execution_module
from domain.models.account import Account
from domain.models.account_connection import AccountConnection
from domain.models.device_workspace import (
    BrowserInstance,
    DeviceWorkspace,
    ExecutionBinding,
)
from domain.models.runtime_event import RuntimeEvent
from errors import DomainError, ErrorCode
from services.accounts.health_execution import AccountHealthExecutor
from services.accounts.runtime_policy import AccountRuntimePolicy
from services.accounts.task_handlers import build_account_health_handler
from services.accounts.unit_of_work import AccountTransaction
from services.browser_runtime import BrowserRuntimeHealth
from services.tasks.errors import TaskCancellationRequested
from services.tasks.types import (
    TaskCommitCoordinator,
    TaskCommitDecision,
)
from tests.runtime.p0c_account_integration_support import (
    account_revision,
    create_account,
    mutation_headers,
    seed_workspace_and_browser,
    session,
)


class _ProbeRuntime:
    def __init__(
        self,
        before_result: Callable[[], None] | None = None,
    ) -> None:
        self._before_result = before_result
        self.calls: list[tuple[int | None, int | None]] = []

    def health(
        self,
        *,
        process_id: int | None,
        debug_port: int | None,
    ) -> BrowserRuntimeHealth:
        self.calls.append((process_id, debug_port))
        if self._before_result is not None:
            self._before_result()
        return BrowserRuntimeHealth(
            alive=True,
            process_id=process_id,
            debug_port=debug_port,
        )


@dataclass
class _TaskContext:
    task_id: str = "task_health_gate"
    account_id: str | None = "account-health-gate"
    attempt: int = 1
    cancelled: bool = False
    progress: list[float] = field(default_factory=list)
    commit_coordinator: TaskCommitCoordinator = field(
        default_factory=TaskCommitCoordinator
    )

    async def report_progress(self, progress: float) -> None:
        self.raise_if_cancelled()
        self.progress.append(progress)

    def raise_if_cancelled(self) -> None:
        if self.cancelled:
            raise TaskCancellationRequested()

    def enable_commit_coordination(self) -> TaskCommitCoordinator:
        return self.commit_coordinator.enable()


class _BlockingExecutor:
    def __init__(self) -> None:
        self.started = threading.Event()
        self.release = threading.Event()
        self.finished = threading.Event()
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
        self.started.set()
        try:
            if not self.release.wait(timeout=2):
                raise RuntimeError("测试未释放健康检查线程")
            commit_coordinator.commit(self._commit)
            return 2
        finally:
            self.finished.set()

    def _commit(self) -> None:
        self.committed = True


class _CommitWindowExecutor:
    def __init__(self) -> None:
        self.commit_started = threading.Event()
        self.release_commit = threading.Event()
        self.finished = threading.Event()
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

        try:
            commit_coordinator.commit(commit)
            return 2
        finally:
            self.finished.set()


def test_probe_rejects_binding_swap_without_writing_old_result(
    licensed_runtime_client: TestClient,
    runtime_data_dir: Path,
) -> None:
    client = licensed_runtime_client
    account_id, _, browser_a = _prepare_health_account(
        client,
        runtime_data_dir,
        key="probe-binding-a",
    )
    workspace_b, browser_b = seed_workspace_and_browser(
        client,
        account_id=account_id,
        key="probe-binding-b",
        root=runtime_data_dir,
    )
    observed_at = datetime.now(UTC)
    binding_b_id = "binding_probe_b"
    with session(client) as database:
        browser = database.get(BrowserInstance, browser_b)
        active_binding = database.scalar(
            select(ExecutionBinding).where(
                ExecutionBinding.account_id == account_id,
                ExecutionBinding.status == "active",
            )
        )
        assert browser is not None
        assert active_binding is not None
        browser.status = "running"
        browser.process_id = 202
        browser.debug_port = 9333
        active_binding.status = "inactive"
        database.add(
            ExecutionBinding(
                id=binding_b_id,
                account_id=account_id,
                device_workspace_id=workspace_b,
                browser_instance_id=browser_b,
                status="active",
                source="health-consistency-test",
                metadata_json=None,
                created_at=observed_at,
                updated_at=observed_at,
            )
        )
        database.commit()

    before_revision = account_revision(client, account_id)

    def swap_binding() -> None:
        with session(client) as database:
            connection = database.scalar(
                select(AccountConnection).where(
                    AccountConnection.account_id == account_id
                )
            )
            assert connection is not None
            connection.active_execution_binding_id = binding_b_id
            database.commit()

    runtime = _ProbeRuntime(swap_binding)
    executor = _executor(client, runtime)

    with pytest.raises(DomainError) as exc_info:
        executor.run(
            account_id,
            checks=("connection",),
            restore=False,
            expected_revision=None,
            require_connection=True,
            commit_coordinator=_active_commit_coordinator(),
        )

    assert exc_info.value.error_code == ErrorCode.REVISION_CONFLICT.value
    assert runtime.calls == [(101, 9222)]
    with session(client) as database:
        connection = database.scalar(
            select(AccountConnection).where(
                AccountConnection.account_id == account_id
            )
        )
        assert connection is not None
        assert connection.active_execution_binding_id == binding_b_id
        assert connection.health_status == "unknown"
        assert connection.last_checked_at is None
        assert database.get(BrowserInstance, browser_a) is not None
        assert database.scalar(
            select(RuntimeEvent).where(
                RuntimeEvent.account_id == account_id,
                RuntimeEvent.event_type == "account.health.updated",
            )
        ) is None
    assert account_revision(client, account_id) == before_revision


def test_probe_rejects_changed_process_and_debug_port_evidence(
    licensed_runtime_client: TestClient,
    runtime_data_dir: Path,
) -> None:
    client = licensed_runtime_client
    account_id, _, browser_id = _prepare_health_account(
        client,
        runtime_data_dir,
        key="probe-runtime-evidence",
    )
    before_revision = account_revision(client, account_id)

    def replace_runtime_evidence() -> None:
        with session(client) as database:
            browser = database.get(BrowserInstance, browser_id)
            assert browser is not None
            browser.process_id = 303
            browser.debug_port = 9444
            database.commit()

    runtime = _ProbeRuntime(replace_runtime_evidence)
    executor = _executor(client, runtime)

    with pytest.raises(DomainError) as exc_info:
        executor.run(
            account_id,
            checks=("connection",),
            restore=False,
            expected_revision=None,
            require_connection=True,
            commit_coordinator=_active_commit_coordinator(),
        )

    assert exc_info.value.error_code == ErrorCode.REVISION_CONFLICT.value
    assert runtime.calls == [(101, 9222)]
    with session(client) as database:
        connection = database.scalar(
            select(AccountConnection).where(
                AccountConnection.account_id == account_id
            )
        )
        assert connection is not None
        assert connection.health_status == "unknown"
        assert connection.last_checked_at is None
    assert account_revision(client, account_id) == before_revision


def test_probe_rejects_changed_workspace_status_evidence(
    licensed_runtime_client: TestClient,
    runtime_data_dir: Path,
) -> None:
    client = licensed_runtime_client
    account_id, workspace_id, _ = _prepare_health_account(
        client,
        runtime_data_dir,
        key="probe-workspace-status",
    )
    before_revision = account_revision(client, account_id)

    def mark_workspace_offline() -> None:
        with session(client) as database:
            workspace = database.get(DeviceWorkspace, workspace_id)
            assert workspace is not None
            workspace.status = "offline"
            database.commit()

    runtime = _ProbeRuntime(mark_workspace_offline)
    with pytest.raises(DomainError) as exc_info:
        _executor(client, runtime).run(
            account_id,
            checks=("connection",),
            restore=False,
            expected_revision=None,
            require_connection=True,
            commit_coordinator=_active_commit_coordinator(),
        )

    assert exc_info.value.error_code == ErrorCode.REVISION_CONFLICT.value
    assert runtime.calls == [(101, 9222)]
    with session(client) as database:
        connection = database.scalar(
            select(AccountConnection).where(
                AccountConnection.account_id == account_id
            )
        )
        workspace = database.get(DeviceWorkspace, workspace_id)
        assert connection is not None
        assert workspace is not None
        assert workspace.status == "offline"
        assert connection.health_status == "unknown"
        assert connection.last_checked_at is None
    assert account_revision(client, account_id) == before_revision


def test_connection_event_uses_updated_account_aggregate_revision(
    licensed_runtime_client: TestClient,
    runtime_data_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = licensed_runtime_client
    account_id, _, _ = _prepare_health_account(
        client,
        runtime_data_dir,
        key="probe-event-revision",
    )
    observed_events: list[tuple[str, int, int]] = []
    original_append = health_execution_module.append_account_event

    def record_event(
        transaction: AccountTransaction,
        **kwargs: Any,
    ) -> None:
        account = transaction.session.get(Account, account_id)
        assert account is not None
        observed_events.append(
            (
                str(kwargs["event_type"]),
                int(kwargs["revision"]),
                int(account.revision),
            )
        )
        original_append(transaction, **kwargs)

    monkeypatch.setattr(
        health_execution_module,
        "append_account_event",
        record_event,
    )
    revision = _executor(client, _ProbeRuntime()).run(
        account_id,
        checks=("connection",),
        restore=False,
        expected_revision=None,
        require_connection=True,
        commit_coordinator=_active_commit_coordinator(),
    )

    assert observed_events == [
        ("account.connection.updated", revision, revision),
        ("account.health.updated", revision, revision),
    ]
    with session(client) as database:
        connection = database.scalar(
            select(AccountConnection).where(
                AccountConnection.account_id == account_id
            )
        )
        event = database.scalar(
            select(RuntimeEvent).where(
                RuntimeEvent.account_id == account_id,
                RuntimeEvent.event_type == "account.connection.updated",
                RuntimeEvent.topic == f"account:{account_id}:connection",
            )
        )
        assert connection is not None
        assert event is not None
        assert event.revision == revision
        assert event.revision != int(connection.revision)


def test_termination_before_business_commit_rolls_back(
    licensed_runtime_client: TestClient,
    runtime_data_dir: Path,
) -> None:
    client = licensed_runtime_client
    account_id, _, _ = _prepare_health_account(
        client,
        runtime_data_dir,
        key="probe-before-commit-gate",
    )
    before_revision = account_revision(client, account_id)
    commit_coordinator = _active_commit_coordinator()
    assert (
        commit_coordinator.request_termination()
        is TaskCommitDecision.TERMINATION_WON
    )

    with pytest.raises(TaskCancellationRequested):
        _executor(client, _ProbeRuntime()).run(
            account_id,
            checks=("connection",),
            restore=False,
            expected_revision=None,
            require_connection=True,
            commit_coordinator=commit_coordinator,
        )

    with session(client) as database:
        connection = database.scalar(
            select(AccountConnection).where(
                AccountConnection.account_id == account_id
            )
        )
        health_event = database.scalar(
            select(RuntimeEvent).where(
                RuntimeEvent.account_id == account_id,
                RuntimeEvent.event_type == "account.health.updated",
            )
        )
        connection_event = database.scalar(
            select(RuntimeEvent).where(
                RuntimeEvent.account_id == account_id,
                RuntimeEvent.event_type == "account.connection.updated",
                RuntimeEvent.topic == f"account:{account_id}:connection",
            )
        )
        assert connection is not None
        assert connection.health_status == "unknown"
        assert connection.last_checked_at is None
        assert health_event is None
        assert connection_event is None
    assert account_revision(client, account_id) == before_revision


def test_commit_wins_during_before_commit_to_commit_window(
    licensed_runtime_client: TestClient,
    runtime_data_dir: Path,
) -> None:
    client = licensed_runtime_client
    account_id, _, _ = _prepare_health_account(
        client,
        runtime_data_dir,
        key="probe-commit-window",
    )
    before_revision = account_revision(client, account_id)
    commit_coordinator = _active_commit_coordinator()
    before_commit = threading.Event()
    release_commit = threading.Event()
    termination_finished = threading.Event()
    worker_errors: list[BaseException] = []
    result: list[int] = []
    decision: list[TaskCommitDecision] = []

    def pause_before_commit(_session: Session) -> None:
        before_commit.set()
        if not release_commit.wait(timeout=2):
            raise RuntimeError("测试未释放数据库提交")

    def execute_health() -> None:
        try:
            result.append(
                _executor(client, _ProbeRuntime()).run(
                    account_id,
                    checks=("connection",),
                    restore=False,
                    expected_revision=None,
                    require_connection=True,
                    commit_coordinator=commit_coordinator,
                )
            )
        except BaseException as exc:
            worker_errors.append(exc)

    def request_termination() -> None:
        decision.append(commit_coordinator.request_termination())
        termination_finished.set()

    event.listen(Session, "before_commit", pause_before_commit)
    worker = threading.Thread(target=execute_health)
    termination = threading.Thread(target=request_termination)
    try:
        worker.start()
        assert before_commit.wait(timeout=1)
        termination.start()
        assert not termination_finished.wait(timeout=0.05)
        release_commit.set()
        worker.join(timeout=2)
        termination.join(timeout=2)
    finally:
        release_commit.set()
        event.remove(Session, "before_commit", pause_before_commit)

    assert not worker.is_alive()
    assert not termination.is_alive()
    assert worker_errors == []
    assert decision == [TaskCommitDecision.COMMIT_WON]
    assert result == [before_revision + 1]
    assert account_revision(client, account_id) == before_revision + 1


@pytest.mark.asyncio
async def test_cancelled_handler_closes_commit_gate_before_thread_resumes() -> None:
    executor = _BlockingExecutor()
    context = _TaskContext()
    handler = build_account_health_handler(
        cast(AccountHealthExecutor, executor)
    )
    task = asyncio.create_task(
        handler(context, {"checks": ["connection"]})
    )
    try:
        assert await asyncio.to_thread(executor.started.wait, 1)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    finally:
        executor.release.set()
    assert await asyncio.to_thread(executor.finished.wait, 1)
    assert executor.committed is False
    assert context.progress == [0.1]


@pytest.mark.asyncio
async def test_timed_out_handler_closes_commit_gate_before_thread_resumes() -> None:
    executor = _BlockingExecutor()
    context = _TaskContext()
    handler = build_account_health_handler(
        cast(AccountHealthExecutor, executor)
    )
    task = asyncio.create_task(
        handler(context, {"checks": ["connection"]})
    )
    try:
        assert await asyncio.to_thread(executor.started.wait, 1)
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(task, timeout=0.01)
    finally:
        executor.release.set()
    assert await asyncio.to_thread(executor.finished.wait, 1)
    assert executor.committed is False
    assert context.progress == [0.1]


@pytest.mark.asyncio
async def test_handler_commit_wins_cancellation_during_commit_window() -> None:
    executor = _CommitWindowExecutor()
    context = _TaskContext()
    handler = build_account_health_handler(
        cast(AccountHealthExecutor, executor)
    )
    task = asyncio.create_task(
        handler(context, {"checks": ["connection"]})
    )
    try:
        assert await asyncio.to_thread(executor.commit_started.wait, 1)
        task.cancel()
        await asyncio.sleep(0)
        assert not task.done()
        executor.release_commit.set()
        result = await task
    finally:
        executor.release_commit.set()

    assert result.result_ref.endswith("revision=2")
    assert await asyncio.to_thread(executor.finished.wait, 1)
    assert executor.committed is True


@pytest.mark.asyncio
async def test_handler_commit_wins_timeout_during_commit_window() -> None:
    executor = _CommitWindowExecutor()
    context = _TaskContext()
    handler = build_account_health_handler(
        cast(AccountHealthExecutor, executor)
    )
    task = asyncio.create_task(
        handler(context, {"checks": ["connection"]})
    )

    async def release_after_timeout() -> None:
        await asyncio.sleep(0.03)
        executor.release_commit.set()

    release = asyncio.create_task(release_after_timeout())
    try:
        assert await asyncio.to_thread(executor.commit_started.wait, 1)
        result = await asyncio.wait_for(task, timeout=0.01)
        await release
    finally:
        executor.release_commit.set()

    assert result.result_ref.endswith("revision=2")
    assert await asyncio.to_thread(executor.finished.wait, 1)
    assert executor.committed is True


def _prepare_health_account(
    client: TestClient,
    runtime_data_dir: Path,
    *,
    key: str,
) -> tuple[str, str, str]:
    account_id, revision = create_account(
        client,
        name=f"健康一致性 {key}",
        idempotency_key=f"idem_{key}_account",
    )
    workspace_id, browser_id = seed_workspace_and_browser(
        client,
        account_id=account_id,
        key=key,
        root=runtime_data_dir,
    )
    observed_at = datetime.now(UTC)
    with session(client) as database:
        database.add(
            ExecutionBinding(
                id=f"binding_{key}",
                account_id=account_id,
                device_workspace_id=workspace_id,
                browser_instance_id=browser_id,
                status="active",
                source="health-consistency-test",
                metadata_json=None,
                created_at=observed_at,
                updated_at=observed_at,
            )
        )
        database.commit()
    bound = client.put(
        f"/api/v1/accounts/{account_id}/connection/binding",
        headers=mutation_headers(
            revision=revision,
            idempotency_key=f"idem_{key}_binding",
        ),
        json={
            "environmentId": f"binding_{key}",
            "eligibilityRevision": 5,
        },
    )
    assert bound.status_code == 200, bound.text
    with session(client) as database:
        browser = database.get(BrowserInstance, browser_id)
        connection = database.scalar(
            select(AccountConnection).where(
                AccountConnection.account_id == account_id
            )
        )
        assert browser is not None
        assert connection is not None
        browser.status = "running"
        browser.process_id = 101
        browser.debug_port = 9222
        connection.auth_status = "valid"
        connection.health_status = "unknown"
        connection.last_checked_at = None
        connection.error_code = None
        connection.revision = 20
        database.commit()
    return account_id, workspace_id, browser_id


def _executor(
    client: TestClient,
    browser_runtime: _ProbeRuntime,
) -> AccountHealthExecutor:
    return AccountHealthExecutor(
        client.app.state.account_unit_of_work,
        read_model=client.app.state.account_read_model,
        browser_runtime=browser_runtime,
        policy_provider=lambda: AccountRuntimePolicy(
            required_capabilities=(),
            mutation_idempotency_ttl_seconds=604_800,
            config_revision=1,
        ),
    )


def _active_commit_coordinator() -> TaskCommitCoordinator:
    return TaskCommitCoordinator().enable()
