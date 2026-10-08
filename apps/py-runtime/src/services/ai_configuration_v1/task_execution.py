from __future__ import annotations

from collections.abc import Sequence

from app.secret_store import SecretStore
from errors import DomainError, ErrorCode
from services.tasks.types import TaskCommitCoordinator
from services.ai_execution_v1.provider_registry import AIProviderPortRegistry
from services.ai_execution_v1.types import (
    CancellationToken,
    ModelRevisionConfig,
)

from .constants import CAPABILITY_KEYS
from .provider_adapters import ProviderAdapterRegistry
from .task_adapter_results import (
    normalize_capability_probes,
    normalize_discovered_models,
)
from .task_execution_context import (
    PROVIDER_INVALIDATIONS,
)
from .task_provider_runtime import ProviderTaskRuntime
from .task_write_operations import AIConfigurationTaskWriter
from .task_real_validation import (
    capability_entry,
    contract_only_capabilities,
    discovery_entries,
    discovery_models,
    failure_entry,
    provider_error_to_domain,
    real_capability,
    require_verified_entries,
    select_health_entries,
)
from .unit_of_work import AIConfigurationUnitOfWork


class AIConfigurationTaskExecutor:
    """执行事务外 Provider 调用，并协调安全写回。"""

    def __init__(
        self,
        unit_of_work: AIConfigurationUnitOfWork,
        *,
        secret_store: SecretStore,
        adapter_registry: ProviderAdapterRegistry,
        provider_port_registry: AIProviderPortRegistry,
        validation_max_output_units: int,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._secret_store = secret_store
        self._adapter_registry = adapter_registry
        self._provider_port_registry = provider_port_registry
        self._validation_max_output_units = validation_max_output_units
        self._writer = AIConfigurationTaskWriter(unit_of_work)
        self._runtime = ProviderTaskRuntime(
            unit_of_work,
            secret_store=secret_store,
            adapter_registry=adapter_registry,
            port_registry=provider_port_registry,
        )

    def check_provider_health(
        self,
        provider_id: str,
        *,
        expected_revision: int,
        force: bool,
        stages: Sequence[str],
        cancel_token: CancellationToken,
        task_id: str,
        commit_coordinator: TaskCommitCoordinator,
    ) -> str:
        del force
        provider = self._runtime.load_provider(provider_id, expected_revision)
        commit_coordinator.raise_if_termination_won()
        validation_entries = ()
        try:
            prepared = self._runtime.resolve_port(provider)
            if prepared is None:
                adapter, connection = self._runtime.prepare_legacy(provider)
                adapter.check_health(connection)
                health_status = "degraded"
            else:
                port, revision = prepared
                result = port.health(
                    revision,
                    deadline_monotonic=self._runtime.deadline(provider),
                    cancel_token=cancel_token,
                )
                validation_entries = select_health_entries(result, stages)
                require_verified_entries(validation_entries)
                health_status = (
                    "ready" if "authentication" in stages else "degraded"
                )
        except Exception as exc:
            safe_error = provider_error_to_domain(exc)
            self._writer.write_external_failure(
                safe_error,
                provider=provider,
                task_id=task_id,
                commit_coordinator=commit_coordinator,
                validation_entries=validation_entries,
            )
        ai_revision = self._writer.write_provider_ready(
            provider,
            task_id=task_id,
            commit_coordinator=commit_coordinator,
            invalidations=PROVIDER_INVALIDATIONS,
            health_status=health_status,
            validation_entries=validation_entries,
        )
        return (
            f"provider://{provider.id}/health"
            f"?aiConfigRevision={ai_revision}"
        )

    def discover_provider_models(
        self,
        provider_id: str,
        *,
        expected_revision: int,
        replace_missing: bool,
        cancel_token: CancellationToken,
        task_id: str,
        commit_coordinator: TaskCommitCoordinator,
    ) -> str:
        if replace_missing:
            raise DomainError(
                ErrorCode.REQUEST_VALIDATION_FAILED,
                "P0 模型发现不支持替换缺失模型",
                status_code=422,
            )
        provider = self._runtime.load_provider(provider_id, expected_revision)
        commit_coordinator.raise_if_termination_won()
        validation_entries = ()
        try:
            prepared = self._runtime.resolve_port(provider)
            if prepared is None:
                adapter, connection = self._runtime.prepare_legacy(provider)
                discovered = normalize_discovered_models(
                    adapter.discover_models(connection)
                )
            else:
                port, revision = prepared
                result = port.discover_models(
                    revision,
                    page_limit=5_000,
                    deadline_monotonic=self._runtime.deadline(provider),
                    cancel_token=cancel_token,
                )
                discovered = normalize_discovered_models(
                    discovery_models(result)
                )
                validation_entries = discovery_entries(result)
                require_verified_entries(validation_entries)
        except Exception as exc:
            if not validation_entries:
                validation_entries = (failure_entry("model_discovery", exc),)
            self._writer.write_external_failure(
                provider_error_to_domain(exc),
                provider=provider,
                task_id=task_id,
                commit_coordinator=commit_coordinator,
                validation_entries=validation_entries,
            )
        ai_revision = self._writer.write_discovered_models(
            provider,
            discovered,
            task_id=task_id,
            commit_coordinator=commit_coordinator,
            validation_entries=validation_entries,
        )
        return (
            f"provider://{provider.id}/models"
            f"?aiConfigRevision={ai_revision}"
        )

    def check_model_capabilities(
        self,
        model_profile_id: str,
        *,
        expected_model_revision: int,
        expected_provider_revision: int,
        capability_keys: Sequence[str],
        force: bool,
        mode: str,
        cancel_token: CancellationToken,
        task_id: str,
        commit_coordinator: TaskCommitCoordinator,
    ) -> str:
        del force
        keys = tuple(capability_keys) or tuple(sorted(CAPABILITY_KEYS))
        model = self._runtime.load_model(
            model_profile_id,
            expected_model_revision=expected_model_revision,
            expected_provider_revision=expected_provider_revision,
        )
        commit_coordinator.raise_if_termination_won()
        validation_entries = ()
        try:
            if mode == "contract_only":
                adapter, connection = self._runtime.prepare_legacy(
                    model.provider
                )
                capabilities = contract_only_capabilities(
                    normalize_capability_probes(
                        adapter.probe_capabilities(
                            connection,
                            model_id=model.model_id,
                            capability_keys=keys,
                        ),
                        requested_keys=keys,
                    )
                )
            else:
                port, provider_revision = self._runtime.prepare_port(
                    model.provider
                )
                model_revision = ModelRevisionConfig(
                    model_profile_id=model.id,
                    model_revision_id=model.revision_id,
                    revision=model.revision,
                    model_id=model.model_id,
                    provider=provider_revision,
                )
                real_capabilities = []
                real_entries = []
                for key in keys:
                    result = port.validate_capability(
                        model_revision,
                        capability_key=key,
                        max_output_units=self._validation_max_output_units,
                        deadline_monotonic=self._runtime.deadline(
                            model.provider
                        ),
                        cancel_token=cancel_token,
                    )
                    real_capabilities.append(real_capability(result))
                    real_entries.append(capability_entry(result))
                    validation_entries = tuple(real_entries)
                capabilities = tuple(real_capabilities)
        except Exception as exc:
            if mode == "real_small_call":
                completed_keys = {
                    entry.capability_key for entry in validation_entries
                }
                failed_key = next(
                    (key for key in keys if key not in completed_keys),
                    None,
                )
                validation_entries = (
                    *validation_entries,
                    failure_entry(
                        "real_small_call",
                        exc,
                        capability_key=failed_key,
                    ),
                )
            self._writer.write_external_failure(
                provider_error_to_domain(exc),
                provider=model.provider,
                model=model,
                task_id=task_id,
                commit_coordinator=commit_coordinator,
                validation_entries=validation_entries,
            )
        ai_revision = self._writer.write_capabilities(
            model,
            capabilities,
            task_id=task_id,
            commit_coordinator=commit_coordinator,
            validation_entries=validation_entries,
        )
        return (
            f"model://{model.id}/capabilities"
            f"?aiConfigRevision={ai_revision}"
        )
