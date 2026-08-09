from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from app.secret_store import FileSecretStore
from domain.models import Base
from domain.models.account import Account
from domain.models.runtime_event import RuntimeEvent
from errors import DomainError, ErrorCode
from persistence.engine import create_runtime_engine
from repositories.account_login_session_repository import (
    AccountLoginSessionRepository,
)
from repositories.execution_environment_v1_repository import (
    ExecutionEnvironmentV1Repository,
)
from repositories.runtime_event_repository import RuntimeEventRepository
from services.accounts.archive_cleanup import AccountArchiveCleanupService
from services.browser_runtime import BrowserRuntimeHealth
from services.events import RuntimeEventService
from services.execution_environments.browser_process import (
    BrowserProcessOwnershipError,
)

from tests.runtime.p0c_account_integration_support import (
    account_revision,
    create_account,
    mutation_headers,
    session,
    wait_account_task,
)


def test_archive_is_persistent_task_and_emits_one_terminal_event(
    licensed_runtime_client: TestClient,
) -> None:
    client = licensed_runtime_client
    account_id, revision = create_account(
        client,
        name="归档任务账号",
        idempotency_key="p0g-archive-task-account",
    )

    accepted = client.post(
        f"/api/v1/accounts/{account_id}/archive",
        headers=mutation_headers(
            revision=revision,
            idempotency_key="p0g-archive-task",
        ),
        json={"reason": "验证持久归档清理"},
    )

    assert accepted.status_code == 202, accepted.text
    task_id = str(accepted.json()["data"]["taskId"])
    task = wait_account_task(client, account_id=account_id, task_id=task_id)
    assert task["taskType"] == "account.archive_cleanup"
    assert task["status"] == "completed"
    assert task["completionKind"] == "succeeded"
    assert task["cancellable"] is False

    listed = client.get(f"/api/v1/accounts/{account_id}/tasks?limit=20")
    assert listed.status_code == 200, listed.text
    assert any(item["taskId"] == task_id for item in listed.json()["data"]["items"])
    assert account_revision(client, account_id) > revision

    with session(client) as database:
        event_count = database.scalar(
            select(func.count(RuntimeEvent.event_id)).where(
                RuntimeEvent.event_type == "account.archived",
                RuntimeEvent.account_id == account_id,
                RuntimeEvent.task_id == task_id,
            )
        )
    assert event_count == 1


def test_archive_ownership_failure_keeps_workspace_and_marks_cleanup_failed(
    tmp_path: Path,
) -> None:
    session_factory = _database(tmp_path)
    root = tmp_path / "real-workspace"
    root.mkdir()
    executable = tmp_path / "chrome.exe"
    executable.write_bytes(b"test")
    environments = ExecutionEnvironmentV1Repository(session_factory)
    aggregate = environments.ensure_draft(
        account_id="account-a",
        idempotency_key="archive-failure-environment",
        name="归档失败环境",
        workspace_display_name="真实工作目录",
        root_ref="wr_abcdefabcdefabcdefabcdefabcdefab",
        root_path=str(root),
        browser_kind="chrome",
    )
    environments.mark_ready(
        account_id="account-a",
        environment_id=aggregate.binding.id,
        activate=True,
        executable_path=str(executable),
        process_id=4321,
        debug_host="127.0.0.1",
        debug_port=49152,
        runtime_evidence_json="{}",
    )
    browser = _BrowserRuntime()
    cleanup = AccountArchiveCleanupService(
        session_factory=session_factory,
        environments=environments,
        login_sessions=AccountLoginSessionRepository(session_factory),
        browser_runtime=browser,
        ownership_service=_RejectingOwnershipService(),
        session_probe=_SessionProbe(),
        secret_store=FileSecretStore(tmp_path / "secrets.json"),
        event_service=RuntimeEventService(
            RuntimeEventRepository(session_factory=session_factory),
            replay_limit=100,
        ),
    )

    with pytest.raises(DomainError) as captured:
        cleanup.cleanup(
            account_id="account-a",
            expected_revision=1,
            reason_provided=True,
            task_id="task-archive-failure",
        )

    assert captured.value.error_code == ErrorCode.BROWSER_PROCESS_OWNERSHIP_UNPROVEN
    with session_factory() as database:
        account = database.get(Account, "account-a")
        assert account is not None
        assert account.status == "attention"
        assert account.status_reason_code == "ARCHIVE_CLEANUP_FAILED"
    failed = environments.get_owned("account-a", aggregate.binding.id)
    assert failed is not None
    assert failed.binding.status == "cleanup_failed"
    assert failed.workspace.status == "cleanup_failed"
    assert failed.browser.status == "orphaned"
    assert browser.stop_count == 0
    assert root.is_dir()


class _BrowserRuntime:
    def __init__(self) -> None:
        self.stop_count = 0

    def stop(self, *, process_id: int | None) -> BrowserRuntimeHealth:
        self.stop_count += 1
        return BrowserRuntimeHealth(alive=False, process_id=process_id)


class _RejectingOwnershipService:
    def verify_existing(self, **_kwargs: object) -> None:
        raise BrowserProcessOwnershipError("模拟浏览器所有权证据失效")


class _SessionProbe:
    def clear_session(self, **_kwargs: object) -> None:
        return None


def _database(tmp_path: Path) -> sessionmaker:
    engine = create_runtime_engine(tmp_path / "archive-cleanup.db")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as database:
        database.add(
            Account(
                id="account-a",
                name="归档失败测试账号",
                platform="tiktok",
                username=None,
                status="draft",
                revision=1,
                created_at="2026-08-02T00:00:00Z",
                updated_at="2026-08-02T00:00:00Z",
            )
        )
        database.commit()
    return factory
