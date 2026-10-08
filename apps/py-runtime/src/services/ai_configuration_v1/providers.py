from __future__ import annotations

from collections.abc import Mapping
from uuid import uuid4

from app.secret_store import SecretStore
from common.pagination import CursorPosition
from domain.models.ai_configuration_v1 import ProviderProfile
from errors import DomainError, ErrorCode
from services.accounts.idempotency import MutationCommand
from services.tasks.coordinator import TaskCoordinator
from services.tasks.types import RuntimeTaskRecord

from .constants import (
    PROVIDER_HEALTH_TASK_TYPE,
    PROVIDER_MODEL_DISCOVERY_TASK_TYPE,
)
from .dto import provider_to_dto
from .events import append_system_ai_event
from .mutation import (
    AIConfigurationMutationExecutor,
    AIResourceMutation,
)
from .mutation_helpers import (
    delete_secret_safely as _delete_secret_safely,
    increment_ai_revision as _increment_ai_revision,
    provider_revision_conflict as _revision_conflict,
    utc_now as _utc_now,
)
from .json_codec import dump_json
from .pagination_helpers import provider_page as _provider_page
from .profile_normalization import (
    normalize_provider_create as _normalize_create_payload,
    normalize_provider_patch as _normalize_patch_payload,
    require_openai_protocol_params,
)
from .revision_snapshots import create_provider_revision
from .query_helpers import (
    provider_dto as _provider_dto,
    require_provider as _require_provider,
)
from .replay_helpers import (
    load_provider_replay as _load_provider_replay,
)
from .unit_of_work import (
    AIConfigurationTransaction,
    AIConfigurationUnitOfWork,
)


