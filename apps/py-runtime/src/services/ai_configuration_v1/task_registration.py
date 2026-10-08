from __future__ import annotations

from app.secret_store import SecretStore
from services.ai_execution_v1.provider_registry import AIProviderPortRegistry
from services.tasks.handler_registry import TaskHandlerRegistry
from services.tasks.types import (
    TaskHandler,
    TaskHandlerDefinition,
    TaskResumePolicy,
)

from .constants import (
    MODEL_CAPABILITY_CHECK_TASK_TYPE,
    PROVIDER_HEALTH_TASK_TYPE,
    PROVIDER_MODEL_DISCOVERY_TASK_TYPE,
)
from .provider_adapters import ProviderAdapterRegistry
from .task_execution import AIConfigurationTaskExecutor
from .task_handlers import (
    build_model_capability_handler,
    build_provider_health_handler,
    build_provider_model_discovery_handler,
)
from .unit_of_work import AIConfigurationUnitOfWork


def register_ai_configuration_task_handlers(
    registry: TaskHandlerRegistry,
    *,
    unit_of_work: AIConfigurationUnitOfWork,
    secret_store: SecretStore,
    adapter_registry: ProviderAdapterRegistry,
    provider_port_registry: AIProviderPortRegistry,
    validation_max_output_units: int,
    timeout_seconds: int | None = None,
) -> None:
    executor = AIConfigurationTaskExecutor(
        unit_of_work,
        secret_store=secret_store,
        adapter_registry=adapter_registry,
        provider_port_registry=provider_port_registry,
        validation_max_output_units=validation_max_output_units,
    )
    _register(
        registry,
        task_type=PROVIDER_HEALTH_TASK_TYPE,
        handler=build_provider_health_handler(executor),
        allowed_fields=frozenset(
            {"providerId", "providerRevision", "stages", "force"}
        ),
        timeout_seconds=timeout_seconds,
    )
    _register(
        registry,
        task_type=PROVIDER_MODEL_DISCOVERY_TASK_TYPE,
        handler=build_provider_model_discovery_handler(executor),
        allowed_fields=frozenset(
            {"providerId", "providerRevision", "replaceMissing"}
        ),
        timeout_seconds=timeout_seconds,
    )
    _register(
        registry,
        task_type=MODEL_CAPABILITY_CHECK_TASK_TYPE,
        handler=build_model_capability_handler(executor),
        allowed_fields=frozenset(
            {
                "modelProfileId",
                "modelRevision",
                "providerRevision",
                "capabilityKeys",
                "mode",
                "force",
            }
        ),
        timeout_seconds=timeout_seconds,
    )


def _register(
    registry: TaskHandlerRegistry,
    *,
    task_type: str,
    handler: TaskHandler,
    allowed_fields: frozenset[str],
    timeout_seconds: int | None,
) -> None:
    registry.register(
        TaskHandlerDefinition(
            task_type=task_type,
            handler=handler,
            allowed_snapshot_fields=allowed_fields,
            resume_policy=TaskResumePolicy.INTERRUPT,
            cancellable=True,
            handler_version=2,
            timeout_seconds=timeout_seconds,
            single_active_per_scope=True,
        )
    )
