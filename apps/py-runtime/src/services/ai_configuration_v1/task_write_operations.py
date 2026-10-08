from __future__ import annotations

from datetime import UTC, datetime
from typing import NoReturn
from uuid import uuid4

from domain.models.ai_configuration_v1 import (
    ModelCapability,
    ModelProfile,
    ProviderProfile,
)
from errors import DomainError, ErrorCode
from services.tasks.types import TaskCommitCoordinator

from .json_codec import dump_json
from .provider_adapters import DiscoveredModel
from .task_adapter_results import (
    NormalizedCapability,
    log_safe_external_failure,
    safe_provider_error,
)
from .task_events import (
    append_task_ai_config_changed,
    append_task_ai_event,
)
from .task_execution_context import (
    CAPABILITY_INVALIDATIONS,
    MODEL_INVALIDATIONS,
    PROVIDER_INVALIDATIONS,
    ModelExecutionConfig,
    ProviderExecutionConfig,
    model_not_found,
    require_model,
    require_provider,
    require_revision,
)
from .revision_snapshots import create_model_revision
from .unit_of_work import (
    AIConfigurationTransaction,
    AIConfigurationUnitOfWork,
)
from .validation_writer import (
    ValidationEvidenceEntry,
    save_validation_entries,
)

_CAPABILITY_CONTRACT_REVISION = 1


