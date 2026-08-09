from __future__ import annotations

import logging
from datetime import UTC, datetime

from app.secret_store import SecretStore
from domain.models.ai_configuration_v1 import CapabilityRoute
from errors import DomainError, ErrorCode

from .events import append_system_ai_event
from .unit_of_work import AIConfigurationTransaction

log = logging.getLogger(__name__)


def increment_ai_revision(
    transaction: AIConfigurationTransaction,
) -> int:
    value = transaction.ai.revisions.increment_ai_config_revision(
        transaction.session
    )
    if isinstance(value, int):
        return value
    revision = getattr(value, "ai_config_revision", None)
    if isinstance(revision, int):
        return revision
    raise RuntimeError("AI 配置修订仓储返回值无效")


def provider_revision_conflict(
    current_revision: int,
    *,
    invalidations: tuple[str, ...],
) -> DomainError:
    return DomainError(
        ErrorCode.REVISION_CONFLICT,
        "AI 配置已被更新，请重新加载后再试",
        status_code=412,
        meta={
            "currentRevision": int(current_revision),
            "invalidations": list(invalidations),
        },
    )


def model_revision_conflict(
    current_revision: int,
    invalidations: tuple[str, ...],
) -> DomainError:
    return DomainError(
        ErrorCode.REVISION_CONFLICT,
        "模型配置已被更新，请重新加载后再试",
        status_code=412,
        meta={
            "currentRevision": int(current_revision),
            "invalidations": list(invalidations),
        },
    )


def route_revision_conflict(current_revision: int) -> DomainError:
    return DomainError(
        ErrorCode.REVISION_CONFLICT,
        "能力路由已被更新，请重新加载后再试",
        status_code=412,
        meta={
            "currentRevision": current_revision,
            "invalidations": ["routes"],
        },
    )


def delete_secret_safely(
    secret_store: SecretStore,
    reference: str,
) -> None:
    try:
        secret_store.delete(reference)
    except Exception:
        log.exception(
            "清理 Provider 旧凭据失败",
            extra={"credential_reference_present": True},
        )


def append_route_events(
    transaction: AIConfigurationTransaction,
    *,
    row: CapabilityRoute,
    ai_revision: int,
    invalidations: tuple[str, ...],
) -> None:
    append_system_ai_event(
        transaction,
        event_type="ai.config.changed",
        resource_type="capability_route",
        resource_id=row.id,
        revision=ai_revision,
        invalidations=invalidations,
        values={"capabilityKey": row.capability_key},
    )


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