class ProviderProfileService:
    def __init__(
        self,
        unit_of_work: AIConfigurationUnitOfWork,
        mutations: AIConfigurationMutationExecutor,
        *,
        secret_store: SecretStore,
        task_coordinator: TaskCoordinator,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._mutations = mutations
        self._secret_store = secret_store
        self._task_coordinator = task_coordinator

    def list_providers(
        self,
        *,
        enabled: bool | None = None,
        health_status: str | None = None,
        cursor: CursorPosition | None = None,
        limit: int = 50,
    ) -> tuple[dict[str, object], CursorPosition | None]:
        with self._unit_of_work.read() as transaction:
            rows = transaction.ai.providers.list(
                transaction.session,
                enabled=enabled,
                health_status=health_status,
            )
            page, next_position = _provider_page(rows, cursor, limit)
            return (
                {
                    "items": [
                        provider_to_dto(
                            row,
                            credential_configured=(
                                row.credential_ref is not None
                            ),
                        )
                        for row in page
                    ],
                    "totalKnown": len(rows),
                },
                next_position,
            )

    def get_provider(self, provider_id: str) -> dict[str, object]:
        with self._unit_of_work.read() as transaction:
            row = _require_provider(transaction, provider_id)
            return _provider_dto(row)

    def create_provider(
        self,
        payload: Mapping[str, object],
        *,
        idempotency_key: str,
        request_id: str,
        operation_id: str,
    ) -> AIResourceMutation:
        del request_id, operation_id
        normalized = _normalize_create_payload(payload)
        command = MutationCommand(
            account_id=None,
            operation_name="ai.provider.create",
            idempotency_key=idempotency_key,
            request_payload=normalized,
        )
        return self._mutations.execute(
            command,
            work=lambda transaction: self._create(
                transaction,
                normalized,
            ),
            replay_loader=_load_provider_replay,
        )

    def update_provider(
        self,
        provider_id: str,
        payload: Mapping[str, object],
        *,
        expected_revision: int,
        request_id: str,
        operation_id: str,
    ) -> dict[str, object]:
        del request_id, operation_id
        changes = _normalize_patch_payload(payload)
        now = _utc_now()
        with self._unit_of_work.write() as transaction:
            current = _require_provider(transaction, provider_id)
            if (
                current.adapter_type == "openai_compatible"
                and "extra_params_json" in changes
            ):
                changes["extra_params_json"] = require_openai_protocol_params(
                    str(changes["extra_params_json"])
                )
            updated = transaction.ai.providers.update(
                transaction.session,
                provider_id,
                expected_revision=expected_revision,
                changes=changes,
                updated_at=now,
            )
            if updated is None:
                raise _revision_conflict(
                    current.revision,
                    invalidations=("providers",),
                )
            create_provider_revision(transaction, updated)
            ai_revision = _increment_ai_revision(transaction)
            invalidations = ("providers", "models", "routes", "recipes")
            append_system_ai_event(
                transaction,
                event_type="provider.updated",
                resource_type="provider_profile",
                resource_id=provider_id,
                revision=ai_revision,
                invalidations=invalidations,
            )
            append_system_ai_event(
                transaction,
                event_type="ai.config.changed",
                resource_type="provider_profile",
                resource_id=provider_id,
                revision=ai_revision,
                invalidations=invalidations,
            )
            return _provider_dto(updated)

    def update_credential(
        self,
        provider_id: str,
        payload: Mapping[str, object],
        *,
        expected_revision: int,
        request_id: str,
        operation_id: str,
    ) -> dict[str, object]:
        del request_id, operation_id
        credential = payload.get("credential")
        if (
            not isinstance(credential, str)
            or not credential
            or credential != credential.strip()
            or len(credential) > 32_768
        ):
            raise DomainError(
                ErrorCode.REQUEST_VALIDATION_FAILED,
                "Provider 凭据格式无效",
                status_code=422,
            )
        new_reference = (
            f"secret://providers/{provider_id}/{uuid4().hex}"
        )
        try:
            self._secret_store.set(new_reference, credential)
        except Exception as exc:
            raise DomainError(
                ErrorCode.PROVIDER_SECRET_UNAVAILABLE,
                "Provider 凭据无法写入系统安全存储",
                status_code=503,
                loggable=True,
            ) from exc

        try:
            with self._unit_of_work.write() as transaction:
                current = _require_provider(transaction, provider_id)
                now = _utc_now()
                updated = transaction.ai.providers.update(
                    transaction.session,
                    provider_id,
                    expected_revision=expected_revision,
                    changes={
                        "credential_ref": new_reference,
                        "health_status": "unknown",
                        "last_error_code": None,
                        "last_error_log_id": None,
                    },
                    updated_at=now,
                )
                if updated is None:
                    raise _revision_conflict(
                        current.revision,
                        invalidations=("providers",),
                    )
                create_provider_revision(transaction, updated)
                ai_revision = _increment_ai_revision(transaction)
                append_system_ai_event(
                    transaction,
                    event_type="provider.credential.updated",
                    resource_type="provider_profile",
                    resource_id=provider_id,
                    revision=ai_revision,
                    invalidations=("provider", "ai-summary"),
                )
                provider_revision = int(updated.revision)
        except Exception:
            _delete_secret_safely(self._secret_store, new_reference)
            raise

        # 旧引用可能仍被非终态执行快照引用，按配置总线保留期清理。
        return {
            "configured": True,
            "maskedValue": f"••••{credential[-4:]}",
            "updatedAt": _utc_now(),
            "providerRevision": provider_revision,
            "credentialReferenceChanged": True,
        }

    async def submit_provider_check(
        self,
        provider_id: str,
        payload: Mapping[str, object],
        *,
        idempotency_key: str,
        request_id: str,
        operation_id: str,
    ) -> RuntimeTaskRecord:
        provider = self._provider_task_snapshot(provider_id)
        return await self._task_coordinator.submit_system_task(
            task_type=PROVIDER_HEALTH_TASK_TYPE,
            payload={
                "providerId": provider.id,
                "providerRevision": int(provider.revision),
                "stages": list(
                    payload.get(
                        "stages",
                        ("network", "authentication"),
                    )
                ),
                "force": bool(payload.get("force", False)),
            },
            idempotency_key=idempotency_key,
            request_id=request_id,
            operation_id=operation_id,
            timeout_seconds=max(1, int(provider.timeout_ms / 1_000)),
        )

    async def submit_model_discovery(
        self,
        provider_id: str,
        payload: Mapping[str, object],
        *,
        idempotency_key: str,
        request_id: str,
        operation_id: str,
    ) -> RuntimeTaskRecord:
        provider = self._provider_task_snapshot(provider_id)
        return await self._task_coordinator.submit_system_task(
            task_type=PROVIDER_MODEL_DISCOVERY_TASK_TYPE,
            payload={
                "providerId": provider.id,
                "providerRevision": int(provider.revision),
                "replaceMissing": bool(
                    payload.get("replaceMissing", False)
                ),
            },
            idempotency_key=idempotency_key,
            request_id=request_id,
            operation_id=operation_id,
            timeout_seconds=max(1, int(provider.timeout_ms / 1_000)),
        )

    def _provider_task_snapshot(
        self,
        provider_id: str,
    ) -> ProviderProfile:
        with self._unit_of_work.read() as transaction:
            provider = _require_provider(transaction, provider_id)
            if provider.credential_ref is not None:
                try:
                    credential = self._secret_store.get(
                        provider.credential_ref
                    )
                except Exception as exc:
                    raise DomainError(
                        ErrorCode.PROVIDER_SECRET_UNAVAILABLE,
                        "Provider 凭据暂不可用",
                        status_code=503,
                        loggable=True,
                    ) from exc
                if credential is None:
                    raise DomainError(
                        ErrorCode.PROVIDER_SECRET_UNAVAILABLE,
                        "Provider 凭据引用已失效，请重新设置",
                        status_code=503,
                    )
            return provider

    def _create(
        self,
        transaction: AIConfigurationTransaction,
        payload: Mapping[str, object],
    ) -> AIResourceMutation:
        now = _utc_now()
        provider_id = f"prov_{uuid4().hex}"
        row = transaction.ai.providers.add(
            transaction.session,
            ProviderProfile(
                id=provider_id,
                name=str(payload["name"]),
                adapter_type=str(payload["adapterType"]),
                base_url=str(payload["baseUrl"]),
                credential_ref=None,
                region=(
                    str(payload["region"])
                    if payload.get("region") is not None
                    else None
                ),
                proxy_ref=(
                    str(payload["proxyRef"])
                    if payload.get("proxyRef") is not None
                    else None
                ),
                extra_params_json=dump_json(payload["extraParams"]),
                cost_policy_json=dump_json(payload["costPolicy"]),
                active_revision_id=None,
                timeout_ms=int(payload["timeoutMs"]),
                max_concurrency=int(payload["maxConcurrency"]),
                enabled=bool(payload["enabled"]),
                health_status="unknown",
                last_checked_at=None,
                last_error_code=None,
                last_error_log_id=None,
                revision=1,
                created_at=now,
                updated_at=now,
            ),
        )
        create_provider_revision(transaction, row)
        ai_revision = _increment_ai_revision(transaction)
        invalidations = ("providers", "ai-summary")
        append_system_ai_event(
            transaction,
            event_type="provider.updated",
            resource_type="provider_profile",
            resource_id=provider_id,
            revision=ai_revision,
            invalidations=invalidations,
        )
        return AIResourceMutation(
            data=_provider_dto(row),
            resource_type="provider_profile",
            resource_id=provider_id,
            revision=int(row.revision),
            invalidations=invalidations,
        )
