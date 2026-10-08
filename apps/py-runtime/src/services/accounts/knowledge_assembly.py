from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from errors import DomainError, ErrorCode
from services.accounts.lifecycle_sync import AccountLifecycleSynchronizer
from services.accounts.unit_of_work import (
    AccountMutationExecutor,
    AccountUnitOfWork,
)
from services.config import ConfigBusService
from services.execution_environments.workspace_root_resolver import (
    WorkspaceRootResolver,
)
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
from services.knowledge.chunk_store import KnowledgeChunkStore
from services.knowledge.controlled_files import (
    RegistryControlledFileResolver,
)
from services.knowledge.ports import ControlledFileResolver
from services.tasks.coordinator import TaskCoordinator
from services.tasks.handler_registry import TaskHandlerRegistry

_MAX_SOURCE_BYTES_KEY = "knowledge.index.maxSourceBytes"
_URL_TIMEOUT_KEY = "knowledge.index.urlTimeoutSeconds"
_MAX_REDIRECTS_KEY = "knowledge.index.maxRedirects"
_CONTROLLED_MAX_BYTES_KEY = "knowledge.controlledFiles.maxBytes"


@dataclass(frozen=True, slots=True)
class AccountKnowledgeServices:
    content_store: KnowledgeContentStore
    index_reconciler: KnowledgeIndexReconciler
    index_submission: KnowledgeIndexSubmissionService
    service: AccountKnowledgeService


def build_account_knowledge_services(
    *,
    unit_of_work: AccountUnitOfWork,
    mutation_executor: AccountMutationExecutor,
    lifecycle_synchronizer: AccountLifecycleSynchronizer,
    config_bus_service: ConfigBusService,
    task_coordinator: TaskCoordinator,
    task_handler_registry: TaskHandlerRegistry,
    knowledge_content_root: Path,
    controlled_file_registry_path: Path | None,
    workspace_root_registry_path: Path | None,
) -> AccountKnowledgeServices:
    content_store = KnowledgeContentStore(knowledge_content_root)
    chunk_store = KnowledgeChunkStore(knowledge_content_root)
    policy_provider = lambda: knowledge_policy(config_bus_service)
    controlled_files = _controlled_file_resolver(
        controlled_file_registry_path,
        workspace_root_registry_path,
    )
    executor = KnowledgeIndexExecutor(
        unit_of_work,
        content_store=content_store,
        chunk_store=chunk_store,
        controlled_file_resolver=controlled_files,
        url_fetcher=SecureKnowledgeUrlFetcher(),
        lifecycle_synchronizer=lifecycle_synchronizer,
        policy_provider=policy_provider,
    )
    register_knowledge_index_handler(
        task_handler_registry,
        executor=executor,
    )
    return AccountKnowledgeServices(
        content_store=content_store,
        index_reconciler=KnowledgeIndexReconciler(
            unit_of_work,
            policy_provider=policy_provider,
            lifecycle_synchronizer=lifecycle_synchronizer,
        ),
        index_submission=KnowledgeIndexSubmissionService(
            unit_of_work,
            coordinator=task_coordinator,
            policy_provider=policy_provider,
        ),
        service=AccountKnowledgeService(
            unit_of_work,
            mutation_executor,
            content_store=content_store,
            controlled_file_resolver=controlled_files,
            controlled_file_max_bytes=lambda: _required_int(
                config_bus_service.get().values,
                _CONTROLLED_MAX_BYTES_KEY,
            ),
            lifecycle_synchronizer=lifecycle_synchronizer,
        ),
    )


def knowledge_policy(
    config_bus_service: ConfigBusService,
) -> KnowledgeIndexPolicy:
    snapshot = config_bus_service.get()
    try:
        return KnowledgeIndexPolicy(
            max_source_bytes=min(
                _required_int(snapshot.values, _MAX_SOURCE_BYTES_KEY),
                _required_int(snapshot.values, _CONTROLLED_MAX_BYTES_KEY),
            ),
            url_timeout_seconds=_required_int(
                snapshot.values,
                _URL_TIMEOUT_KEY,
            ),
            max_redirects=_required_int(
                snapshot.values,
                _MAX_REDIRECTS_KEY,
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


def _controlled_file_resolver(
    registry_path: Path | None,
    workspace_registry_path: Path | None,
) -> ControlledFileResolver:
    if registry_path is None or workspace_registry_path is None:
        return UnavailableControlledFileResolver()
    return RegistryControlledFileResolver(
        registry_path,
        workspace_roots=WorkspaceRootResolver(workspace_registry_path),
    )


def _required_int(values: Mapping[str, object], key: str) -> int:
    value = values.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"配置总线缺少有效整数配置：{key}")
    return value
