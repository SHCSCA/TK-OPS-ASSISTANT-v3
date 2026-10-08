from __future__ import annotations

import hashlib
from uuid import uuid4

from domain.models.ai_configuration_v1 import (
    ModelProfile,
    ModelProfileRevision,
    ProviderProfile,
    ProviderProfileRevision,
)
from errors import DomainError, ErrorCode

from .json_codec import content_hash, load_object
from .mutation_helpers import utc_now
from .unit_of_work import AIConfigurationTransaction


def create_provider_revision(
    transaction: AIConfigurationTransaction,
    provider: ProviderProfile,
) -> ProviderProfileRevision:
    extra_params = load_object(
        provider.extra_params_json,
        label="Provider 扩展参数",
    )
    cost_policy = load_object(
        provider.cost_policy_json,
        label="Provider 成本策略",
    )
    row = ProviderProfileRevision(
        id=f"prev_{uuid4().hex}",
        provider_profile_id=provider.id,
        revision=int(provider.revision),
        adapter_type=provider.adapter_type,
        base_url=provider.base_url,
        base_url_hash=_hash_text(provider.base_url),
        region=provider.region,
        proxy_ref=provider.proxy_ref,
        timeout_ms=int(provider.timeout_ms),
        max_concurrency=int(provider.max_concurrency),
        extra_params_json=provider.extra_params_json,
        cost_policy_json=provider.cost_policy_json,
        credential_ref=provider.credential_ref,
        content_hash=content_hash(
            {
                "adapterType": provider.adapter_type,
                "baseUrlHash": _hash_text(provider.base_url),
                "region": provider.region,
                "proxyRef": provider.proxy_ref,
                "timeoutMs": int(provider.timeout_ms),
                "maxConcurrency": int(provider.max_concurrency),
                "extraParams": extra_params,
                "costPolicy": cost_policy,
                "credentialRefHash": _optional_hash(provider.credential_ref),
            }
        ),
        created_at=utc_now(),
    )
    transaction.ai.immutable_revisions.add_provider(
        transaction.session,
        row,
    )
    provider.active_revision_id = row.id
    transaction.session.flush([provider])
    return row


def create_model_revision(
    transaction: AIConfigurationTransaction,
    model: ModelProfile,
) -> ModelProfileRevision:
    provider = transaction.ai.providers.get(
        transaction.session,
        model.provider_profile_id,
    )
    if provider is None or provider.active_revision_id is None:
        raise DomainError(
            ErrorCode.AI_DEPENDENCY_INVALID,
            "Provider 不可变修订尚未就绪",
            status_code=409,
        )
    provider_revision = transaction.ai.immutable_revisions.get_provider(
        transaction.session,
        provider.active_revision_id,
    )
    if (
        provider_revision is None
        or provider_revision.provider_profile_id != provider.id
    ):
        raise DomainError(
            ErrorCode.AI_DEPENDENCY_INVALID,
            "Provider 不可变修订已损坏",
            status_code=409,
            loggable=True,
        )
    base_limits = load_object(
        model.base_limits_json,
        label="模型基础限制",
    )
    row = ModelProfileRevision(
        id=f"mrev_{uuid4().hex}",
        model_profile_id=model.id,
        provider_profile_revision_id=provider_revision.id,
        revision=int(model.revision),
        model_id=model.model_id,
        display_name=model.display_name,
        enabled=bool(model.enabled),
        context_window=model.context_window,
        base_limits_json=model.base_limits_json,
        content_hash=content_hash(
            {
                "providerRevisionId": provider_revision.id,
                "modelId": model.model_id,
                "displayName": model.display_name,
                "enabled": bool(model.enabled),
                "contextWindow": model.context_window,
                "baseLimits": base_limits,
            }
        ),
        created_at=utc_now(),
    )
    transaction.ai.immutable_revisions.add_model(
        transaction.session,
        row,
    )
    model.active_revision_id = row.id
    transaction.session.flush([model])
    return row


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _optional_hash(value: str | None) -> str | None:
    return None if value is None else _hash_text(value)
