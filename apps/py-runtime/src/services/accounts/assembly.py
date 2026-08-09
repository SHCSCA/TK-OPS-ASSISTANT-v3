from __future__ import annotations

import logging
import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session, sessionmaker

from errors import DomainError, ErrorCode
from repositories.account_configuration_v1_repository import (
    AccountConfigurationV1Repository,
)
from repositories.account_connection_v1_repository import (
    AccountConnectionV1Repository,
)
from repositories.account_login_session_repository import (
    AccountLoginSessionRepository,
)
from repositories.execution_environment_v1_repository import (
    ExecutionEnvironmentV1Repository,
)
from repositories.account_workspace_v1_repository import (
    AccountWorkspaceV1Repository,
)
from repositories.knowledge_v1_repository import KnowledgeV1Repository
from repositories.mutation_idempotency_repository import (
    MutationIdempotencyRepository,
)
from repositories.runtime_task_repository import RuntimeTaskRepository
from services.accounts.branding import AccountBrandingService
from services.accounts.archive_cleanup import AccountArchiveCleanupService
from services.accounts.assembly_reconciliation import (
    active_knowledge_source_ids as _active_knowledge_source_ids,
    list_account_ids as _list_account_ids,
    list_text_source_references as _list_text_source_references,
)
from services.accounts.commands import AccountCommandService
from services.accounts.connection import AccountConnectionService
from services.accounts.copy_config import AccountConfigCopyService
from services.accounts.health_execution import AccountHealthExecutor
from services.accounts.idempotency import MutationIdempotencyService
from services.accounts.idempotency_cleanup import (
    MutationIdempotencyReconciler,
)
from services.accounts.lifecycle_sync import AccountLifecycleSynchronizer
from services.accounts.login_sessions import (
    AccountLoginSessionService,
    LoginBrowserNavigationPort,
    register_login_session_task_handlers,
)
from services.accounts.ports import (
    AccountAIReadinessPort,
    AIRecipeCopyPort,
    UnavailableAccountAIReadinessPort,
    UnavailableAIRecipeCopyPort,
)
from services.accounts.positioning import AccountPositioningService
from services.accounts.read_model import AccountReadModel
from services.accounts.readiness import AccountReadinessEvaluator
from services.accounts.runtime_policy import load_account_runtime_policy
from services.accounts.task_registration import register_account_task_handlers
from services.accounts.task_submission import AccountTaskSubmissionService
from services.accounts.unit_of_work import (
    AccountMutationExecutor,
    AccountUnitOfWork,
)
from services.accounts.workspace_activation import (
    AccountWorkspaceActivationService,
)
from services.browser_runtime import BrowserRuntime
from services.accounts.tiktok_session_probe import (
    TikTokSessionProbe,
    TikTokSessionProbePort,
)
from app.secret_store import SecretStore
from services.config import ConfigBusService
from services.events import RuntimeEventService
from services.knowledge import (
    AccountKnowledgeService,
    KnowledgeContentStore,
    KnowledgeIndexExecutor,
    KnowledgeIndexPolicy,
    KnowledgeIndexReconciler,
    KnowledgeIndexSubmissionService,
    SecureKnowledgeUrlFetcher,
    UnavailableControlledFileResolver,
    register_knowledge_index_handler,
)
from services.tasks.coordinator import TaskCoordinator
from services.tasks.handler_registry import TaskHandlerRegistry
from services.tasks.snapshot import TaskSnapshotPolicy
from services.execution_environments.browser_process import (
    BrowserProcessOwnershipService,
)

log = logging.getLogger(__name__)
_RECENT_PAGES_KEY = "ui.recentPages"
_KNOWLEDGE_MAX_SOURCE_BYTES_KEY = "knowledge.index.maxSourceBytes"
_KNOWLEDGE_URL_TIMEOUT_KEY = "knowledge.index.urlTimeoutSeconds"
_KNOWLEDGE_MAX_REDIRECTS_KEY = "knowledge.index.maxRedirects"
_TASK_SNAPSHOT_MAX_BYTES_KEY = "runtime.taskSnapshotMaxBytes"
StartupReconcilerRegistrar = Callable[[Callable[[], object]], None]


@dataclass(frozen=True, slots=True)
class AccountV1Services:
    unit_of_work: AccountUnitOfWork
    read_model: AccountReadModel
    commands: AccountCommandService
    workspace_activation: AccountWorkspaceActivationService
    copy_config: AccountConfigCopyService
    tasks: AccountTaskSubmissionService
    connection: AccountConnectionService
    login_sessions: AccountLoginSessionService
    positioning: AccountPositioningService
    knowledge: AccountKnowledgeService
    knowledge_index: KnowledgeIndexSubmissionService
    branding: AccountBrandingService


