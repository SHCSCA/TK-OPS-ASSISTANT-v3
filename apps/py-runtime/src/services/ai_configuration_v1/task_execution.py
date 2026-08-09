from __future__ import annotations

from collections.abc import Sequence

from app.secret_store import SecretStore
from errors import DomainError, ErrorCode
from services.tasks.types import TaskCommitCoordinator

from .constants import CAPABILITY_KEYS
from .provider_adapters import (
    ProviderAdapter,
    ProviderAdapterRegistry,
    ProviderConnection,
)
from .task_adapter_results import (
    normalize_capability_probes,
    normalize_discovered_models,
)
from .task_execution_context import (
    CAPABILITY_INVALIDATIONS,
    PROVIDER_INVALIDATIONS,
    ModelExecutionConfig,
    ProviderExecutionConfig,
    provider_execution_config,
    require_model,
    require_provider,
    require_revision,
)
from .task_write_operations import AIConfigurationTaskWriter
from .unit_of_work import AIConfigurationUnitOfWork


class AIConfigurationTaskExecutor:
    """执行事务外 Provider 调用，并协调安全写回。"""

    def __init__(
        self,
        unit_of_work: AIConfigurationUnitOfWork,
        *,
        secret_store: SecretStore,
        adapter_registry: ProviderAdapterRegistry,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._secret_store = secret_store
        self._adapter_registry = adapter_registry
        self._writer = AIConfigurationTaskWriter(unit_of_work)

    def check_provider_health(
        self,
        provider_id: str,
        *,
        expected_revision: int,
        force: bool,
        task_id: str,
        commit_coordinator: TaskCommitCoordinator,
    ) -> str:
        del force
        provider = self._load_provider(provider_id, expected_revision)
        commit_coordinator.raise_if_termination_won()
        try:
            adapter, connection = self._prepare_external_call(provider)
            adapter.check_health(connection)
        except Exception as exc:
            self._writer.write_external_failure(
                exc,
                provider=provider,
                task_id=task_id,
                commit_coordinator=commit_coordinator,
            )
        ai_revision = self._writer.write_provider_ready(
            provider,
            task_id=task_id,
            commit_coordinator=commit_coordinator,
            invalidations=PROVIDER_INVALIDATIONS,
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
        task_id: str,
        commit_coordinator: TaskCommitCoordinator,
    ) -> str:
        if replace_missing:
            raise DomainError(
                ErrorCode.REQUEST_VALIDATION_FAILED,
                "P0 模型发现不支持替换缺失模型",
                status_code=422,
            )
        provider = self._load_provider(provider_id, expected_revision)
        commit_coordinator.raise_if_termination_won()
        try:
            adapter, connection = self._prepare_external_call(provider)
            discovered = normalize_discovered_models(
                adapter.discover_models(connection)
            )
        except Exception as exc:
            self._writer.write_external_failure(
                exc,
                provider=provider,
                task_id=task_id,
                commit_coordinator=commit_coordinator,
            )
        ai_revision = self._writer.write_discovered_models(
            provider,
            discovered,
            task_id=task_id,
            commit_coordinator=commit_coordinator,
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
        task_id: str,
        commit_coordinator: TaskCommitCoordinator,
    ) -> str:
        del force
        keys = tuple(capability_keys) or tuple(sorted(CAPABILITY_KEYS))
        model = self._load_model(
            model_profile_id,
            expected_model_revision=expected_model_revision,
            expected_provider_revision=expected_provider_revision,
        )
        commit_coordinator.raise_if_termination_won()
        try:
            adapter, connection = self._prepare_external_call(model.provider)
            capabilities = normalize_capability_probes(
                adapter.probe_capabilities(
                    connection,
                    model_id=model.model_id,
                    capability_keys=keys,
                ),
                requested_keys=keys,
            )
        except Exception as exc:
            self._writer.write_external_failure(
                exc,
                provider=model.provider,
                model=model,
                task_id=task_id,
                commit_coordinator=commit_coordinator,
            )
        ai_revision = self._writer.write_capabilities(
            model,
            capabilities,
            task_id=task_id,
            commit_coordinator=commit_coordinator,
        )
        return (
            f"model://{model.id}/capabilities"
            f"?aiConfigRevision={ai_revision}"
        )

    def _load_provider(
        self,
        provider_id: str,
        expected_revision: int,
    ) -> ProviderExecutionConfig:
        with self._unit_of_work.read() as transaction:
            row = require_provider(transaction, provider_id)
            require_revision(
                row.revision,
                expected_revision,
                invalidations=PROVIDER_INVALIDATIONS,
            )
            return provider_execution_config(row)

    def _load_model(
        self,
        model_profile_id: str,
        *,
        expected_model_revision: int,
        expected_provider_revision: int,
    ) -> ModelExecutionConfig:
        with self._unit_of_work.read() as transaction:
            row = require_model(transaction, model_profile_id)
            provider = require_provider(
                transaction,
                row.provider_profile_id,
            )
            require_revision(
                row.revision,
                expected_model_revision,
                invalidations=CAPABILITY_INVALIDATIONS,
            )
            require_revision(
                provider.revision,
                expected_provider_revision,
                invalidations=CAPABILITY_INVALIDATIONS,
            )
            return ModelExecutionConfig(
                id=row.id,
                revision=int(row.revision),
                model_id=row.model_id,
                provider=provider_execution_config(provider),
            )

    def _prepare_external_call(
        self,
        provider: ProviderExecutionConfig,
    ) -> tuple[ProviderAdapter, ProviderConnection]:
        adapter = self._adapter_registry.require(provider.adapter_type)
        credential: str | None = None
        if provider.credential_ref is not None:
            try:
                credential = self._secret_store.get(
                    provider.credential_ref
                )
            except Exception as exc:
                raise DomainError(
                    ErrorCode.PROVIDER_SECRET_UNAVAILABLE,
                    "Provider 凭据暂不可用",
                    status_code=503,
                    loggable=True,
                ) from exc
            if not credential:
                raise DomainError(
                    ErrorCode.PROVIDER_SECRET_UNAVAILABLE,
                    "Provider 凭据引用已失效，请重新设置",
                    status_code=503,
                )
        return (
            adapter,
            ProviderConnection(
                adapter_type=provider.adapter_type,
                base_url=provider.base_url,
                credential=credential,
                timeout_seconds=provider.timeout_seconds,
            ),
        )
