from __future__ import annotations

from dataclasses import dataclass

from app.secret_store import SecretStore
from domain.models.ai_execution_evidence import AIProviderValidationRun
from domain.models.ai_execution_snapshot import AIExecutionCandidate
from errors import DomainError, ErrorCode
from services.ai_configuration_v1.json_codec import content_hash, load_object

from .provider_ports import AIProviderPort
from .provider_registry import AIProviderPortRegistry
from .types import ModelRevisionConfig, ProviderRevisionConfig
from .unit_of_work import AIExecutionTransaction


@dataclass(frozen=True, slots=True)
class FrozenCandidateRuntime:
    port: AIProviderPort
    model: ModelRevisionConfig
    cost_policy: dict[str, object]


class AIExecutionProviderRuntime:
    """只按执行候选冻结的修订读取 Provider 配置。"""

    def __init__(
        self,
        *,
        secret_store: SecretStore,
        port_registry: AIProviderPortRegistry,
    ) -> None:
        self._secret_store = secret_store
        self._ports = port_registry

    def load(
        self,
        transaction: AIExecutionTransaction,
        candidate: AIExecutionCandidate,
    ) -> FrozenCandidateRuntime:
        provider = transaction.ai.immutable_revisions.get_provider(
            transaction.session,
            candidate.provider_revision_id,
        )
        model = transaction.ai.immutable_revisions.get_model(
            transaction.session,
            candidate.model_revision_id,
        )
        validation = transaction.session.get(
            AIProviderValidationRun,
            candidate.validation_run_id,
        )
        if (
            provider is None
            or model is None
            or validation is None
            or provider.provider_profile_id != candidate.provider_profile_id
            or model.model_profile_id != candidate.model_profile_id
            or model.provider_profile_revision_id != provider.id
            or validation.provider_profile_id != candidate.provider_profile_id
            or validation.model_profile_id != candidate.model_profile_id
            or validation.status != "verified"
            or validation.stage != "real_small_call"
            or provider.adapter_type != candidate.adapter_type
            or provider.credential_ref != candidate.credential_ref
            or model.model_id != candidate.model_id
        ):
            raise _snapshot_invalid()
        safe_snapshot = {
            "ordinal": int(candidate.ordinal),
            "providerProfileId": candidate.provider_profile_id,
            "providerRevisionId": provider.id,
            "providerContentHash": provider.content_hash,
            "adapterType": provider.adapter_type,
            "modelProfileId": candidate.model_profile_id,
            "modelRevisionId": model.id,
            "modelContentHash": model.content_hash,
            "modelId": model.model_id,
            "capabilityContractRevision": int(
                candidate.capability_contract_revision
            ),
            "validationRunId": validation.id,
            "timeoutMs": int(candidate.timeout_ms),
            "maxRetries": int(candidate.max_retries),
            "maxConcurrency": int(candidate.max_concurrency),
            "maxCostMicros": int(candidate.max_cost_micros),
        }
        if content_hash(safe_snapshot) != candidate.snapshot_hash:
            raise _snapshot_invalid()
        extra_params = load_object(
            provider.extra_params_json,
            label="Provider 扩展参数",
        )
        cost_policy = load_object(
            provider.cost_policy_json,
            label="Provider 成本策略",
        )
        provider_config = ProviderRevisionConfig(
            provider_profile_id=provider.provider_profile_id,
            provider_revision_id=provider.id,
            revision=int(provider.revision),
            adapter_type=provider.adapter_type,
            base_url=provider.base_url,
            credential=self._credential(provider.credential_ref),
            timeout_seconds=int(candidate.timeout_ms) / 1_000,
            max_concurrency=int(candidate.max_concurrency),
            extra_params=extra_params,
            cost_policy=cost_policy,
        )
        return FrozenCandidateRuntime(
            port=self._ports.require(provider.adapter_type),
            model=ModelRevisionConfig(
                model_profile_id=model.model_profile_id,
                model_revision_id=model.id,
                revision=int(model.revision),
                model_id=model.model_id,
                provider=provider_config,
            ),
            cost_policy=cost_policy,
        )

    def _credential(self, reference: str | None) -> str | None:
        if reference is None:
            return None
        try:
            value = self._secret_store.get(reference)
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
                "Provider 凭据引用已失效，请重新配置",
                status_code=503,
            )
        return value


def _snapshot_invalid() -> DomainError:
    return DomainError(
        ErrorCode.AI_DEPENDENCY_INVALID,
        "AI 执行候选快照完整性校验失败",
        status_code=409,
        loggable=True,
    )


__all__ = ["AIExecutionProviderRuntime", "FrozenCandidateRuntime"]