@dataclass(frozen=True, slots=True)
class KnowledgeStartupReconciliationReport:
    checked_account_count: int
    protected_active_source_count: int
    reconciled_source_count: int
    scanned_content_file_count: int
    protected_content_file_count: int
    removed_orphan_content_file_count: int


def build_account_v1_services(
    *,
    session_factory: sessionmaker[Session],
    event_service: RuntimeEventService,
    config_bus_service: ConfigBusService,
    task_coordinator: TaskCoordinator,
    task_handler_registry: TaskHandlerRegistry,
    startup_reconciler_registrar: StartupReconcilerRegistrar,
    browser_runtime: BrowserRuntime,
    secret_store: SecretStore,
    knowledge_content_root: Path,
    account_repository: AccountWorkspaceV1Repository,
    connection_repository: AccountConnectionV1Repository,
    configuration_repository: AccountConfigurationV1Repository,
    knowledge_repository: KnowledgeV1Repository,
    idempotency_repository: MutationIdempotencyRepository,
    task_repository: RuntimeTaskRepository,
    ai_readiness_port: AccountAIReadinessPort | None = None,
    ai_recipe_copy_port: AIRecipeCopyPort | None = None,
    login_browser_runtime: LoginBrowserNavigationPort | None = None,
    login_session_probe: TikTokSessionProbePort | None = None,
) -> AccountV1Services:
    try:
        return _build_account_v1_services(
            session_factory=session_factory,
            event_service=event_service,
            config_bus_service=config_bus_service,
            task_coordinator=task_coordinator,
            task_handler_registry=task_handler_registry,
            startup_reconciler_registrar=startup_reconciler_registrar,
            browser_runtime=browser_runtime,
            secret_store=secret_store,
            knowledge_content_root=knowledge_content_root,
            account_repository=account_repository,
            connection_repository=connection_repository,
            configuration_repository=configuration_repository,
            knowledge_repository=knowledge_repository,
            idempotency_repository=idempotency_repository,
            task_repository=task_repository,
            ai_readiness_port=ai_readiness_port,
            ai_recipe_copy_port=ai_recipe_copy_port,
            login_browser_runtime=login_browser_runtime,
            login_session_probe=login_session_probe,
        )
    except Exception:
        log.exception("账号 v1 服务装配失败")
        raise


