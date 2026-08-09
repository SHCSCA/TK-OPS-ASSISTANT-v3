from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.secret_store import FileSecretStore
from domain.models import Base
from domain.models.account import Account
from domain.models.account_connection import AccountConnection
from domain.models.device_workspace import (
    BrowserInstance,
    DeviceWorkspace,
    ExecutionBinding,
)
from errors import DomainError, ErrorCode
from persistence.engine import create_runtime_engine
from repositories.account_login_session_repository import (
    AccountLoginSessionRepository,
)
from repositories.execution_environment_v1_repository import (
    ExecutionEnvironmentV1Repository,
)
from services.accounts.login_sessions import (
    PREPARE_TASK_TYPE,
    PROBE_TASK_TYPE,
    AccountLoginSessionService,
    register_login_session_task_handlers,
)
from services.accounts.tiktok_session_probe import TikTokSessionProbeResult
from services.tasks.handler_registry import TaskHandlerRegistry


def test_supervised_login_opens_visible_browser_and_persists_minimal_proof(
    tmp_path: Path,
) -> None:
    session_factory = _database(tmp_path)
    repository = AccountLoginSessionRepository(session_factory)
    coordinator = FakeCoordinator()
    service = AccountLoginSessionService(
        repository=repository,
        environment_repository=ExecutionEnvironmentV1Repository(session_factory),
        task_coordinator=coordinator,  # type: ignore[arg-type]
        login_timeout_seconds=lambda: 600,
        probe_timeout_seconds=lambda: 20,
    )
    browser = FakeBrowserRuntime()
    probe = FakeProbe(identity="efficiency.lab")
    secrets = FileSecretStore(tmp_path / "secrets.json")
    registry = TaskHandlerRegistry()
    register_login_session_task_handlers(
        registry,
        repository=repository,
        browser_runtime=browser,  # type: ignore[arg-type]
        probe=probe,  # type: ignore[arg-type]
        secret_store=secrets,
        probe_timeout_seconds=lambda: 20,
    )

    accepted = asyncio.run(
        service.create(
            "account-a",
            environment_id="environment-a",
            idempotency_key="login-create-a",
            request_id="request-a",
            operation_id="operation-a",
        )
    )
    asyncio.run(
        registry.require(PREPARE_TASK_TYPE).handler(
            FakeTaskContext("prepare-task", "account-a"),
            {"loginSessionId": accepted.sessionId},
        )
    )
    waiting = service.get("account-a", accepted.sessionId)

    assert waiting.state == "waiting_user"
    assert browser.navigations == [(9222, "https://www.tiktok.com/login")]
    probing = asyncio.run(
        service.probe(
            "account-a",
            accepted.sessionId,
            expected_revision=waiting.revision,
            idempotency_key="login-probe-a",
            request_id="request-probe",
            operation_id="operation-probe",
        )
    )
    asyncio.run(
        registry.require(PROBE_TASK_TYPE).handler(
            FakeTaskContext("probe-task", "account-a"),
            {"loginSessionId": probing.sessionId},
        )
    )

    completed = service.get("account-a", accepted.sessionId)
    assert completed.state == "completed"
    assert completed.detectedIdentity == "efficiency.lab"
    proof = secrets.get("account-session:account-a")
    assert proof is not None
    assert json.loads(proof) == {
        "schemaVersion": 1,
        "accountId": "account-a",
        "executionBindingId": "environment-a",
        "browserInstanceId": "browser-a",
        "identity": "efficiency.lab",
        "probedAt": json.loads(proof)["probedAt"],
    }
    assert "cookie" not in proof.lower()
    assert str(tmp_path) not in proof
    with session_factory() as database:
        connection = database.scalar(
            select(AccountConnection).where(
                AccountConnection.account_id == "account-a"
            )
        )
        assert connection is not None
        assert connection.auth_status == "valid"
        assert connection.health_status == "ready"


def test_login_session_is_account_scoped_and_identity_mismatch_stays_required(
    tmp_path: Path,
) -> None:
    session_factory = _database(tmp_path)
    repository = AccountLoginSessionRepository(session_factory)
    aggregate = repository.ensure(
        account_id="account-a",
        idempotency_key="login-scope-a",
        timeout_seconds=600,
    )

    assert repository.get_owned("account-b", aggregate.login_session.id) is None
    repository.mark_waiting(
        account_id="account-a",
        session_id=aggregate.login_session.id,
    )
    repository.begin_probe(
        account_id="account-a",
        session_id=aggregate.login_session.id,
    )
    repository.mark_probe_failed(
        account_id="account-a",
        session_id=aggregate.login_session.id,
        error_code="ACCOUNT_PLATFORM_IDENTITY_MISMATCH",
        error_log_id="log-mismatch",
        retryable=True,
        detected_identity="wrong.account",
    )

    current = repository.get_owned("account-a", aggregate.login_session.id)
    assert current is not None
    assert current.login_session.state == "waiting_user"
    assert current.login_session.detected_identity == "wrong.account"
    assert current.connection.auth_status == "required"


def test_preparing_login_cancel_propagates_to_prepare_task(
    tmp_path: Path,
) -> None:
    session_factory = _database(tmp_path)
    coordinator = FakeCoordinator()
    service = AccountLoginSessionService(
        repository=AccountLoginSessionRepository(session_factory),
        environment_repository=ExecutionEnvironmentV1Repository(session_factory),
        task_coordinator=coordinator,  # type: ignore[arg-type]
        login_timeout_seconds=lambda: 600,
        probe_timeout_seconds=lambda: 20,
        cancel_timeout_seconds=lambda: 2,
    )
    accepted = asyncio.run(
        service.create(
            "account-a",
            environment_id="environment-a",
            idempotency_key="login-cancel-create",
            request_id="request-create",
            operation_id="operation-create",
        )
    )

    cancelled = asyncio.run(
        service.cancel(
            "account-a",
            accepted.sessionId,
            idempotency_key="login-cancel",
        )
    )

    assert cancelled.state == "cancelled"
    assert coordinator.cancelled == [accepted.taskId]