class AIConfigurationTaskWriter:
    """在任务提交协调器保护下原子写回 AI 配置与事件。"""

    def __init__(self, unit_of_work: AIConfigurationUnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    def write_provider_ready(
        self,
        provider: ProviderExecutionConfig,
        *,
        task_id: str,
        commit_coordinator: TaskCommitCoordinator,
        invalidations: tuple[str, ...],
        health_status: str = "ready",
        validation_entries: tuple[ValidationEvidenceEntry, ...] = (),
    ) -> int:
        with self._unit_of_work.write(
            commit_coordinator=commit_coordinator
        ) as transaction:
            updated = _update_provider_health(
                transaction,
                provider,
                status=health_status,
                error_code=None,
                error_log_id=None,
            )
            save_validation_entries(
                transaction,
                provider=provider,
                model=None,
                task_id=task_id,
                entries=validation_entries,
            )
            ai_revision = transaction.ai.revisions.get(
                transaction.session
            )
            append_task_ai_event(
                transaction,
                event_type="provider.health.updated",
                resource_type="provider_profile",
                resource_id=updated.id,
                task_id=task_id,
                revision=ai_revision,
                invalidations=invalidations,
                values={"healthStatus": health_status},
            )
            return ai_revision

    def write_discovered_models(
        self,
        provider: ProviderExecutionConfig,
        discovered: tuple[DiscoveredModel, ...],
        *,
        task_id: str,
        commit_coordinator: TaskCommitCoordinator,
        validation_entries: tuple[ValidationEvidenceEntry, ...] = (),
    ) -> int:
        with self._unit_of_work.write(
            commit_coordinator=commit_coordinator
        ) as transaction:
            updated_provider = _update_provider_health(
                transaction,
                provider,
                status="ready",
                error_code=None,
                error_log_id=None,
            )
            changed_models = _upsert_discovered_models(
                transaction,
                provider_id=provider.id,
                discovered=discovered,
            )
            save_validation_entries(
                transaction,
                provider=provider,
                model=None,
                task_id=task_id,
                entries=validation_entries,
            )
            ai_revision = (
                transaction.ai.revisions.increment(transaction.session)
                if changed_models
                else transaction.ai.revisions.get(transaction.session)
            )
            append_task_ai_event(
                transaction,
                event_type="provider.health.updated",
                resource_type="provider_profile",
                resource_id=updated_provider.id,
                task_id=task_id,
                revision=ai_revision,
                invalidations=MODEL_INVALIDATIONS,
                values={"healthStatus": "ready"},
            )
            for model in changed_models:
                append_task_ai_event(
                    transaction,
                    event_type="model.updated",
                    resource_type="model_profile",
                    resource_id=model.id,
                    task_id=task_id,
                    revision=ai_revision,
                    invalidations=MODEL_INVALIDATIONS,
                )
            if changed_models:
                append_task_ai_config_changed(
                    transaction,
                    resource_type="provider_profile",
                    resource_id=provider.id,
                    task_id=task_id,
                    revision=ai_revision,
                    invalidations=MODEL_INVALIDATIONS,
                    values={
                        "discoveredCount": len(discovered),
                        "changedCount": len(changed_models),
                    },
                )
            return ai_revision

    def write_capabilities(
        self,
        model: ModelExecutionConfig,
        capabilities: tuple[NormalizedCapability, ...],
        *,
        task_id: str,
        commit_coordinator: TaskCommitCoordinator,
        validation_entries: tuple[ValidationEvidenceEntry, ...] = (),
    ) -> int:
        now = _utc_now()
        with self._unit_of_work.write(
            commit_coordinator=commit_coordinator
        ) as transaction:
            current_model = require_model(transaction, model.id)
            current_provider = require_provider(
                transaction,
                model.provider.id,
            )
            if current_model.provider_profile_id != current_provider.id:
                raise model_not_found()
            require_revision(
                current_model.revision,
                model.revision,
                invalidations=CAPABILITY_INVALIDATIONS,
            )
            updated_provider = _update_provider_health(
                transaction,
                model.provider,
                status="ready",
                error_code=None,
                error_log_id=None,
            )
            saved_with_changes = tuple(
                _save_capability(
                    transaction,
                    model_id=model.id,
                    capability=capability,
                    verified_at=now,
                )
                for capability in capabilities
            )
            save_validation_entries(
                transaction,
                provider=model.provider,
                model=model,
                task_id=task_id,
                entries=validation_entries,
            )
            saved = tuple(item[0] for item in saved_with_changes)
            capability_changed = any(
                item[1] for item in saved_with_changes
            )
            ai_revision = (
                transaction.ai.revisions.increment(transaction.session)
                if capability_changed
                else transaction.ai.revisions.get(transaction.session)
            )
            append_task_ai_event(
                transaction,
                event_type="provider.health.updated",
                resource_type="provider_profile",
                resource_id=updated_provider.id,
                task_id=task_id,
                revision=ai_revision,
                invalidations=CAPABILITY_INVALIDATIONS,
                values={"healthStatus": "ready"},
            )
            for capability in saved:
                append_task_ai_event(
                    transaction,
                    event_type="model.capability.updated",
                    resource_type="model_capability",
                    resource_id=capability.id,
                    task_id=task_id,
                    revision=ai_revision,
                    invalidations=CAPABILITY_INVALIDATIONS,
                    values={
                        "capabilityKey": capability.capability_key,
                        "contractVerified": bool(
                            capability.contract_verified
                        ),
                    },
                )
            if capability_changed:
                append_task_ai_config_changed(
                    transaction,
                    resource_type="model_profile",
                    resource_id=model.id,
                    task_id=task_id,
                    revision=ai_revision,
                    invalidations=CAPABILITY_INVALIDATIONS,
                    values={
                        "capabilityKeys": [
                            item.capability_key for item in saved
                        ]
                    },
                )
            return ai_revision

    def write_external_failure(
        self,
        error: Exception,
        *,
        provider: ProviderExecutionConfig,
        task_id: str,
        commit_coordinator: TaskCommitCoordinator,
        model: ModelExecutionConfig | None = None,
        validation_entries: tuple[ValidationEvidenceEntry, ...] = (),
    ) -> NoReturn:
        safe_error = safe_provider_error(error)
        log_id = f"log_{uuid4().hex}"
        log_safe_external_failure(
            task_id=task_id,
            provider_id=provider.id,
            model_id=None if model is None else model.id,
            error_code=safe_error.error_code,
            log_id=log_id,
        )
        with self._unit_of_work.write(
            commit_coordinator=commit_coordinator
        ) as transaction:
            if model is not None:
                current_model = require_model(transaction, model.id)
                if current_model.provider_profile_id != provider.id:
                    raise model_not_found()
                require_revision(
                    current_model.revision,
                    model.revision,
                    invalidations=CAPABILITY_INVALIDATIONS,
                )
            updated = _update_provider_health(
                transaction,
                provider,
                status="failed",
                error_code=safe_error.error_code,
                error_log_id=log_id,
            )
            save_validation_entries(
                transaction,
                provider=provider,
                model=model,
                task_id=task_id,
                entries=validation_entries,
            )
            ai_revision = transaction.ai.revisions.get(
                transaction.session
            )
            invalidations = (
                CAPABILITY_INVALIDATIONS
                if model is not None
                else PROVIDER_INVALIDATIONS
            )
            append_task_ai_event(
                transaction,
                event_type="provider.health.updated",
                resource_type="provider_profile",
                resource_id=updated.id,
                task_id=task_id,
                revision=ai_revision,
                invalidations=invalidations,
                values={
                    "healthStatus": "failed",
                    "errorCode": safe_error.error_code,
                },
                log_id=log_id,
            )
        raise safe_error from None


def _update_provider_health(
    transaction: AIConfigurationTransaction,
    provider: ProviderExecutionConfig,
    *,
    status: str,
    error_code: str | None,
    error_log_id: str | None,
) -> ProviderProfile:
    current = require_provider(transaction, provider.id)
    require_revision(
        current.revision,
        provider.revision,
        invalidations=PROVIDER_INVALIDATIONS,
    )
    now = _utc_now()
    updated = transaction.ai.providers.update_health(
        transaction.session,
        provider.id,
        expected_revision=provider.revision,
        changes={
            "health_status": status,
            "last_checked_at": now,
            "last_error_code": error_code,
            "last_error_log_id": error_log_id,
        },
        updated_at=now,
    )
    if updated is None:
        latest = require_provider(transaction, provider.id)
        require_revision(
            latest.revision,
            provider.revision,
            invalidations=PROVIDER_INVALIDATIONS,
        )
        raise RuntimeError("Provider 健康状态写回未返回结果")
    return updated


def _upsert_discovered_models(
    transaction: AIConfigurationTransaction,
    *,
    provider_id: str,
    discovered: tuple[DiscoveredModel, ...],
) -> tuple[ModelProfile, ...]:
    changed: list[ModelProfile] = []
    now = _utc_now()
    for item in discovered:
        current = transaction.ai.models.get_by_provider_model(
            transaction.session,
            provider_id=provider_id,
            model_id=item.model_id,
        )
        if current is None:
            changed.append(
                transaction.ai.models.add(
                    transaction.session,
                    ModelProfile(
                        id=f"model_{uuid4().hex}",
                        provider_profile_id=provider_id,
                        model_id=item.model_id,
                        display_name=item.display_name,
                        enabled=False,
                        discovery_source="discovered",
                        context_window=item.context_window,
                        base_limits_json=dump_json({}),
                        active_revision_id=None,
                        revision=1,
                        created_at=now,
                        updated_at=now,
                    ),
                )
            )
            create_model_revision(transaction, changed[-1])
            continue
        if current.discovery_source != "discovered":
            continue
        changes: dict[str, object] = {}
        if current.display_name != item.display_name:
            changes["display_name"] = item.display_name
        if current.context_window != item.context_window:
            changes["context_window"] = item.context_window
        if not changes:
            continue
        updated = transaction.ai.models.update(
            transaction.session,
            current.id,
            expected_revision=int(current.revision),
            changes=changes,
            updated_at=now,
        )
        if updated is None:
            raise DomainError(
                ErrorCode.REVISION_CONFLICT,
                "发现模型已被更新，请重新执行模型发现",
                status_code=412,
                meta={"invalidations": list(MODEL_INVALIDATIONS)},
            )
        create_model_revision(transaction, updated)
        changed.append(updated)
    return tuple(changed)


def _save_capability(
    transaction: AIConfigurationTransaction,
    *,
    model_id: str,
    capability: NormalizedCapability,
    verified_at: str,
) -> tuple[ModelCapability, bool]:
    current = transaction.ai.capabilities.get(
        transaction.session,
        model_profile_id=model_id,
        capability_key=capability.capability_key,
    )
    changed = _capability_semantically_changed(current, capability)
    row = ModelCapability(
        id=current.id if current is not None else f"cap_{uuid4().hex}",
        model_profile_id=model_id,
        capability_key=capability.capability_key,
        declared_supported=capability.declared_supported,
        adapter_supported=capability.adapter_supported,
        contract_verified=capability.contract_verified,
        input_modalities_json=capability.input_modalities_json,
        output_modalities_json=capability.output_modalities_json,
        parameter_schema_json=capability.parameter_schema_json,
        source_urls_json=(
            current.source_urls_json if current is not None else dump_json([])
        ),
        known_limits_json=capability.known_limits_json,
        verified_at=verified_at,
        contract_revision=_CAPABILITY_CONTRACT_REVISION,
    )
    return (
        transaction.ai.capabilities.save(transaction.session, row),
        changed,
    )


def _capability_semantically_changed(
    current: ModelCapability | None,
    capability: NormalizedCapability,
) -> bool:
    if current is None:
        return True
    return any(
        (
            current.declared_supported != capability.declared_supported,
            current.adapter_supported != capability.adapter_supported,
            current.contract_verified != capability.contract_verified,
            current.input_modalities_json != capability.input_modalities_json,
            current.output_modalities_json != capability.output_modalities_json,
            current.parameter_schema_json != capability.parameter_schema_json,
            current.known_limits_json != capability.known_limits_json,
            current.contract_revision != _CAPABILITY_CONTRACT_REVISION,
        )
    )


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
