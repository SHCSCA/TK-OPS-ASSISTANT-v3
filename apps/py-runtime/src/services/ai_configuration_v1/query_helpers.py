from __future__ import annotations

from domain.models.ai_configuration_v1 import (
    CapabilityRoute,
    ModelProfile,
    ProviderProfile,
)
from errors import DomainError, ErrorCode

from .dto import model_to_dto, provider_to_dto
from .unit_of_work import AIConfigurationTransaction


def require_provider(
    transaction: AIConfigurationTransaction,
    provider_id: str,
) -> ProviderProfile:
    row = transaction.ai.providers.get(
        transaction.session,
        provider_id,
    )
    if row is None:
        raise DomainError(
            ErrorCode.PROVIDER_NOT_FOUND,
            "Provider 不存在",
            status_code=404,
        )
    return row


def provider_dto(row: ProviderProfile) -> dict[str, object]:
    return provider_to_dto(
        row,
        credential_configured=row.credential_ref is not None,
    )


def require_model(
    transaction: AIConfigurationTransaction,
    model_profile_id: str,
) -> ModelProfile:
    row = transaction.ai.models.get(
        transaction.session,
        model_profile_id,
    )
    if row is None:
        raise DomainError(
            ErrorCode.MODEL_NOT_FOUND,
            "模型不存在",
            status_code=404,
        )
    return row


def model_dto(
    transaction: AIConfigurationTransaction,
    row: ModelProfile,
) -> dict[str, object]:
    capabilities = transaction.ai.capabilities.list(
        transaction.session,
        model_profile_id=row.id,
    )
    return model_to_dto(row, capabilities)


def require_route(
    transaction: AIConfigurationTransaction,
    capability_key: str,
) -> CapabilityRoute:
    row = transaction.ai.routes.get(
        transaction.session,
        capability_key,
    )
    if row is None:
        raise DomainError(
            ErrorCode.CAPABILITY_ROUTE_INVALID,
            "能力路由尚未配置",
            status_code=422,
        )
    return row
