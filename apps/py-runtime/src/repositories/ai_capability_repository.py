from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from persistence import connect_sqlite, initialize_schema


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
    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        initialize_schema(database_path)

    def load_capabilities(self) -> list[StoredAICapabilityConfig]:
        with connect_sqlite(self._database_path) as connection:
            rows = connection.execute(
                'SELECT * FROM ai_capability_configs ORDER BY capability_id ASC'
            ).fetchall()

        return [self._to_capability(row) for row in rows]

    def save_capabilities(
        self,
        capabilities: list[StoredAICapabilityConfig],
    ) -> list[StoredAICapabilityConfig]:
        with connect_sqlite(self._database_path) as connection:
            connection.executemany(
                '''
                INSERT INTO ai_capability_configs (
                    capability_id, enabled, provider, model,
                    agent_role, system_prompt, user_prompt_template, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(capability_id) DO UPDATE SET
                    enabled = excluded.enabled,
                    provider = excluded.provider,
                    model = excluded.model,
                    agent_role = excluded.agent_role,
                    system_prompt = excluded.system_prompt,
                    user_prompt_template = excluded.user_prompt_template,
                    updated_at = excluded.updated_at
                ''',
                [
                    (
                        item.capability_id,
                        int(item.enabled),
                        item.provider,
                        item.model,
                        item.agent_role,
                        item.system_prompt,
                        item.user_prompt_template,
                        item.updated_at,
                    )
                    for item in capabilities
                ],
            )
            connection.commit()

        return capabilities

    def load_provider_settings(self) -> list[StoredAIProviderSetting]:
        with connect_sqlite(self._database_path) as connection:
            rows = connection.execute(
                'SELECT * FROM ai_provider_settings ORDER BY provider_id ASC'
            ).fetchall()

        return [self._to_provider(row) for row in rows]

    def save_provider_setting(self, provider_id: str, base_url: str) -> StoredAIProviderSetting:
        stored = StoredAIProviderSetting(
            provider_id=provider_id,
            base_url=base_url,
            updated_at=_utc_now(),
        )
        with connect_sqlite(self._database_path) as connection:
            connection.execute(
                '''
                INSERT INTO ai_provider_settings (provider_id, base_url, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(provider_id) DO UPDATE SET
                    base_url = excluded.base_url,
                    updated_at = excluded.updated_at
                ''',
                (stored.provider_id, stored.base_url, stored.updated_at),
            )
            connection.commit()

        return stored

    def _to_capability(self, row) -> StoredAICapabilityConfig:
        return StoredAICapabilityConfig(
            capability_id=str(row['capability_id']),
            enabled=bool(row['enabled']),
            provider=str(row['provider']),
            model=str(row['model']),
            agent_role=str(row['agent_role']),
            system_prompt=str(row['system_prompt']),
            user_prompt_template=str(row['user_prompt_template']),
            updated_at=str(row['updated_at']),
        )

    def _to_provider(self, row) -> StoredAIProviderSetting:
        return StoredAIProviderSetting(
            provider_id=str(row['provider_id']),
            base_url=str(row['base_url']),
            updated_at=str(row['updated_at']),
        )


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace('+00:00', 'Z')
