from __future__ import annotations

from collections.abc import Mapping

from errors import DomainError, ErrorCode

from .dto import route_to_dto
from .query_helpers import (
    model_dto,
    provider_dto,
    require_model,
    require_provider,
)
from .unit_of_work import AIConfigurationTransaction


def load_provider_replay(
    transaction: AIConfigurationTransaction,
    resource_type: str,
    resource_id: str,
) -> Mapping[str, object]:
    if resource_type != "provider_profile":
        raise DomainError(
            ErrorCode.INTERNAL_ERROR,
            "Provider 幂等记录资源类型异常",
            status_code=500,
            loggable=True,
        )
    return provider_dto(require_provider(transaction, resource_id))


def load_model_replay(
    transaction: AIConfigurationTransaction,
    resource_type: str,
    resource_id: str,
) -> Mapping[str, object]:
    if resource_type != "model_profile":
        raise DomainError(
            ErrorCode.INTERNAL_ERROR,
            "模型幂等记录资源类型异常",
            status_code=500,
            loggable=True,
        )
    return model_dto(
        transaction,
        require_model(transaction, resource_id),
    )


def load_route_replay(
    transaction: AIConfigurationTransaction,
    resource_type: str,
    resource_id: str,
) -> Mapping[str, object]:
    if resource_type != "capability_route":
        raise DomainError(
            ErrorCode.INTERNAL_ERROR,
            "能力路由幂等记录资源类型异常",
            status_code=500,
            loggable=True,
        )
    rows = transaction.ai.routes.list(transaction.session)
    row = next((item for item in rows if item.id == resource_id), None)
    if row is None:
        raise DomainError(
            ErrorCode.CAPABILITY_ROUTE_INVALID,
            "能力路由幂等资源已不存在",
            status_code=422,
        )
    return route_to_dto(row)
