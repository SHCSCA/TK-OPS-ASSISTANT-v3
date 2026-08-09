from __future__ import annotations

import asyncio
import json
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
from schemas.v1.execution_environments import ExecutionEnvironmentCreateInput
from services.browser_runtime import BrowserLaunchResult, BrowserRuntimeHealth
from services.execution_environments.browser_process import (
    BrowserOwnershipEvidence,
    BrowserProcessOwnershipError,
)
from services.execution_environments.provisioning import (
    ExecutionEnvironmentProvisioner,
)
from services.execution_environments.service import ExecutionEnvironmentService
from services.execution_environments.workspace_root_resolver import (
    WorkspaceRootResolver,
)

ROOT_REF = "wr_abcdefabcdefabcdefabcdefabcdefab"


@pytest.mark.parametrize("ownership_recheck_fails", [False, True])
def test_provision_failure_only_stops_browser_with_proven_ownership(
    tmp_path: Path,
    ownership_recheck_fails: bool,
) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    repository = _FailingReadyRepository(root)
    browser = _BrowserRuntime()
    ownership = _OwnershipService(recheck_fails=ownership_recheck_fails)
    provisioner = ExecutionEnvironmentProvisioner(
        repository=repository,
        root_resolver=_RootResolver(root),
        browser_runtime=browser,
        ownership_service=ownership,
        event_service=_UnusedEventService(),
    )

    with pytest.raises(DomainError) as captured:
        provisioner.provision(
            account_id="account-a",
            environment_id="environment-a",
            root_ref=ROOT_REF,
            activate_when_ready=False,
            task_id="task-a",
        )

    assert captured.value.error_code == ErrorCode.EXECUTION_ENVIRONMENT_PROVISION_FAILED
    assert ownership.recheck_count == 1
    assert browser.stop_count == (0 if ownership_recheck_fails else 1)
    assert repository.browser_orphaned is ownership_recheck_fails


def test_task_submission_failure_does_not_leave_provisioning_half_object(
    tmp_path: Path,
) -> None:
    session_factory = _database(tmp_path)
    workspace = tmp_path / "real-workspace"
    workspace.mkdir()
    registry = tmp_path / "workspace-roots.v1.json"
    registry.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "revision": 1,
                "roots": [
                    {
                        "accountId": "account-a",
                        "canonicalPath": str(workspace.resolve()),
                        "createdAt": "2026-08-02T00:00:00Z",
                        "displayName": workspace.name,
                        "revision": 1,
                        "rootRef": ROOT_REF,
                        "status": "active",
                        "updatedAt": "2026-08-02T00:00:00Z",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    repository = ExecutionEnvironmentV1Repository(session_factory)
    service = ExecutionEnvironmentService(
        repository=repository,
        root_resolver=WorkspaceRootResolver(registry),
        task_coordinator=_FailingTaskCoordinator(),
    )

    with pytest.raises(RuntimeError, match="模拟任务提交失败"):
        asyncio.run(
            service.create(
                "account-a",
                ExecutionEnvironmentCreateInput(
                    name="故障补偿环境",
                    rootRef=ROOT_REF,
                    browser={"kind": "chrome", "selection": "auto"},
                    activateWhenReady=False,
                ),
                idempotency_key="environment-submit-failure",
                request_id="request-submit-failure",
                operation_id="operation-submit-failure",
            )
        )

    environments = repository.list_owned("account-a")
    assert len(environments) == 1
    assert environments[0].binding.status == "failed"
    assert environments[0].workspace.status == "failed"
    assert environments[0].browser.status == "failed"


class _FailingReadyRepository:
    def __init__(self, root: Path) -> None:
        self.aggregate = SimpleNamespace(
            binding=SimpleNamespace(id="environment-a"),
            browser=SimpleNamespace(id="browser-a"),
            workspace=SimpleNamespace(root_ref=ROOT_REF, root_path=str(root)),
        )
        self.browser_orphaned: bool | None = None

    def get_owned(self, _account_id: str, _environment_id: str):
        return self.aggregate

    def mark_ready(self, **_kwargs: object) -> int:
        raise RuntimeError("模拟数据库提交失败")

    def mark_failed(self, **kwargs: object) -> None:
        self.browser_orphaned = bool(kwargs["browser_orphaned"])


class _RootResolver:
    def __init__(self, root: Path) -> None:
        self.root = root

    def resolve(self, *, account_id: str, root_ref: str):
        assert account_id == "account-a"
        assert root_ref == ROOT_REF
        return SimpleNamespace(path=self.root)


class _BrowserRuntime:
    def __init__(self) -> None:
        self.stop_count = 0

    def launch(self, *, profile_path: Path) -> BrowserLaunchResult:
        return BrowserLaunchResult(
            process_id=4321,
            debug_host="127.0.0.1",
            debug_port=49152,
            executable_path=str(profile_path.parent / "chrome.exe"),
        )

    def stop(self, *, process_id: int | None) -> BrowserRuntimeHealth:
        assert process_id == 4321
        self.stop_count += 1
        return BrowserRuntimeHealth(alive=False, process_id=process_id)


class _OwnershipService:
    def __init__(self, *, recheck_fails: bool) -> None:
        self.recheck_fails = recheck_fails
        self.recheck_count = 0

    def create_marker(self, **_kwargs: object) -> str:
        return "nonce"

    def verify_launch(self, **_kwargs: object) -> BrowserOwnershipEvidence:
        return BrowserOwnershipEvidence(
            schemaVersion=1,
            runtimeGeneration="generation-a",
            executableCanonicalPathHash="a" * 64,
            profileCanonicalPathHash="b" * 64,
            processId=4321,
            processCreatedAt="2026-08-02T00:00:00Z",
            launchNonceHash="c" * 64,
            debugHost="127.0.0.1",
            debugPort=49152,
            ownerMarkerVersion=1,
        )

    def verify_existing(self, **_kwargs: object) -> None:
        self.recheck_count += 1
        if self.recheck_fails:
            raise BrowserProcessOwnershipError("模拟所有权证据失效")


class _UnusedEventService:
    def append_standalone(self, _event: object) -> None:
        raise AssertionError("失败路径不应发布完成事件")


class _FailingTaskCoordinator:
    async def submit_account_task(self, _account_id: str, **_kwargs: object):
        raise RuntimeError("模拟任务提交失败")


def _database(tmp_path: Path) -> sessionmaker:
    engine = create_runtime_engine(tmp_path / "compensation.db")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        session.add(
            Account(
                id="account-a",
                name="补偿测试账号",
                platform="tiktok",
                username=None,
                status="draft",
                revision=1,
                created_at="2026-08-02T00:00:00Z",
                updated_at="2026-08-02T00:00:00Z",
            )
        )
        session.commit()
    return factory
