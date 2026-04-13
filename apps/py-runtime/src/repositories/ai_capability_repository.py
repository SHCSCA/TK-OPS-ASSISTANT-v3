from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from domain.models import AICapabilityConfig, AIProviderSetting


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


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
