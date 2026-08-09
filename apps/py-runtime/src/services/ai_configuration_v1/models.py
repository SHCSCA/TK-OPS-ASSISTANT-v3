from __future__ import annotations

from collections.abc import Mapping
from uuid import uuid4

from common.pagination import CursorPosition
from domain.models.ai_configuration_v1 import ModelProfile
from errors import DomainError, ErrorCode
from services.accounts.idempotency import MutationCommand
from services.tasks.coordinator import TaskCoordinator
from services.tasks.types import RuntimeTaskRecord

from .constants import MODEL_CAPABILITY_CHECK_TASK_TYPE
from .dto import capability_to_dto
from .events import append_system_ai_event
from .json_codec import dump_json
from .mutation import (
    AIConfigurationMutationExecutor,
    AIResourceMutation,
)
from .mutation_helpers import (
    model_revision_conflict as _revision_conflict,
    utc_now as _utc_now,
)
from .pagination_helpers import (
    model_capability_page as _dict_page,
    model_page as _model_page,
)
from .profile_normalization import (
    normalize_model_create as _normalize_model_create,
    normalize_model_patch as _normalize_model_patch,
)
from .query_helpers import (
    model_dto as _model_dto,
    require_model as _require_model,
    require_provider as _require_provider,
)
from .replay_helpers import load_model_replay as _load_model_replay
from .unit_of_work import (
    AIConfigurationTransaction,
    AIConfigurationUnitOfWork,
)
from .validation import (
    require_capability_key,
    require_capability_keys,
)