def test_login_cancel_failure_preserves_diagnostic_context(
    tmp_path: Path,
) -> None:
    session_factory = _database(tmp_path)
    coordinator = FakeCoordinator(cancel_fails=True)
    service = AccountLoginSessionService(
        repository=AccountLoginSessionRepository(session_factory),
        environment_repository=ExecutionEnvironmentV1Repository(session_factory),
        task_coordinator=coordinator,  # type: ignore[arg-type]
        login_timeout_seconds=lambda: 600,
        probe_timeout_seconds=lambda: 20,
        cancel_timeout_seconds=lambda: 2,
    )
    accepted = asyncio.run(
        service.create(
            "account-a",
            environment_id="environment-a",
            idempotency_key="login-cancel-failed-create",
            request_id="request-create",
            operation_id="operation-create",
        )
    )

    with pytest.raises(DomainError) as captured:
        asyncio.run(
            service.cancel(
                "account-a",
                accepted.sessionId,
                idempotency_key="login-cancel-failed",
            )
        )

    assert captured.value.error_code == ErrorCode.LOGIN_SESSION_CANCEL_INCOMPLETE

    current = service.get("account-a", accepted.sessionId)
    assert current.state == "failed"
    assert current.errorCode == "LOGIN_SESSION_CANCEL_INCOMPLETE"
    assert current.errorLogId is not None


class FakeCoordinator:
    def __init__(self, *, cancel_fails: bool = False) -> None:
        self.index = 0
        self.cancel_fails = cancel_fails
        self.cancelled: list[str] = []

    async def submit_account_task(self, _account_id: str, **_kwargs: object):
        self.index += 1
        return SimpleNamespace(id=f"task-{self.index}")

    async def cancel_account_task(
        self,
        _account_id: str,
        task_id: str,
        **_kwargs: object,
    ):
        if self.cancel_fails:
            raise RuntimeError("cancel failed")
        self.cancelled.append(task_id)
        return SimpleNamespace(status=SimpleNamespace(value="completed"))


class FakeBrowserRuntime:
    def __init__(self) -> None:
        self.navigations: list[tuple[int, str]] = []

    def navigate(self, *, debug_port: int, url: str) -> None:
        self.navigations.append((debug_port, url))


class FakeProbe:
    def __init__(self, *, identity: str) -> None:
        self.identity = identity

    def probe(self, *, debug_port: int, timeout_seconds: int):
        assert debug_port == 9222
        assert timeout_seconds == 20
        return TikTokSessionProbeResult(
            authenticated=True,
            identity=self.identity,
        )

    def clear_session(self, *, debug_port: int, timeout_seconds: int) -> None:
        assert debug_port == 9222
        assert timeout_seconds == 20


class FakeTaskContext:
    attempt = 1

    def __init__(self, task_id: str, account_id: str) -> None:
        self.task_id = task_id
        self.account_id = account_id

    async def report_progress(self, _progress: float) -> None:
        return None

    def raise_if_cancelled(self) -> None:
        return None

    def enable_commit_coordination(self):
        return SimpleNamespace(commit=lambda callback: callback())


def _database(tmp_path: Path) -> sessionmaker:
    engine = create_runtime_engine(tmp_path / "runtime.db")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as database:
        for account_id, username in (
            ("account-a", "efficiency.lab"),
            ("account-b", "other.account"),
        ):
            database.add(
                Account(
                    id=account_id,
                    name=account_id,
                    username=username,
                    platform="tiktok",
                    status="draft",
                    revision=1,
                    created_at="2026-08-02T00:00:00Z",
                    updated_at="2026-08-02T00:00:00Z",
                )
            )
        database.flush()
        database.add(
            DeviceWorkspace(
                id="workspace-a",
                account_id="account-a",
                name="账号 A 工作区",
                root_path=str(tmp_path / "workspace-a"),
                root_ref="wr_0123456789abcdef0123456789abcdef",
                ownership_state="owned",
                revision=2,
                status="ready",
                error_count=0,
            )
        )
        database.flush()
        database.add(
            BrowserInstance(
                id="browser-a",
                account_id="account-a",
                workspace_id="workspace-a",
                name="Chrome",
                profile_path=str(tmp_path / "workspace-a" / "browser-profile"),
                status="running",
                process_id=1234,
                debug_host="127.0.0.1",
                debug_port=9222,
                runtime_evidence_json=json.dumps(
                    {
                        "schemaVersion": 1,
                        "ownerMarkerVersion": 1,
                        "debugHost": "127.0.0.1",
                    }
                ),
                ownership_state="owned",
                revision=2,
            )
        )
        database.flush()
        database.add(
            ExecutionBinding(
                id="environment-a",
                account_id="account-a",
                device_workspace_id="workspace-a",
                browser_instance_id="browser-a",
                status="active",
                source="p0g",
                revision=2,
            )
        )
        database.flush()
        database.add(
            AccountConnection(
                id="connection-a",
                account_id="account-a",
                auth_status="required",
                health_status="unknown",
                active_execution_binding_id="environment-a",
                revision=1,
                created_at="2026-08-02T00:00:00Z",
                updated_at="2026-08-02T00:00:00Z",
            )
        )
        database.commit()
    return factory
