from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from sqlalchemy.orm import sessionmaker

import services.accounts.assembly as assembly_module
from app.runtime_kernel import _RuntimeRecoveryService
from app.secret_store import FileSecretStore
from repositories.account_configuration_v1_repository import (
    AccountConfigurationV1Repository,
)
from repositories.account_connection_v1_repository import (
    AccountConnectionV1Repository,
)
from repositories.account_workspace_v1_repository import (
    AccountWorkspaceV1Repository,
)
from repositories.knowledge_v1_repository import KnowledgeV1Repository
from repositories.mutation_idempotency_repository import (
    MutationIdempotencyRepository,
)
from repositories.runtime_task_repository import RuntimeTaskRepository
from services.accounts.assembly import build_account_v1_services
from services.accounts.idempotency_cleanup import (
    MutationIdempotencyReconciler,
)
from services.accounts.workspace_activation import (
    AccountWorkspaceActivationService,
)
from services.knowledge import KnowledgeIndexSubmissionService
from services.tasks.handler_registry import TaskHandlerRegistry
from services.tasks.recovery import TaskRecoveryService
from services.tasks.snapshot import TaskSnapshotPolicy
from services.tasks.types import TaskRecoveryPlan


def test_account_v1_assembly_exposes_bundle_and_registers_tasks(
    tmp_path: Path,
) -> None:
    registry = TaskHandlerRegistry()
    reconcilers: list[object] = []
    session_factory = Mock(spec=sessionmaker)
    config_bus = SimpleNamespace(
        get=lambda: SimpleNamespace(
            values={
                "accounts.requiredCapabilities": [],
                "api.mutationIdempotencyTtlSeconds": 604_800,
                "ui.recentPages": {},
                "knowledge.index.maxSourceBytes": 20 * 1024 * 1024,
                "knowledge.index.urlTimeoutSeconds": 15,
                "knowledge.index.maxRedirects": 3,
                "runtime.taskSnapshotMaxBytes": 64 * 1024,
                "connection.loginSessionTimeoutSeconds": 600,
                "connection.probeTimeoutSeconds": 20,
            },
            revision=0,
        )
    )

    bundle = build_account_v1_services(
        session_factory=session_factory,
        event_service=Mock(),
        config_bus_service=config_bus,
        task_coordinator=Mock(),
        task_handler_registry=registry,
        startup_reconciler_registrar=reconcilers.append,
        browser_runtime=Mock(),
        secret_store=FileSecretStore(tmp_path / "secrets.json"),
        knowledge_content_root=tmp_path / "accounts",
        account_repository=AccountWorkspaceV1Repository(),
        connection_repository=AccountConnectionV1Repository(),
        configuration_repository=AccountConfigurationV1Repository(),
        knowledge_repository=KnowledgeV1Repository(),
        idempotency_repository=MutationIdempotencyRepository(),
        task_repository=RuntimeTaskRepository(
            session_factory=session_factory
        ),
    )

    assert tuple(bundle.__dataclass_fields__) == (
        "unit_of_work",
        "read_model",
        "commands",
        "workspace_activation",
        "copy_config",
        "tasks",
        "connection",
        "login_sessions",
        "positioning",
        "knowledge",
        "knowledge_index",
        "branding",
    )
    assert isinstance(
        bundle.knowledge_index,
        KnowledgeIndexSubmissionService,
    )
    assert isinstance(
        bundle.workspace_activation,
        AccountWorkspaceActivationService,
    )
    assert registry.task_types() == (
        "account.archive_cleanup",
        "account.connection_check",
        "account.health_check",
        "account.login.prepare",
        "account.login.probe",
        "account.logout",
        "account.restore_health_check",
        "knowledge.index",
    )
    assert len(reconcilers) == 2
    assert isinstance(
        getattr(reconcilers[0], "__self__", None),
        MutationIdempotencyReconciler,
    )
    assert getattr(reconcilers[1], "__name__", None) == (
        "reconcile_knowledge_index"
    )


