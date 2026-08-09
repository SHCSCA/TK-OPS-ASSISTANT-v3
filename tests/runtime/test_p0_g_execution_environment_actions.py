from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy.orm import sessionmaker

from domain.models import Base
from domain.models.account import Account
from errors import DomainError, ErrorCode
from persistence.engine import create_runtime_engine
from repositories.execution_environment_v1_repository import (
    ExecutionEnvironmentV1Repository,
)
from services.browser_runtime import BrowserRuntimeHealth
from services.execution_environments.actions import (
    ExecutionEnvironmentActionService,
)
from services.execution_environments.service import ExecutionEnvironmentService


def test_stale_stop_task_cannot_control_running_browser() -> None:
    repository = _ActionRepository(browser_status="running", revision=4)
    browser = _BrowserRuntime()
    ownership = _OwnershipService()
    service = _action_service(repository, browser, ownership)

    with pytest.raises(DomainError) as captured:
        service.stop(
            account_id="account-a",
            environment_id="environment-a",
            expected_revision=3,
            task_id="task-stale-stop",
        )

    assert captured.value.error_code == ErrorCode.REVISION_CONFLICT
    assert ownership.verify_count == 0
    assert browser.stop_count == 0


def test_resumed_stop_task_converges_when_browser_is_already_stopped() -> None:
    repository = _ActionRepository(browser_status="stopped", revision=5)
    events = _EventService()
    service = _action_service(
        repository,
        _BrowserRuntime(),
        _OwnershipService(),
        events=events,
    )

    revision = service.stop(
        account_id="account-a",
        environment_id="environment-a",
        expected_revision=3,
        task_id="task-resumed-stop",
    )

    assert revision == 5
    assert len(events.events) == 1
    assert events.events[0].event_type == "execution_environment.stopped"


def test_check_rejects_stopped_environment_without_reporting_healthy() -> None:
    repository = _ActionRepository(browser_status="stopped", revision=5)
    browser = _BrowserRuntime()
    service = _action_service(repository, browser, _OwnershipService())

    with pytest.raises(DomainError) as captured:
        service.check(
            account_id="account-a",
            environment_id="environment-a",
            expected_revision=5,
            task_id="task-check-stopped",
        )

    assert captured.value.error_code == ErrorCode.EXECUTION_ENVIRONMENT_NOT_ELIGIBLE
    assert browser.health_count == 0
    assert repository.mark_checked_count == 0


def test_failed_health_check_becomes_recoverable_stopped_environment(
    tmp_path: Path,
) -> None:
    factory = _database(tmp_path)
    root = tmp_path / "workspace"
    root.mkdir()
    repository = ExecutionEnvironmentV1Repository(factory)
    aggregate = repository.ensure_draft(
        account_id="account-a",
        idempotency_key="health-failure-environment",
        name="健康失败环境",
        workspace_display_name="真实工作目录",
        root_ref="wr_abcdefabcdefabcdefabcdefabcdefab",
        root_path=str(root),
        browser_kind="chrome",
    )
    repository.mark_ready(
        account_id="account-a",
        environment_id=aggregate.binding.id,
        activate=False,
        executable_path=str(tmp_path / "chrome.exe"),
        process_id=4321,
        debug_host="127.0.0.1",
        debug_port=49152,
        runtime_evidence_json='{"ownerMarkerVersion":1}',
    )

    repository.mark_checked(
        account_id="account-a",
        environment_id=aggregate.binding.id,
        healthy=False,
        error_code=ErrorCode.EXECUTION_ENVIRONMENT_NOT_ELIGIBLE.value,
        error_log_id="log-health-failure",
    )

    failed = repository.get_owned("account-a", aggregate.binding.id)
    assert failed is not None
    assert failed.browser.status == "stopped"
    assert failed.browser.process_id is None
    assert failed.workspace.status == "offline"
    assert failed.binding.status == "failed"
    assert ExecutionEnvironmentService._to_dto(failed).browser.ownershipVerified is False


class _ActionRepository:
    def __init__(self, *, browser_status: str, revision: int) -> None:
        self.aggregate = SimpleNamespace(
            binding=SimpleNamespace(
                id="environment-a",
                status="active",
                revision=revision,
            ),
            browser=SimpleNamespace(
                id="browser-a",
                status=browser_status,
                process_id=4321,
                debug_host="127.0.0.1",
                debug_port=49152,
                executable_path="C:/chrome.exe",
                runtime_evidence_json='{"ownerMarkerVersion":1}',
                profile_path="C:/profile",
            ),
            workspace=SimpleNamespace(root_ref="wr_test"),
        )
        self.mark_checked_count = 0

    def get_owned(self, _account_id: str, _environment_id: str):
        return self.aggregate

    def get_owned_including_deleted(
        self,
        _account_id: str,
        _environment_id: str,
    ):
        return self.aggregate

    def mark_checked(self, **_kwargs: object) -> int:
        self.mark_checked_count += 1
        return int(self.aggregate.binding.revision)


class _BrowserRuntime:
    def __init__(self) -> None:
        self.health_count = 0
        self.stop_count = 0

    def health(self, **_kwargs: object) -> BrowserRuntimeHealth:
        self.health_count += 1
        return BrowserRuntimeHealth(alive=True)

    def stop(self, **_kwargs: object) -> BrowserRuntimeHealth:
        self.stop_count += 1
        return BrowserRuntimeHealth(alive=False)


class _OwnershipService:
    def __init__(self) -> None:
        self.verify_count = 0

    def verify_existing(self, **_kwargs: object) -> None:
        self.verify_count += 1


class _EventService:
    def __init__(self) -> None:
        self.events: list[object] = []

    def append_standalone_idempotent(self, event: object) -> None:
        self.events.append(event)


def _action_service(
    repository: _ActionRepository,
    browser: _BrowserRuntime,
    ownership: _OwnershipService,
    *,
    events: _EventService | None = None,
) -> ExecutionEnvironmentActionService:
    return ExecutionEnvironmentActionService(
        repository=repository,
        browser_runtime=browser,
        ownership_service=ownership,
        provisioner=SimpleNamespace(),
        event_service=events or _EventService(),
    )


def _database(tmp_path: Path) -> sessionmaker:
    engine = create_runtime_engine(tmp_path / "execution-actions.db")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as database:
        database.add(
            Account(
                id="account-a",
                name="执行环境动作测试",
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
