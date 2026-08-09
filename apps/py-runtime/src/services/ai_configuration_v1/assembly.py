from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session, sessionmaker

from app.secret_store import SecretStore
from repositories.account_workspace_v1_repository import (
    AccountWorkspaceV1Repository,
)
from repositories.ai_configuration_v1 import AIConfigurationV1Repository
from repositories.mutation_idempotency_repository import (
    MutationIdempotencyRepository,
)
from services.accounts.idempotency import MutationIdempotencyService
from services.accounts.ports import (
    AccountAIReadinessPort,
    AIRecipeCopyPort,
)
from services.config import ConfigBusService
from services.events import RuntimeEventService
from services.tasks.coordinator import TaskCoordinator
from services.tasks.handler_registry import TaskHandlerRegistry

from .models import ModelProfileService
from .mutation import AIConfigurationMutationExecutor
from .prompts import PromptProfileService
from .provider_adapters import ProviderAdapterRegistry
from .providers import ProviderProfileService
from .recipes import (
    AccountAIReadinessAdapter,
    AccountAIRecipeService,
    AIRecipeCopyAdapter,
)
from .routes import CapabilityRouteService
from .task_registration import register_ai_configuration_task_handlers
from .templates import CompositionTemplateService
from .unit_of_work import AIConfigurationUnitOfWork

log = logging.getLogger(__name__)
_MUTATION_TTL_KEY = "api.mutationIdempotencyTtlSeconds"


@dataclass(frozen=True, slots=True)
class AIConfigurationV1Services:
    providers: ProviderProfileService
    models: ModelProfileService
    routes: CapabilityRouteService
    prompts: PromptProfileService
    templates: CompositionTemplateService
    recipes: AccountAIRecipeService
    readiness_port: AccountAIReadinessPort
    recipe_copy_port: AIRecipeCopyPort


def build_ai_configuration_v1_services(
    *,
    session_factory: sessionmaker[Session],
    repository: AIConfigurationV1Repository,
    event_service: RuntimeEventService,
    secret_store: SecretStore,
    task_coordinator: TaskCoordinator,
    task_handler_registry: TaskHandlerRegistry,
    config_bus_service: ConfigBusService,
    account_repository: AccountWorkspaceV1Repository | None = None,
    idempotency_repository: MutationIdempotencyRepository | None = None,
    adapter_registry: ProviderAdapterRegistry | None = None,
) -> AIConfigurationV1Services:
    try:
        unit_of_work = AIConfigurationUnitOfWork(
            session_factory,
            repository=repository,
            event_service=event_service,
            account_repository=account_repository,
            idempotency_repository=idempotency_repository,
        )
        idempotency_service = MutationIdempotencyService(
            unit_of_work.idempotency_repository,
            retention_seconds=lambda: _mutation_ttl(config_bus_service),
        )
        mutations = AIConfigurationMutationExecutor(
            unit_of_work,
            idempotency_service,
        )
        adapters = adapter_registry or ProviderAdapterRegistry()
        register_ai_configuration_task_handlers(
            task_handler_registry,
            unit_of_work=unit_of_work,
            secret_store=secret_store,
            adapter_registry=adapters,
        )
        return AIConfigurationV1Services(
            providers=ProviderProfileService(
                unit_of_work,
                mutations,
                secret_store=secret_store,
                task_coordinator=task_coordinator,
            ),
            models=ModelProfileService(
                unit_of_work,
                mutations,
                task_coordinator=task_coordinator,
            ),
            routes=CapabilityRouteService(unit_of_work, mutations),
            prompts=PromptProfileService(unit_of_work, mutations),
            templates=CompositionTemplateService(unit_of_work, mutations),
            recipes=AccountAIRecipeService(unit_of_work, mutations),
            readiness_port=AccountAIReadinessAdapter(repository),
            recipe_copy_port=AIRecipeCopyAdapter(repository),
        )
    except Exception:
        log.exception("P0-E AI 配置服务装配失败")
        raise


def _mutation_ttl(config_bus_service: ConfigBusService) -> int:
    value = config_bus_service.get().values.get(_MUTATION_TTL_KEY)
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 1
    ):
        raise ValueError("AI 配置幂等保留时间配置无效")
    return value

