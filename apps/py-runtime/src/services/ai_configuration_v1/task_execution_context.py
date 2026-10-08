from __future__ import annotations

from dataclasses import dataclass

from domain.models.ai_configuration_v1 import (
    ModelProfile,
    ModelProfileRevision,
    ProviderProfile,
    ProviderProfileRevision,
)
from errors import DomainError, ErrorCode

from .unit_of_work import AIConfigurationTransaction
from .json_codec import load_object

PROVIDER_INVALIDATIONS = (
    "providers",
    "routes",
    "recipes",
    "ai-summary",
)
MODEL_INVALIDATIONS = (
    "providers",
    "models",
    "routes",
    "recipes",
    "ai-summary",
)
CAPABILITY_INVALIDATIONS = (
    "providers",
    "models",
    "model-capabilities",
    "routes",
    "recipes",
    "ai-summary",
)


@dataclass(frozen=True, slots=True)
class ProviderExecutionConfig:
    id: str
    revision: int
    revision_id: str
    adapter_type: str
    base_url: str
    credential_ref: str | None
    timeout_seconds: float
    max_concurrency: int
    extra_params: dict[str, object]
    cost_policy: dict[str, object]


@dataclass(frozen=True, slots=True)
class ModelExecutionConfig:
    id: str
    revision: int
    revision_id: str
    model_id: str
    provider: ProviderExecutionConfig


def provider_execution_config(
    row: ProviderProfile,
    revision_row: ProviderProfileRevision,
) -> ProviderExecutionConfig:
    if revision_row.provider_profile_id != row.id:
        raise DomainError(
            ErrorCode.AI_DEPENDENCY_INVALID,
            "Provider 活动修订归属无效",
            status_code=409,
            loggable=True,
        )
    return ProviderExecutionConfig(
        id=row.id,
        revision=int(revision_row.revision),
        revision_id=revision_row.id,
        adapter_type=revision_row.adapter_type,
        base_url=revision_row.base_url,
        credential_ref=revision_row.credential_ref,
        timeout_seconds=max(float(revision_row.timeout_ms) / 1_000.0, 0.001),
        max_concurrency=int(revision_row.max_concurrency),
        extra_params=load_object(
            revision_row.extra_params_json,
            label="Provider 修订扩展参数",
        ),
        cost_policy=load_object(
            revision_row.cost_policy_json,
            label="Provider 修订成本策略",
        ),
    )


def require_provider_revision(
    transaction: AIConfigurationTransaction,
    provider: ProviderProfile,
) -> ProviderProfileRevision:
    if provider.active_revision_id is None:
        raise DomainError(
            ErrorCode.AI_DEPENDENCY_INVALID,
            "Provider 不可变修订尚未就绪",
            status_code=409,
        )
    row = transaction.ai.immutable_revisions.get_provider(
        transaction.session,
        provider.active_revision_id,
    )
    if row is None or row.provider_profile_id != provider.id:
        raise DomainError(
            ErrorCode.AI_DEPENDENCY_INVALID,
            "Provider 不可变修订已损坏",
            status_code=409,
            loggable=True,
        )
    return row


def require_model_revision(
    transaction: AIConfigurationTransaction,
    model: ModelProfile,
) -> ModelProfileRevision:
    if model.active_revision_id is None:
        raise DomainError(
            ErrorCode.AI_DEPENDENCY_INVALID,
            "模型不可变修订尚未就绪",
            status_code=409,
        )
    row = transaction.ai.immutable_revisions.get_model(
        transaction.session,
        model.active_revision_id,
    )
    if row is None or row.model_profile_id != model.id:
        raise DomainError(
            ErrorCode.AI_DEPENDENCY_INVALID,
            "模型不可变修订已损坏",
            status_code=409,
            loggable=True,
        )
    return row


def require_provider(
    transaction: AIConfigurationTransaction,
    provider_id: str,
) -> ProviderProfile:
    row = transaction.ai.providers.get(transaction.session, provider_id)
    if row is None:
        raise DomainError(
            ErrorCode.PROVIDER_NOT_FOUND,
            "Provider 不存在",
            status_code=404,
        )
    return row


def require_model(
    transaction: AIConfigurationTransaction,
    model_profile_id: str,
) -> ModelProfile:
    row = transaction.ai.models.get(
        transaction.session,
        model_profile_id,
    )
    if row is None:
        raise model_not_found()
    return row


def model_not_found() -> DomainError:
    return DomainError(
        ErrorCode.MODEL_NOT_FOUND,
        "模型不存在",
        status_code=404,
    )


def require_revision(
    current_revision: int,
    expected_revision: int,
    *,
    invalidations: tuple[str, ...],
) -> None:
    if int(current_revision) == expected_revision:
        return
    raise DomainError(
        ErrorCode.REVISION_CONFLICT,
        "AI 配置已被更新，请重新加载后重试",
        status_code=412,
        meta={
            "currentRevision": int(current_revision),
            "invalidations": list(invalidations),
        },
    )
