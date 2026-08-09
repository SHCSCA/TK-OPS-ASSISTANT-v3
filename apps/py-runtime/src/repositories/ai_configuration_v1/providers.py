from __future__ import annotations

from collections.abc import Mapping

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from domain.models.ai_configuration_v1 import ModelProfile, ProviderProfile
from repositories.ai_configuration_v1._support import (
    limited,
    log_repository_errors,
    validated_changes,
)

_PROVIDER_UPDATE_FIELDS = frozenset(
    {
        "name",
        "base_url",
        "credential_ref",
        "region",
        "proxy_ref",
        "timeout_ms",
        "max_concurrency",
        "enabled",
        "health_status",
        "last_checked_at",
        "last_error_code",
        "last_error_log_id",
    }
)


class ProviderProfileRepository:
    """通过调用方 Session 持久化系统 Provider。"""

    @log_repository_errors("列出 Provider")
    def list(
        self,
        session: Session,
        *,
        enabled: bool | None = None,
        health_status: str | None = None,
        limit: int | None = None,
    ) -> tuple[ProviderProfile, ...]:
        statement = select(ProviderProfile)
        if enabled is not None:
            statement = statement.where(ProviderProfile.enabled == enabled)
        if health_status is not None:
            statement = statement.where(
                ProviderProfile.health_status == health_status
            )
        statement = statement.order_by(
            ProviderProfile.updated_at.desc(),
            ProviderProfile.id.asc(),
        )
        return tuple(session.scalars(limited(statement, limit)).all())

    @log_repository_errors("读取 Provider")
    def get(
        self,
        session: Session,
        provider_id: str,
    ) -> ProviderProfile | None:
        return session.get(ProviderProfile, provider_id)

    @log_repository_errors("新增 Provider")
    def add(
        self,
        session: Session,
        provider: ProviderProfile,
    ) -> ProviderProfile:
        session.add(provider)
        session.flush([provider])
        return provider

    @log_repository_errors("更新 Provider")
    def update(
        self,
        session: Session,
        provider_id: str,
        *,
        expected_revision: int,
        changes: Mapping[str, object],
        updated_at: str,
    ) -> ProviderProfile | None:
        values = validated_changes(changes, _PROVIDER_UPDATE_FIELDS)
        if not values:
            current = self.get(session, provider_id)
            if current is None or current.revision != expected_revision:
                return None
            return current
        statement = (
            update(ProviderProfile)
            .where(
                ProviderProfile.id == provider_id,
                ProviderProfile.revision == expected_revision,
            )
            .values(
                **values,
                updated_at=updated_at,
                revision=ProviderProfile.revision + 1,
            )
            .returning(ProviderProfile)
            .execution_options(
                synchronize_session=False,
                populate_existing=True,
            )
        )
        return session.scalars(statement).one_or_none()

    @log_repository_errors("统计 Provider 模型")
    def count_models(
        self,
        session: Session,
        provider_id: str,
    ) -> int:
        count = session.scalar(
            select(func.count(ModelProfile.id)).where(
                ModelProfile.provider_profile_id == provider_id
            )
        )
        return int(count or 0)
