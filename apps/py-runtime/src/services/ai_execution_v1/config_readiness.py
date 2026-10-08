from __future__ import annotations

from sqlalchemy.orm import Session

from repositories.ai_configuration_v1 import AIConfigurationV1Repository
from services.ai_configuration_v1.unit_of_work import AIConfigurationTransaction


def model_dependency_issue(
    transaction: AIConfigurationTransaction,
    *,
    model_id: str,
    capability_key: str,
) -> str | None:
    """检查模型当前不可变修订是否具有可执行的真实验证证据。"""
    return model_dependency_issue_for_repository(
        transaction.ai,
        transaction.session,
        model_id=model_id,
        capability_key=capability_key,
    )


def model_dependency_issue_for_repository(
    repository: AIConfigurationV1Repository,
    session: Session,
    *,
    model_id: str,
    capability_key: str,
) -> str | None:
    model = repository.models.get(session, model_id)
    if model is None or not model.enabled or model.active_revision_id is None:
        return "AI_MODEL_DISABLED"
    model_revision = repository.immutable_revisions.get_model(
        session,
        model.active_revision_id,
    )
    if model_revision is None or not model_revision.enabled:
        return "AI_MODEL_DISABLED"
    provider = repository.providers.get(
        session,
        model.provider_profile_id,
    )
    if (
        provider is None
        or not provider.enabled
        or provider.active_revision_id is None
    ):
        return "AI_PROVIDER_DISABLED"
    provider_revision = repository.immutable_revisions.get_provider(
        session,
        provider.active_revision_id,
    )
    if (
        provider_revision is None
        or model_revision.provider_profile_revision_id
        != provider_revision.id
    ):
        return "AI_PROVIDER_REAL_VALIDATION_REQUIRED"
    capability = repository.capabilities.get(
        session,
        model_profile_id=model_id,
        capability_key=capability_key,
    )
    if (
        capability is None
        or not capability.declared_supported
        or not capability.adapter_supported
        or not capability.contract_verified
    ):
        return "AI_MODEL_CAPABILITY_UNVERIFIED"
    validation = repository.validation_runs.latest_verified_capability(
        session,
        provider_profile_id=provider.id,
        provider_revision=int(provider_revision.revision),
        model_profile_id=model.id,
        model_revision=int(model_revision.revision),
        capability_key=capability_key,
    )
    if validation is None:
        return "AI_PROVIDER_REAL_VALIDATION_REQUIRED"
    return None


__all__ = [
    "model_dependency_issue",
    "model_dependency_issue_for_repository",
]
