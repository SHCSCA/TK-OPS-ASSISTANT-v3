from __future__ import annotations

import time

from app.secret_store import SecretStore
from errors import DomainError, ErrorCode
from services.ai_execution_v1.provider_ports import AIProviderPort
from services.ai_execution_v1.provider_registry import AIProviderPortRegistry
from services.ai_execution_v1.types import ProviderRevisionConfig

from .provider_adapters import (
    ProviderAdapter,
    ProviderAdapterRegistry,
    ProviderConnection,
)
from .task_execution_context import (
    CAPABILITY_INVALIDATIONS,
    PROVIDER_INVALIDATIONS,
    ModelExecutionConfig,
    ProviderExecutionConfig,
    provider_execution_config,
    require_model,
    require_model_revision,
    require_provider,
    require_provider_revision,
    require_revision,
)
from .unit_of_work import AIConfigurationUnitOfWork


class ProviderTaskRuntime:
    """解析不可变配置，并在事务外准备 Provider 调用。"""

    def __init__(
        self,
        unit_of_work: AIConfigurationUnitOfWork,
        *,
        secret_store: SecretStore,
        adapter_registry: ProviderAdapterRegistry,
        port_registry: AIProviderPortRegistry,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._secret_store = secret_store
        self._adapter_registry = adapter_registry
        self._port_registry = port_registry

    def load_provider(
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
            revision_row = require_provider_revision(transaction, row)
            require_revision(
                revision_row.revision,
                expected_revision,
                invalidations=PROVIDER_INVALIDATIONS,
            )
            return provider_execution_config(row, revision_row)

    def load_model(
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
            model_revision = require_model_revision(transaction, row)
            provider_revision = require_provider_revision(
                transaction,
                provider,
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
            require_revision(
                model_revision.revision,
                expected_model_revision,
                invalidations=CAPABILITY_INVALIDATIONS,
            )
            require_revision(
                provider_revision.revision,
                expected_provider_revision,
                invalidations=CAPABILITY_INVALIDATIONS,
            )
            if (
                model_revision.provider_profile_revision_id
                != provider_revision.id
            ):
                raise DomainError(
                    ErrorCode.AI_DEPENDENCY_INVALID,
                    "模型与 Provider 不可变修订不一致",
                    status_code=409,
                )
            return ModelExecutionConfig(
                id=row.id,
                revision=int(row.revision),
                revision_id=model_revision.id,
                model_id=row.model_id,
                provider=provider_execution_config(
                    provider,
                    provider_revision,
                ),
            )

    def prepare_legacy(
        self,
        provider: ProviderExecutionConfig,
    ) -> tuple[ProviderAdapter, ProviderConnection]:
        adapter = self._adapter_registry.require(provider.adapter_type)
        return (
            adapter,
            ProviderConnection(
                adapter_type=provider.adapter_type,
                base_url=provider.base_url,
                credential=self._resolve_credential(provider),
                timeout_seconds=provider.timeout_seconds,
            ),
        )

    def prepare_port(
        self,
        provider: ProviderExecutionConfig,
    ) -> tuple[AIProviderPort, ProviderRevisionConfig]:
        port = self._port_registry.require(provider.adapter_type)
        return port, self._revision_config(provider)

    def resolve_port(
        self,
        provider: ProviderExecutionConfig,
    ) -> tuple[AIProviderPort, ProviderRevisionConfig] | None:
        if self._port_registry.resolve(provider.adapter_type) is None:
            return None
        return self.prepare_port(provider)

    @staticmethod
    def deadline(provider: ProviderExecutionConfig) -> float:
        return time.monotonic() + provider.timeout_seconds

    def _revision_config(
        self,
        provider: ProviderExecutionConfig,
    ) -> ProviderRevisionConfig:
        return ProviderRevisionConfig(
            provider_profile_id=provider.id,
            provider_revision_id=provider.revision_id,
            revision=provider.revision,
            adapter_type=provider.adapter_type,
            base_url=provider.base_url,
            credential=self._resolve_credential(provider),
            timeout_seconds=provider.timeout_seconds,
            max_concurrency=provider.max_concurrency,
            extra_params=provider.extra_params,
            cost_policy=provider.cost_policy,
        )

    def _resolve_credential(
        self,
        provider: ProviderExecutionConfig,
    ) -> str | None:
        if provider.credential_ref is None:
            return None
        try:
            credential = self._secret_store.get(provider.credential_ref)
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
        return credential


__all__ = ["ProviderTaskRuntime"]