def test_runtime_recovery_reconciles_before_resumable_tasks_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    order: list[str] = []
    expected = TaskRecoveryPlan(
        resumable_task_ids=("task_resume",),
        interrupted_task_ids=(),
        timed_out_task_ids=(),
        cancelled_task_ids=(),
    )

    async def prepare_tasks(_: TaskRecoveryService) -> TaskRecoveryPlan:
        order.append("prepare")
        return expected

    def schedule_tasks(
        _: TaskRecoveryService,
        plan: TaskRecoveryPlan,
    ) -> None:
        assert plan is expected
        order.append("schedule")

    monkeypatch.setattr(
        TaskRecoveryService,
        "prepare_recovery",
        prepare_tasks,
    )
    monkeypatch.setattr(
        TaskRecoveryService,
        "schedule_recovery",
        schedule_tasks,
    )
    service = _RuntimeRecoveryService(
        task_service=Mock(),
        handler_registry=TaskHandlerRegistry(),
        snapshot_policy=Mock(),
        scheduler=Mock(),
        startup_reconcilers=[lambda: order.append("knowledge")],
    )

    result = asyncio.run(service.recover())

    assert result is expected
    assert order == ["prepare", "knowledge", "schedule"]


def test_active_knowledge_sources_are_loaded_from_task_snapshot() -> None:
    snapshot_policy = TaskSnapshotPolicy(max_bytes=64 * 1024)
    snapshot = snapshot_policy.freeze(
        {
            "sourceIds": ["ksrc_active_1", "ksrc_active_2"],
            "policy": {
                "maxSourceBytes": 20 * 1024 * 1024,
                "urlTimeoutSeconds": 15,
                "maxRedirects": 3,
                "configRevision": 4,
            },
        },
        allowed_fields=frozenset({"sourceIds", "policy"}),
        handler_version=1,
        idempotency_key="idem-active-knowledge-index",
        request_id="req_active_knowledge_index",
        operation_id="op_active_knowledge_index",
        attempt=1,
        retry_of_task_id=None,
        requested_timeout_seconds=None,
    )
    record = SimpleNamespace(
        id="task_active_knowledge_index",
        account_id="acc_a",
        task_type="knowledge.index",
        config_snapshot_json=snapshot.serialized,
        handler_version=1,
        idempotency_key_hash=snapshot.key_hash,
        request_hash=snapshot.request_hash,
    )

    active = assembly_module._active_knowledge_source_ids(
        [record],
        snapshot_policy=snapshot_policy,
    )

    assert active == {
        "acc_a": frozenset(
            {"ksrc_active_1", "ksrc_active_2"}
        )
    }


def test_invalid_active_snapshot_blocks_startup_reconciliation(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(
        assembly_module,
        "_list_account_ids",
        lambda _unit_of_work: ("acc_a",),
    )
    record = SimpleNamespace(
        id="task_invalid_knowledge_index",
        account_id="acc_a",
        task_type="knowledge.index",
        config_snapshot_json="{",
        handler_version=1,
        idempotency_key_hash="0" * 64,
        request_hash="1" * 64,
    )
    task_repository = SimpleNamespace(
        list_non_terminal=lambda: [record]
    )
    reconciler = Mock()
    content_store = Mock()

    with caplog.at_level(logging.ERROR, logger=assembly_module.log.name):
        with pytest.raises(
            RuntimeError,
            match="已停止启动对账",
        ):
            assembly_module._reconcile_knowledge_index(
                unit_of_work=Mock(),
                task_repository=task_repository,
                reconciler=reconciler,
                snapshot_policy=TaskSnapshotPolicy(
                    max_bytes=64 * 1024
                ),
                content_store=content_store,
            )

    reconciler.reconcile.assert_not_called()
    content_store.reconcile_orphaned_text_files.assert_not_called()
    assert "解析非终态知识索引任务快照失败" in caplog.text