def _build_account_v1_services(
    *,
    session_factory: sessionmaker[Session],
    event_service: RuntimeEventService,
    config_bus_service: ConfigBusService,
    task_coordinator: TaskCoordinator,
    task_handler_registry: TaskHandlerRegistry,
    startup_reconciler_registrar: StartupReconcilerRegistrar,
    browser_runtime: BrowserRuntime,
    secret_store: SecretStore,
    knowledge_content_root: Path,
    account_repository: AccountWorkspaceV1Repository,
    connection_repository: AccountConnectionV1Repository,
    configuration_repository: AccountConfigurationV1Repository,
    knowledge_repository: KnowledgeV1Repository,
    idempotency_repository: MutationIdempotencyRepository,
    task_repository: RuntimeTaskRepository,
    ai_readiness_port: AccountAIReadinessPort | None,
    ai_recipe_copy_port: AIRecipeCopyPort | None,
    login_browser_runtime: LoginBrowserNavigationPort | None,
    login_session_probe: TikTokSessionProbePort | None,
) -> AccountV1Services:
    unit_of_work = AccountUnitOfWork(
        session_factory,
        event_service=event_service,
        account_repository=account_repository,
        connection_repository=connection_repository,
        configuration_repository=configuration_repository,
        knowledge_repository=knowledge_repository,
        idempotency_repository=idempotency_repository,
    )
    policy_provider = lambda: load_account_runtime_policy(config_bus_service)
    idempotency_service = MutationIdempotencyService(
        idempotency_repository,
        retention_seconds=lambda: (
            policy_provider().mutation_idempotency_ttl_seconds
        ),
    )
    mutation_executor = AccountMutationExecutor(
        unit_of_work,
        idempotency_service,
    )
    readiness_evaluator = AccountReadinessEvaluator(
        ai_readiness_port or UnavailableAccountAIReadinessPort()
    )
    read_model = AccountReadModel(
        unit_of_work,
        readiness_evaluator=readiness_evaluator,
        policy_provider=policy_provider,
        recent_pages_provider=lambda: _recent_pages(config_bus_service),
    )
    lifecycle_synchronizer = AccountLifecycleSynchronizer(
        read_model=read_model,
        policy_provider=policy_provider,
    )
    health_executor = AccountHealthExecutor(
        unit_of_work,
        read_model=read_model,
        browser_runtime=browser_runtime,
        policy_provider=policy_provider,
    )
    login_repository = AccountLoginSessionRepository(session_factory)
    environment_repository = ExecutionEnvironmentV1Repository(session_factory)
    effective_probe = login_session_probe or TikTokSessionProbe()
    runtime_generation = (
        os.getenv("TK_OPS_RUNTIME_ARTIFACT_BUILD_ID", "").strip()
        or f"runtime-{uuid4().hex}"
    )
    archive_cleanup_service = AccountArchiveCleanupService(
        session_factory=session_factory,
        environments=environment_repository,
        login_sessions=login_repository,
        browser_runtime=browser_runtime,
        ownership_service=BrowserProcessOwnershipService(
            runtime_generation=runtime_generation
        ),
        session_probe=effective_probe,
        secret_store=secret_store,
        event_service=event_service,
    )
    register_account_task_handlers(
        task_handler_registry,
        executor=health_executor,
        archive_cleanup_service=archive_cleanup_service,
        coordinator=task_coordinator,
    )
    login_timeout_provider = lambda: _required_int(
        config_bus_service.get().values,
        "connection.loginSessionTimeoutSeconds",
    )
    probe_timeout_provider = lambda: _required_int(
        config_bus_service.get().values,
        "connection.probeTimeoutSeconds",
    )
    cancel_timeout_provider = lambda: _required_int(
        config_bus_service.get().values,
        "connection.cancelTimeoutSeconds",
    )
    register_login_session_task_handlers(
        task_handler_registry,
        repository=login_repository,
        browser_runtime=login_browser_runtime or browser_runtime,
        probe=effective_probe,
        secret_store=secret_store,
        probe_timeout_seconds=probe_timeout_provider,
    )
    content_store = KnowledgeContentStore(knowledge_content_root)
    knowledge_policy_provider = lambda: _knowledge_policy(config_bus_service)
    knowledge_index_executor = KnowledgeIndexExecutor(
        unit_of_work,
        content_store=content_store,
        controlled_file_resolver=UnavailableControlledFileResolver(),
        url_fetcher=SecureKnowledgeUrlFetcher(),
        lifecycle_synchronizer=lifecycle_synchronizer,
        policy_provider=knowledge_policy_provider,
    )
    register_knowledge_index_handler(
        task_handler_registry,
        executor=knowledge_index_executor,
    )
    knowledge_reconciler = KnowledgeIndexReconciler(
        unit_of_work,
        policy_provider=knowledge_policy_provider,
        lifecycle_synchronizer=lifecycle_synchronizer,
    )
    idempotency_reconciler = MutationIdempotencyReconciler(unit_of_work)

    def reconcile_knowledge_index() -> object:
        return _reconcile_knowledge_index(
            unit_of_work=unit_of_work,
            task_repository=task_repository,
            reconciler=knowledge_reconciler,
            snapshot_policy=_task_snapshot_policy(config_bus_service),
            content_store=content_store,
        )

    startup_reconciler_registrar(idempotency_reconciler.reconcile)
    startup_reconciler_registrar(reconcile_knowledge_index)
    return AccountV1Services(
        unit_of_work=unit_of_work,
        read_model=read_model,
        commands=AccountCommandService(
            unit_of_work,
            mutation_executor,
            read_model=read_model,
            policy_provider=policy_provider,
        ),
        workspace_activation=AccountWorkspaceActivationService(
            mutation_executor,
            read_model=read_model,
            policy_provider=policy_provider,
        ),
        copy_config=AccountConfigCopyService(
            mutation_executor,
            ai_recipe_copy_port=(
                ai_recipe_copy_port or UnavailableAIRecipeCopyPort()
            ),
        ),
        tasks=AccountTaskSubmissionService(
            unit_of_work,
            coordinator=task_coordinator,
        ),
        connection=AccountConnectionService(
            unit_of_work,
            mutation_executor,
        ),
        login_sessions=AccountLoginSessionService(
            repository=login_repository,
            environment_repository=environment_repository,
            task_coordinator=task_coordinator,
            login_timeout_seconds=login_timeout_provider,
            probe_timeout_seconds=probe_timeout_provider,
            cancel_timeout_seconds=cancel_timeout_provider,
        ),
        positioning=AccountPositioningService(
            unit_of_work,
            mutation_executor,
        ),
        knowledge=AccountKnowledgeService(
            unit_of_work,
            mutation_executor,
            content_store=content_store,
            lifecycle_synchronizer=lifecycle_synchronizer,
        ),
        knowledge_index=KnowledgeIndexSubmissionService(
            unit_of_work,
            coordinator=task_coordinator,
            policy_provider=knowledge_policy_provider,
        ),
        branding=AccountBrandingService(
            unit_of_work,
            mutation_executor,
        ),
    )


