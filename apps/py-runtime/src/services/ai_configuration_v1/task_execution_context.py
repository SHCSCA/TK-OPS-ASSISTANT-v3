from __future__ import annotations

from dataclasses import dataclass

from domain.models.ai_configuration_v1 import (
    ModelProfile,
    ProviderProfile,
)
from errors import DomainError, ErrorCode

from .unit_of_work import AIConfigurationTransaction

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
    adapter_type: str
    base_url: str
    credential_ref: str | None
    timeout_seconds: float


@dataclass(frozen=True, slots=True)
class ModelExecutionConfig:
    id: str
    revision: int
    model_id: str
    provider: ProviderExecutionConfig


def provider_execution_config(
    row: ProviderProfile,
) -> ProviderExecutionConfig:
    return ProviderExecutionConfig(
        id=row.id,
        revision=int(row.revision),
        adapter_type=row.adapter_type,
        base_url=row.base_url,
        credential_ref=row.credential_ref,
        timeout_seconds=max(float(row.timeout_ms) / 1_000.0, 0.001),
    )


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
