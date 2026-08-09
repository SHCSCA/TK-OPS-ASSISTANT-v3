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
from services.execution_environments.service import ExecutionEnvironmentService
from services.execution_environments.workspace_root_resolver import (
    WorkspaceRootResolver,
)
from services.tasks.types import TaskStatus

ROOT_REF = "wr_0123456789abcdef0123456789abcdef"


def test_fresh_database_creates_real_account_scoped_draft_without_seed(
    tmp_path: Path,
) -> None:
    session_factory = _database(tmp_path)
    workspace = tmp_path / "account-workspace"
    workspace.mkdir()
    registry = _registry(tmp_path, workspace)
    coordinator = FakeTaskCoordinator()
    service = ExecutionEnvironmentService(
        repository=ExecutionEnvironmentV1Repository(session_factory),
        root_resolver=WorkspaceRootResolver(registry),
        task_coordinator=coordinator,  # type: ignore[arg-type]
    )

    accepted = asyncio.run(
        service.create(
            "account-a",
            ExecutionEnvironmentCreateInput(
                name="主执行环境",
                rootRef=ROOT_REF,
                browser={"kind": "chrome", "selection": "auto"},
                activateWhenReady=False,
            ),
            idempotency_key="environment-create-1",
            request_id="request-1",
            operation_id="operation-1",
        )
    )
    repeated = asyncio.run(
        service.create(
            "account-a",
            ExecutionEnvironmentCreateInput(
                name="主执行环境",
                rootRef=ROOT_REF,
                browser={"kind": "chrome", "selection": "auto"},
                activateWhenReady=False,
            ),
            idempotency_key="environment-create-1",
            request_id="request-2",
            operation_id="operation-2",
        )
    )

    assert repeated.environmentId == accepted.environmentId
    items = service.list("account-a").items
    assert len(items) == 1
    assert items[0].status == "provisioning"
    assert items[0].workspace.rootRef == ROOT_REF
    assert items[0].workspace.displayName == "account-workspace"
    serialized = items[0].model_dump_json()
    assert str(workspace) not in serialized
    assert "profile_path" not in serialized
    assert coordinator.payloads[0] == {
        "environmentId": accepted.environmentId,
        "rootRef": ROOT_REF,
        "activateWhenReady": False,
    }


def test_environment_creation_rejects_cross_account_root(
    tmp_path: Path,
) -> None:
    session_factory = _database(tmp_path)
    workspace = tmp_path / "account-workspace"
    workspace.mkdir()
    registry = _registry(tmp_path, workspace)
    service = ExecutionEnvironmentService(
        repository=ExecutionEnvironmentV1Repository(session_factory),
        root_resolver=WorkspaceRootResolver(registry),
        task_coordinator=FakeTaskCoordinator(),  # type: ignore[arg-type]
    )

    with pytest.raises(DomainError) as captured:
        asyncio.run(
            service.create(
                "account-b",
                ExecutionEnvironmentCreateInput(
                    name="错误环境",
                    rootRef=ROOT_REF,
                    browser={"kind": "edge", "selection": "auto"},
                    activateWhenReady=False,
                ),
                idempotency_key="environment-cross-account",
                request_id="request-cross",
                operation_id="operation-cross",
            )
        )

    assert captured.value.error_code == ErrorCode.WORKSPACE_ROOT_NOT_FOUND


def test_failed_environment_retries_original_task_and_preserves_environment(
    tmp_path: Path,
) -> None:
    session_factory = _database(tmp_path)
    workspace = tmp_path / "account-workspace"
    workspace.mkdir()
    coordinator = FakeTaskCoordinator()
    repository = ExecutionEnvironmentV1Repository(session_factory)
    service = ExecutionEnvironmentService(
        repository=repository,
        root_resolver=WorkspaceRootResolver(_registry(tmp_path, workspace)),
        task_coordinator=coordinator,  # type: ignore[arg-type]
    )
    accepted = asyncio.run(
        service.create(
            "account-a",
            ExecutionEnvironmentCreateInput(
                name="主执行环境",
                rootRef=ROOT_REF,
                browser={"kind": "chrome", "selection": "auto"},
                activateWhenReady=False,
            ),
            idempotency_key="environment-retry-origin",
            request_id="request-create",
            operation_id="operation-create",
        )
    )
    repository.mark_failed(
        account_id="account-a",
        environment_id=accepted.environmentId,
        error_code=ErrorCode.EXECUTION_ENVIRONMENT_PROVISION_FAILED.value,
        error_log_id="log-provision-failed",
    )
    failed = service.get("account-a", accepted.environmentId)

    retried = asyncio.run(
        service.retry(
            "account-a",
            accepted.environmentId,
            expected_revision=failed.revision,
            idempotency_key="environment-retry-1",
            request_id="request-retry",
            operation_id="operation-retry",
        )
    )

    assert retried.environmentId == accepted.environmentId
    assert retried.retryOfTaskId == accepted.taskId
    assert retried.taskId == "task-environment-retry"
    current = service.get("account-a", accepted.environmentId)
    assert current.status == "provisioning"
    assert current.lastTaskId == retried.taskId
    assert current.lastRetryOfTaskId == accepted.taskId
    assert current.workspace.rootRef == ROOT_REF


class FakeTaskCoordinator:
    def __init__(self) -> None:
        self.payloads: list[dict[str, object]] = []

    async def submit_account_task(
        self,
        _account_id: str,
        **kwargs: object,
    ) -> SimpleNamespace:
        self.payloads.append(dict(kwargs["payload"]))  # type: ignore[arg-type]
        return SimpleNamespace(id="task-environment-provision")

    async def get_account_task(self, _account_id: str, task_id: str):
        return SimpleNamespace(
            id=task_id,
            task_type="execution_environment.provision",
            status=TaskStatus.FAILED,
        )

    async def retry_account_task(
        self,
        _account_id: str,
        _task_id: str,
        **_kwargs: object,
    ) -> SimpleNamespace:
        return SimpleNamespace(id="task-environment-retry")


def _database(tmp_path: Path) -> sessionmaker:
    engine = create_runtime_engine(tmp_path / "runtime.db")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        for account_id in ("account-a", "account-b"):
            session.add(
                Account(
                    id=account_id,
                    name=account_id,
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


def _registry(tmp_path: Path, workspace: Path) -> Path:
    path = tmp_path / "workspace-roots.v1.json"
    path.write_text(
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
    return path
