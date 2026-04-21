from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from domain.models import (
    AICapabilityConfig,
    AIProviderHealth,
    AIProviderModel,
    AIProviderSetting,
)


@dataclass(frozen=True, slots=True)
class StoredAICapabilityConfig:
    capability_id: str
    enabled: bool
    provider: str
    model: str
    agent_role: str
    system_prompt: str
    user_prompt_template: str
    updated_at: str


@dataclass(frozen=True, slots=True)
class StoredAIProviderSetting:
    provider_id: str
    base_url: str
    updated_at: str


@dataclass(frozen=True, slots=True)
class StoredAIProviderModel:
    provider_id: str
    model_id: str
    display_name: str
    capability_kinds: list[str]
    input_modalities: list[str]
    output_modalities: list[str]
    context_window: int | None
    default_for: list[str]
    enabled: bool
    created_at: str
    updated_at: str


@dataclass(frozen=True, slots=True)
class StoredAIProviderHealth:
    provider_id: str
    label: str
    readiness: str
    last_checked_at: str | None
    latency_ms: int | None
    error_code: str | None
    error_message: str | None
    updated_at: str


class AICapabilityRepository:
    def __init__(self, *, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def load_capabilities(self) -> list[StoredAICapabilityConfig]:
        with self._session_factory() as session:
            rows = session.scalars(
                select(AICapabilityConfig).order_by(AICapabilityConfig.capability_id.asc())
            ).all()

        return [self._to_capability(item) for item in rows]

    def save_capabilities(
        self,
        capabilities: list[StoredAICapabilityConfig],
    ) -> list[StoredAICapabilityConfig]:
        with self._session_factory() as session:
            for item in capabilities:
                session.merge(
                    AICapabilityConfig(
                        capability_id=item.capability_id,
                        enabled=int(item.enabled),
                        provider=item.provider,
                        model=item.model,
                        agent_role=item.agent_role,
                        system_prompt=item.system_prompt,
                        user_prompt_template=item.user_prompt_template,
                        updated_at=item.updated_at,
                    )
                )
            session.commit()

        return capabilities

    def load_provider_settings(self) -> list[StoredAIProviderSetting]:
        with self._session_factory() as session:
            rows = session.scalars(
                select(AIProviderSetting).order_by(AIProviderSetting.provider_id.asc())
            ).all()

        return [self._to_provider(item) for item in rows]

    def save_provider_setting(self, provider_id: str, base_url: str) -> StoredAIProviderSetting:
        stored = StoredAIProviderSetting(
            provider_id=provider_id,
            base_url=base_url,
            updated_at=_utc_now(),
        )
        with self._session_factory() as session:
            session.merge(
                AIProviderSetting(
                    provider_id=stored.provider_id,
                    base_url=stored.base_url,
                    updated_at=stored.updated_at,
                )
            )
            session.commit()

        return stored

    def load_provider_models(
        self,
        *,
        provider_id: str | None = None,
    ) -> list[StoredAIProviderModel]:
        with self._session_factory() as session:
            stmt = select(AIProviderModel).order_by(
                AIProviderModel.provider_id.asc(),
                AIProviderModel.model_id.asc(),
            )
            if provider_id is not None:
                stmt = stmt.where(AIProviderModel.provider_id == provider_id)
            rows = session.scalars(stmt).all()

        return [self._to_provider_model(item) for item in rows]

    def upsert_provider_model(
        self,
        model: StoredAIProviderModel,
    ) -> tuple[StoredAIProviderModel, bool]:
        with self._session_factory() as session:
            existing = session.scalar(
                select(AIProviderModel).where(
                    AIProviderModel.provider_id == model.provider_id,
                    AIProviderModel.model_id == model.model_id,
                )
            )
            was_upsert = existing is not None
            if existing is None:
                existing = AIProviderModel(
                    provider_id=model.provider_id,
                    model_id=model.model_id,
                    display_name=model.display_name,
                    capability_kinds_json=json.dumps(model.capability_kinds, ensure_ascii=False),
                    input_modalities_json=json.dumps(model.input_modalities, ensure_ascii=False),
                    output_modalities_json=json.dumps(model.output_modalities, ensure_ascii=False),
                    context_window=model.context_window,
                    default_for_json=json.dumps(model.default_for, ensure_ascii=False),
                    enabled=int(model.enabled),
                    created_at=model.created_at,
                    updated_at=model.updated_at,
                )
                session.add(existing)
            else:
                existing.display_name = model.display_name
                existing.capability_kinds_json = json.dumps(
                    model.capability_kinds,
                    ensure_ascii=False,
                )
                existing.input_modalities_json = json.dumps(
                    model.input_modalities,
                    ensure_ascii=False,
                )
                existing.output_modalities_json = json.dumps(
                    model.output_modalities,
                    ensure_ascii=False,
                )
                existing.context_window = model.context_window
                existing.default_for_json = json.dumps(model.default_for, ensure_ascii=False)
                existing.enabled = int(model.enabled)
                existing.updated_at = model.updated_at
            session.commit()
            session.refresh(existing)
            return self._to_provider_model(existing), was_upsert

    def load_provider_health_snapshots(self) -> list[StoredAIProviderHealth]:
        with self._session_factory() as session:
            rows = session.scalars(
                select(AIProviderHealth).order_by(AIProviderHealth.provider_id.asc())
            ).all()
        return [self._to_provider_health(item) for item in rows]

    def save_provider_health_snapshots(
        self,
        items: list[StoredAIProviderHealth],
    ) -> list[StoredAIProviderHealth]:
        with self._session_factory() as session:
            for item in items:
                session.merge(
                    AIProviderHealth(
                        provider_id=item.provider_id,
                        label=item.label,
                        readiness=item.readiness,
                        last_checked_at=item.last_checked_at,
                        latency_ms=item.latency_ms,
                        error_code=item.error_code,
                        error_message=item.error_message,
                        updated_at=item.updated_at,
                    )
                )
            session.commit()
        return items

    def _to_capability(self, row: AICapabilityConfig) -> StoredAICapabilityConfig:
        return StoredAICapabilityConfig(
            capability_id=row.capability_id,
            enabled=bool(row.enabled),
            provider=row.provider,
            model=row.model,
            agent_role=row.agent_role,
            system_prompt=row.system_prompt,
            user_prompt_template=row.user_prompt_template,
            updated_at=row.updated_at,
        )

    def _to_provider(self, row: AIProviderSetting) -> StoredAIProviderSetting:
        return StoredAIProviderSetting(
            provider_id=row.provider_id,
            base_url=row.base_url,
            updated_at=row.updated_at,
        )

    def _to_provider_model(self, row: AIProviderModel) -> StoredAIProviderModel:
        return StoredAIProviderModel(
            provider_id=row.provider_id,
            model_id=row.model_id,
            display_name=row.display_name,
            capability_kinds=_loads_list(row.capability_kinds_json),
            input_modalities=_loads_list(row.input_modalities_json),
            output_modalities=_loads_list(row.output_modalities_json),
            context_window=row.context_window,
            default_for=_loads_list(row.default_for_json),
            enabled=bool(row.enabled),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _to_provider_health(self, row: AIProviderHealth) -> StoredAIProviderHealth:
        return StoredAIProviderHealth(
            provider_id=row.provider_id,
            label=row.label,
            readiness=row.readiness,
            last_checked_at=row.last_checked_at,
            latency_ms=row.latency_ms,
            error_code=row.error_code,
            error_message=row.error_message,
            updated_at=row.updated_at,
        )


def _loads_list(payload: str) -> list[str]:
    try:
        loaded = json.loads(payload)
    except json.JSONDecodeError:
        return []
    if not isinstance(loaded, list):
        return []
    return [str(item) for item in loaded if str(item).strip()]


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
