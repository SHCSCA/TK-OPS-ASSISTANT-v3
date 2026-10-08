from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.secret_store import SecretStore
from domain.models.ai_configuration_v1 import (
    ModelProfileRevision,
    ProviderProfileRevision,
)
from domain.models.ai_execution_evidence import AIProviderValidationRun
from errors import DomainError, ErrorCode
from services.ai_configuration_v1.json_codec import load_object

from .provider_registry import AIProviderPortRegistry
from .unit_of_work import AIExecutionTransaction


@dataclass(frozen=True, slots=True)
class ResolvedCandidate:
    ordinal: int
    provider_profile_id: str
    provider_revision: ProviderProfileRevision
    model_profile_id: str
    model_revision: ModelProfileRevision
    capability_contract_revision: int
    validation: AIProviderValidationRun
    timeout_ms: int
    max_retries: int
    max_concurrency: int
    max_cost_micros: int
    retry_policy: dict[str, Any]
    extra_params: dict[str, Any]
    cost_policy: dict[str, Any]

    def safe_snapshot(self) -> dict[str, object]:
        return {
            "ordinal": self.ordinal,
            "providerProfileId": self.provider_profile_id,
            "providerRevisionId": self.provider_revision.id,
            "providerContentHash": self.provider_revision.content_hash,
            "adapterType": self.provider_revision.adapter_type,
            "modelProfileId": self.model_profile_id,
            "modelRevisionId": self.model_revision.id,
            "modelContentHash": self.model_revision.content_hash,
            "modelId": self.model_revision.model_id,
            "capabilityContractRevision": self.capability_contract_revision,
            "validationRunId": self.validation.id,
            "timeoutMs": self.timeout_ms,
            "maxRetries": self.max_retries,
            "maxConcurrency": self.max_concurrency,
            "maxCostMicros": self.max_cost_micros,
        }


def resolve_candidates(
    transaction: AIExecutionTransaction,
    *,
    capability_key: str,
    model_ids: tuple[str, ...],
    route_timeout_ms: int,
    route_max_retries: int,
    route_max_concurrency: int,
    route_max_cost_micros: int,
    retry_policy: dict[str, Any],
    global_max_concurrency: int,
    allow_fallback: bool,
    secret_store: SecretStore,
    port_registry: AIProviderPortRegistry,
) -> tuple[ResolvedCandidate, ...]:
    selected = model_ids if allow_fallback else model_ids[:1]
    candidates = tuple(
        _resolve_candidate(
            transaction,
            capability_key=capability_key,
            model_id=model_id,
            ordinal=ordinal,
            route_timeout_ms=route_timeout_ms,
            route_max_retries=route_max_retries,
            route_max_concurrency=route_max_concurrency,
            route_max_cost_micros=route_max_cost_micros,
            retry_policy=retry_policy,
            global_max_concurrency=global_max_concurrency,
            secret_store=secret_store,
            port_registry=port_registry,
        )
        for ordinal, model_id in enumerate(selected)
    )
    if not candidates:
        raise DomainError(
            ErrorCode.AI_ROUTE_INCOMPLETE,
            "当前能力路由没有可执行候选模型",
            status_code=409,
        )
    return candidates


def _resolve_candidate(
    transaction: AIExecutionTransaction,
    *,
    capability_key: str,
    model_id: str,
    ordinal: int,
    route_timeout_ms: int,
    route_max_retries: int,
    route_max_concurrency: int,
    route_max_cost_micros: int,
    retry_policy: dict[str, Any],
    global_max_concurrency: int,
    secret_store: SecretStore,
    port_registry: AIProviderPortRegistry,
) -> ResolvedCandidate:
    model = transaction.ai.models.get(transaction.session, model_id)
    if model is None or not model.enabled or model.active_revision_id is None:
        raise _dependency_error(ErrorCode.AI_MODEL_DISABLED)
    model_revision = transaction.ai.immutable_revisions.get_model(
        transaction.session,
        model.active_revision_id,
    )
    if model_revision is None or not model_revision.enabled:
        raise _dependency_error(ErrorCode.AI_MODEL_DISABLED)
    provider = transaction.ai.providers.get(
        transaction.session,
        model.provider_profile_id,
    )
    if (
        provider is None
        or not provider.enabled
        or provider.active_revision_id is None
    ):
        raise _dependency_error(ErrorCode.AI_PROVIDER_DISABLED)
    provider_revision = transaction.ai.immutable_revisions.get_provider(
        transaction.session,
        provider.active_revision_id,
    )
    if (
        provider_revision is None
        or model_revision.provider_profile_revision_id != provider_revision.id
    ):
        raise _dependency_error(ErrorCode.AI_PROVIDER_REAL_VALIDATION_REQUIRED)
    capability = transaction.ai.capabilities.get(
        transaction.session,
        model_profile_id=model.id,
        capability_key=capability_key,
    )
    validation = transaction.ai.validation_runs.latest_verified_capability(
        transaction.session,
        provider_profile_id=provider.id,
        provider_revision=int(provider_revision.revision),
        model_profile_id=model.id,
        model_revision=int(model_revision.revision),
        capability_key=capability_key,
    )
    if (
        capability is None
        or not capability.declared_supported
        or not capability.adapter_supported
        or not capability.contract_verified
        or validation is None
    ):
        raise _dependency_error(ErrorCode.AI_PROVIDER_REAL_VALIDATION_REQUIRED)
    port_registry.require(provider_revision.adapter_type)
    _require_credential(provider_revision, secret_store)
    return ResolvedCandidate(
        ordinal=ordinal,
        provider_profile_id=provider.id,
        provider_revision=provider_revision,
        model_profile_id=model.id,
        model_revision=model_revision,
        capability_contract_revision=int(capability.contract_revision),
        validation=validation,
        timeout_ms=min(route_timeout_ms, int(provider_revision.timeout_ms)),
        max_retries=route_max_retries,
        max_concurrency=min(
            global_max_concurrency,
            route_max_concurrency,
            int(provider_revision.max_concurrency),
        ),
        max_cost_micros=route_max_cost_micros,
        retry_policy=retry_policy,
        extra_params=load_object(
            provider_revision.extra_params_json,
            label="Provider 扩展参数",
        ),
        cost_policy=load_object(
            provider_revision.cost_policy_json,
            label="Provider 成本策略",
        ),
    )


def _require_credential(
    revision: ProviderProfileRevision,
    secret_store: SecretStore,
) -> None:
    if revision.credential_ref is None:
        return
    try:
        value = secret_store.get(revision.credential_ref)
    except Exception as exc:
        raise DomainError(
            ErrorCode.PROVIDER_SECRET_UNAVAILABLE,
            "Provider 凭据暂不可用",
            status_code=503,
            loggable=True,
        ) from exc
    if not value:
        raise DomainError(
            ErrorCode.PROVIDER_SECRET_UNAVAILABLE,
            "Provider 凭据引用已失效，请重新设置",
            status_code=503,
        )


def _dependency_error(code: ErrorCode) -> DomainError:
    messages = {
        ErrorCode.AI_MODEL_DISABLED: "候选模型未启用或修订缺失",
        ErrorCode.AI_PROVIDER_DISABLED: "候选 Provider 未启用或修订缺失",
        ErrorCode.AI_PROVIDER_REAL_VALIDATION_REQUIRED: (
            "候选模型尚未通过当前修订的真实小调用"
        ),
    }
    return DomainError(
        code,
        messages[code],
        status_code=409,
        meta={"repairActions": [{"kind": "navigate", "targetPage": "ai-system-settings"}]},
    )


__all__ = ["ResolvedCandidate", "resolve_candidates"]
