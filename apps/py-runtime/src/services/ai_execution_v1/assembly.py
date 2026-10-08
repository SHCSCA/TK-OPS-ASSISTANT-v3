from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session, sessionmaker

from app.secret_store import SecretStore
from repositories.account_configuration_v1_repository import (
    AccountConfigurationV1Repository,
)
from repositories.account_workspace_v1_repository import (
    AccountWorkspaceV1Repository,
)
from repositories.ai_configuration_v1 import AIConfigurationV1Repository
from repositories.ai_execution_v1 import AIExecutionV1Repository
from repositories.knowledge_asset_v1_repository import (
    KnowledgeAssetV1Repository,
)
from repositories.knowledge_v1_repository import KnowledgeV1Repository
from repositories.runtime_task_repository import RuntimeTaskRepository
from services.config import ConfigBusService
from services.events import RuntimeEventService
from services.knowledge.chunk_store import KnowledgeChunkStore
from services.tasks.coordinator import TaskCoordinator
from services.tasks.handler_registry import TaskHandlerRegistry

from .content_store import AIExecutionContentStore
from .concurrency import AIExecutionConcurrencyGate
from .creation import AIExecutionCreationService
from .execution_material import AIExecutionMaterialLoader
from .execution_state import AIExecutionStateService
from .executor import AIExecutionExecutor
from .gateway import AIExecutionGateway
from .knowledge_context import KnowledgeContextResolver
from .provider_registry import AIProviderPortRegistry
from .provider_runtime import AIExecutionProviderRuntime
from .queries import AIExecutionQueryService
from .recovery import AIExecutionStartupReconciler
from .retry import AIExecutionRetryService
from .snapshot_builder import AIExecutionSnapshotBuilder
from .task_registration import register_ai_execution_handler
from .unit_of_work import AIExecutionUnitOfWork

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AIExecutionV1Services:
    gateway: AIExecutionGateway
    queries: AIExecutionQueryService
    unit_of_work: AIExecutionUnitOfWork
    recovery: AIExecutionStartupReconciler


def build_ai_execution_v1_services(
    *,
    session_factory: sessionmaker[Session],
    account_repository: AccountWorkspaceV1Repository,
    configuration_repository: AccountConfigurationV1Repository,
    ai_repository: AIConfigurationV1Repository,
    execution_repository: AIExecutionV1Repository,
    knowledge_repository: KnowledgeV1Repository,
    knowledge_asset_repository: KnowledgeAssetV1Repository,
    task_repository: RuntimeTaskRepository,
    event_service: RuntimeEventService,
    task_coordinator: TaskCoordinator,
    task_handler_registry: TaskHandlerRegistry,
    config_bus_service: ConfigBusService,
    secret_store: SecretStore,
    provider_port_registry: AIProviderPortRegistry,
    account_content_root: Path,
) -> AIExecutionV1Services:
    try:
        unit_of_work = AIExecutionUnitOfWork(
            session_factory,
            account_repository=account_repository,
            configuration_repository=configuration_repository,
            ai_repository=ai_repository,
            execution_repository=execution_repository,
            knowledge_repository=knowledge_repository,
            knowledge_asset_repository=knowledge_asset_repository,
            task_repository=task_repository,
            event_service=event_service,
        )
        content_store = AIExecutionContentStore(
            account_content_root,
            output_max_bytes=_positive_int(
                config_bus_service,
                "ai.execution.outputMaxBytes",
            ),
        )
        knowledge_context = KnowledgeContextResolver(
            KnowledgeChunkStore(account_content_root)
        )
        state = AIExecutionStateService(unit_of_work)
        queries = AIExecutionQueryService(
            unit_of_work,
            content_store=content_store,
        )
        executor = AIExecutionExecutor(
            unit_of_work,
            material_loader=AIExecutionMaterialLoader(
                content_store=content_store,
                knowledge_context=knowledge_context,
            ),
            provider_runtime=AIExecutionProviderRuntime(
                secret_store=secret_store,
                port_registry=provider_port_registry,
            ),
            state=state,
            content_store=content_store,
            concurrency_gate=AIExecutionConcurrencyGate(
                _positive_int(
                    config_bus_service,
                    "ai.execution.globalMaxConcurrency",
                )
            ),
            retry_base_delay_ms=_positive_int(
                config_bus_service,
                "ai.execution.retryBaseDelayMs",
            ),
            retry_max_delay_ms=_positive_int(
                config_bus_service,
                "ai.execution.retryMaxDelayMs",
            ),
        )
        register_ai_execution_handler(
            task_handler_registry,
            executor=executor,
        )
        recovery = AIExecutionStartupReconciler(
            unit_of_work,
            state=state,
        )
        gateway = AIExecutionGateway(
            snapshot_builder=AIExecutionSnapshotBuilder(
                unit_of_work,
                config_bus=config_bus_service,
                secret_store=secret_store,
                port_registry=provider_port_registry,
                knowledge_context=knowledge_context,
            ),
            creation=AIExecutionCreationService(
                unit_of_work,
                content_store=content_store,
                task_coordinator=task_coordinator,
            ),
            retry=AIExecutionRetryService(
                unit_of_work,
                content_store=content_store,
                task_coordinator=task_coordinator,
            ),
            queries=queries,
            state=state,
            task_coordinator=task_coordinator,
        )
        return AIExecutionV1Services(
            gateway=gateway,
            queries=queries,
            unit_of_work=unit_of_work,
            recovery=recovery,
        )
    except Exception:
        log.exception("P0-H AI 执行服务装配失败")
        raise


def _positive_int(config_bus: ConfigBusService, key: str) -> int:
    value = config_bus.get().values.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"AI 执行配置总线键 {key} 无效")
    return value


__all__ = ["AIExecutionV1Services", "build_ai_execution_v1_services"]