def _recent_pages(
    config_bus_service: ConfigBusService,
) -> Mapping[str, object]:
    snapshot = config_bus_service.get()
    value = snapshot.values.get(_RECENT_PAGES_KEY)
    if not isinstance(value, Mapping):
        raise DomainError(
            ErrorCode.INTERNAL_ERROR,
            "账号最近页面配置异常，请查看诊断日志",
            status_code=500,
            loggable=True,
            log_context={
                "operation": "accounts.resolve_recent_pages",
                "configRevision": snapshot.revision,
            },
        )
    return dict(value)


def _knowledge_policy(
    config_bus_service: ConfigBusService,
) -> KnowledgeIndexPolicy:
    snapshot = config_bus_service.get()
    try:
        return KnowledgeIndexPolicy(
            max_source_bytes=_required_int(
                snapshot.values,
                _KNOWLEDGE_MAX_SOURCE_BYTES_KEY,
            ),
            url_timeout_seconds=_required_int(
                snapshot.values,
                _KNOWLEDGE_URL_TIMEOUT_KEY,
            ),
            max_redirects=_required_int(
                snapshot.values,
                _KNOWLEDGE_MAX_REDIRECTS_KEY,
            ),
            config_revision=snapshot.revision,
        )
    except ValueError as exc:
        raise DomainError(
            ErrorCode.INTERNAL_ERROR,
            "知识索引策略配置异常，请查看诊断日志",
            status_code=500,
            loggable=True,
            log_context={
                "operation": "knowledge.resolve_index_policy",
                "configRevision": snapshot.revision,
            },
        ) from exc


def _required_int(values: Mapping[str, object], key: str) -> int:
    value = values.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"配置总线缺少有效整数配置：{key}")
    return value


def _task_snapshot_policy(
    config_bus_service: ConfigBusService,
) -> TaskSnapshotPolicy:
    snapshot = config_bus_service.get()
    try:
        return TaskSnapshotPolicy(
            max_bytes=_required_int(
                snapshot.values,
                _TASK_SNAPSHOT_MAX_BYTES_KEY,
            )
        )
    except ValueError as exc:
        raise DomainError(
            ErrorCode.INTERNAL_ERROR,
            "任务快照策略配置异常，请查看诊断日志",
            status_code=500,
            loggable=True,
            log_context={
                "operation": "knowledge.resolve_task_snapshot_policy",
                "configRevision": snapshot.revision,
            },
        ) from exc


def _reconcile_knowledge_index(
    *,
    unit_of_work: AccountUnitOfWork,
    task_repository: RuntimeTaskRepository,
    reconciler: KnowledgeIndexReconciler,
    snapshot_policy: TaskSnapshotPolicy,
    content_store: KnowledgeContentStore,
) -> KnowledgeStartupReconciliationReport:
    account_ids = _list_account_ids(unit_of_work)
    active_source_ids = _active_knowledge_source_ids(
        task_repository.list_non_terminal(),
        snapshot_policy=snapshot_policy,
    )
    referenced_sources = _list_text_source_references(
        unit_of_work,
        account_ids,
    )
    content_report = content_store.reconcile_orphaned_text_files(
        referenced_sources
    )
    index_report = reconciler.reconcile(
        account_ids,
        active_source_ids_by_account=active_source_ids,
    )
    report = KnowledgeStartupReconciliationReport(
        checked_account_count=index_report.checked_account_count,
        protected_active_source_count=(
            index_report.protected_active_source_count
        ),
        reconciled_source_count=index_report.reconciled_source_count,
        scanned_content_file_count=(
            content_report.scanned_candidate_count
        ),
        protected_content_file_count=content_report.protected_file_count,
        removed_orphan_content_file_count=(
            content_report.removed_orphan_count
        ),
    )
    log.info(
        "知识索引与正文孤儿状态对账完成",
        extra={
            "checked_account_count": report.checked_account_count,
            "protected_active_source_count": (
                report.protected_active_source_count
            ),
            "reconciled_source_count": report.reconciled_source_count,
            "scanned_content_file_count": (
                report.scanned_content_file_count
            ),
            "protected_content_file_count": (
                report.protected_content_file_count
            ),
            "removed_orphan_content_file_count": (
                report.removed_orphan_content_file_count
            ),
        },
    )
    return report