class ModelProfileService:
    def __init__(
        self,
        unit_of_work: AIConfigurationUnitOfWork,
        mutations: AIConfigurationMutationExecutor,
        *,
        task_coordinator: TaskCoordinator,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._mutations = mutations
        self._task_coordinator = task_coordinator

    def list_models(
        self,
        *,
        provider_id: str | None = None,
        enabled: bool | None = None,
        capability_key: str | None = None,
        cursor: CursorPosition | None = None,
        limit: int = 50,
    ) -> tuple[dict[str, object], CursorPosition | None]:
        if capability_key is not None:
            require_capability_key(capability_key)
        with self._unit_of_work.read() as transaction:
            if provider_id is not None:
                _require_provider(transaction, provider_id)
            rows = transaction.ai.models.list(
                transaction.session,
                provider_id=provider_id,
                enabled=enabled,
                capability_key=capability_key,
            )
            page, next_position = _model_page(rows, cursor, limit)
            return (
                {
                    "items": [
                        _model_dto(transaction, row)
                        for row in page
                    ],
                    "totalKnown": len(rows),
                },
                next_position,
            )

    def get_model(self, model_profile_id: str) -> dict[str, object]:
        with self._unit_of_work.read() as transaction:
            return _model_dto(
                transaction,
                _require_model(transaction, model_profile_id),
            )

    def create_model(
        self,
        payload: Mapping[str, object],
        *,
        idempotency_key: str,
        request_id: str,
        operation_id: str,
    ) -> AIResourceMutation:
        del request_id, operation_id
        normalized = _normalize_model_create(payload)
        command = MutationCommand(
            account_id=None,
            operation_name="ai.model.create",
            idempotency_key=idempotency_key,
            request_payload=normalized,
        )
        return self._mutations.execute(
            command,
            work=lambda transaction: self._create_model(
                transaction,
                normalized,
            ),
            replay_loader=_load_model_replay,
        )

    def update_model(
        self,
        model_profile_id: str,
        payload: Mapping[str, object],
        *,
        expected_revision: int,
        request_id: str,
        operation_id: str,
    ) -> dict[str, object]:
        del request_id, operation_id
        changes = _normalize_model_patch(payload)
        with self._unit_of_work.write() as transaction:
            current = _require_model(transaction, model_profile_id)
            if changes.get("enabled") is False:
                references = transaction.ai.routes.list_referencing_model(
                    transaction.session,
                    model_profile_id,
                )
                if any(route.enabled for route in references):
                    raise DomainError(
                        ErrorCode.MODEL_IN_USE,
                        "模型仍被启用的能力路由引用",
                        status_code=409,
                        meta={
                            "capabilityKeys": [
                                route.capability_key
                                for route in references
                                if route.enabled
                            ]
                        },
                    )
            updated = transaction.ai.models.update(
                transaction.session,
                model_profile_id,
                expected_revision=expected_revision,
                changes=changes,
                updated_at=_utc_now(),
            )
            if updated is None:
                raise _revision_conflict(current.revision, ("models",))
            ai_revision = transaction.ai.revisions.increment(
                transaction.session
            )
            invalidations = ("models", "routes", "recipes")
            append_system_ai_event(
                transaction,
                event_type="model.updated",
                resource_type="model_profile",
                resource_id=model_profile_id,
                revision=ai_revision,
                invalidations=invalidations,
            )
            append_system_ai_event(
                transaction,
                event_type="ai.config.changed",
                resource_type="model_profile",
                resource_id=model_profile_id,
                revision=ai_revision,
                invalidations=invalidations,
            )
            return _model_dto(transaction, updated)

    def list_model_capabilities(
        self,
        *,
        provider_id: str | None = None,
        model_profile_id: str | None = None,
        capability_key: str | None = None,
        availability: str | None = None,
        cursor: CursorPosition | None = None,
        limit: int = 50,
    ) -> tuple[dict[str, object], CursorPosition | None]:
        if capability_key is not None:
            require_capability_key(capability_key)
        with self._unit_of_work.read() as transaction:
            if provider_id is not None:
                _require_provider(transaction, provider_id)
            if model_profile_id is not None:
                _require_model(transaction, model_profile_id)
            rows = transaction.ai.capabilities.list(
                transaction.session,
                provider_id=provider_id,
                model_profile_id=model_profile_id,
                capability_key=capability_key,
            )
            enriched = []
            for row in rows:
                model = _require_model(
                    transaction,
                    row.model_profile_id,
                )
                item = capability_to_dto(row)
                if (
                    availability is not None
                    and item["availability"] != availability
                ):
                    continue
                enriched.append(
                    {
                        **item,
                        "modelProfileId": row.model_profile_id,
                        "providerProfileId": model.provider_profile_id,
                    }
                )
            page, next_position = _dict_page(
                tuple(enriched),
                cursor,
                limit,
            )
            return (
                {
                    "items": list(page),
                    "totalKnown": len(enriched),
                },
                next_position,
            )

    def get_model_capabilities(
        self,
        model_profile_id: str,
    ) -> list[dict[str, object]]:
        with self._unit_of_work.read() as transaction:
            _require_model(transaction, model_profile_id)
            return [
                capability_to_dto(row)
                for row in transaction.ai.capabilities.list(
                    transaction.session,
                    model_profile_id=model_profile_id,
                )
            ]

    async def submit_capability_checks(
        self,
        model_profile_id: str,
        payload: Mapping[str, object],
        *,
        idempotency_key: str,
        request_id: str,
        operation_id: str,
    ) -> RuntimeTaskRecord:
        raw_keys = payload.get("capabilityKeys")
        keys = (
            tuple()
            if raw_keys is None
            else require_capability_keys(raw_keys)
        )
        with self._unit_of_work.read() as transaction:
            model = _require_model(transaction, model_profile_id)
            provider = _require_provider(
                transaction,
                model.provider_profile_id,
            )
        return await self._task_coordinator.submit_system_task(
            task_type=MODEL_CAPABILITY_CHECK_TASK_TYPE,
            payload={
                "modelProfileId": model.id,
                "modelRevision": int(model.revision),
                "providerRevision": int(provider.revision),
                "capabilityKeys": list(keys),
                "force": bool(payload.get("force", False)),
            },
            idempotency_key=idempotency_key,
            request_id=request_id,
            operation_id=operation_id,
            timeout_seconds=max(1, int(provider.timeout_ms / 1_000)),
        )

    def _create_model(
        self,
        transaction: AIConfigurationTransaction,
        payload: Mapping[str, object],
    ) -> AIResourceMutation:
        provider_id = str(payload["providerProfileId"])
        _require_provider(transaction, provider_id)
        model_id = str(payload["modelId"])
        if transaction.ai.models.get_by_provider_model(
            transaction.session,
            provider_id=provider_id,
            model_id=model_id,
        ) is not None:
            raise DomainError(
                ErrorCode.MODEL_ALREADY_EXISTS,
                "同一 Provider 已存在该模型",
                status_code=409,
            )
        now = _utc_now()
        row = transaction.ai.models.add(
            transaction.session,
            ModelProfile(
                id=f"model_{uuid4().hex}",
                provider_profile_id=provider_id,
                model_id=model_id,
                display_name=str(payload["displayName"]),
                enabled=bool(payload["enabled"]),
                discovery_source="manual",
                context_window=None,
                base_limits_json=dump_json(payload["baseLimits"]),
                revision=1,
                created_at=now,
                updated_at=now,
            ),
        )
        ai_revision = transaction.ai.revisions.increment(
            transaction.session
        )
        invalidations = ("models", "routes", "recipes")
        append_system_ai_event(
            transaction,
            event_type="model.updated",
            resource_type="model_profile",
            resource_id=row.id,
            revision=ai_revision,
            invalidations=invalidations,
        )
        append_system_ai_event(
            transaction,
            event_type="ai.config.changed",
            resource_type="model_profile",
            resource_id=row.id,
            revision=ai_revision,
            invalidations=invalidations,
        )
        return AIResourceMutation(
            data=_model_dto(transaction, row),
            resource_type="model_profile",
            resource_id=row.id,
            revision=int(row.revision),
            invalidations=invalidations,
        )
