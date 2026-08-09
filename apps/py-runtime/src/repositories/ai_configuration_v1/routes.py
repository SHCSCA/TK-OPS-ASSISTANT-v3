from __future__ import annotations

from collections.abc import Mapping

from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from domain.models.ai_configuration_v1 import CapabilityRoute
from repositories.ai_configuration_v1._support import (
    limited,
    log_repository_errors,
    validated_changes,
)

_ROUTE_UPDATE_FIELDS = frozenset(
    {
        "primary_model_profile_id",
        "fallback_model_profile_id",
        "prompt_profile_id",
        "enabled",
        "validation_status",
        "validation_issues_json",
    }
)


class CapabilityRouteRepository:
    """持久化系统级能力路由聚合。"""

    @log_repository_errors("列出能力路由")
    def list(
        self,
        session: Session,
        *,
        capability_key: str | None = None,
        validation_status: str | None = None,
        limit: int | None = None,
    ) -> tuple[CapabilityRoute, ...]:
        statement = select(CapabilityRoute)
        if capability_key is not None:
            statement = statement.where(
                CapabilityRoute.capability_key == capability_key
            )
        if validation_status is not None:
            statement = statement.where(
                CapabilityRoute.validation_status == validation_status
            )
        statement = statement.order_by(CapabilityRoute.capability_key.asc())
        return tuple(session.scalars(limited(statement, limit)).all())

    @log_repository_errors("读取能力路由")
    def get(
        self,
        session: Session,
        capability_key: str,
    ) -> CapabilityRoute | None:
        return session.scalars(
            select(CapabilityRoute).where(
                CapabilityRoute.capability_key == capability_key
            )
        ).one_or_none()

    @log_repository_errors("新增能力路由")
    def add(
        self,
        session: Session,
        route: CapabilityRoute,
    ) -> CapabilityRoute:
        session.add(route)
        session.flush([route])
        return route

    @log_repository_errors("更新能力路由")
    def update(
        self,
        session: Session,
        capability_key: str,
        *,
        expected_revision: int,
        changes: Mapping[str, object],
        updated_at: str,
    ) -> CapabilityRoute | None:
        values = validated_changes(changes, _ROUTE_UPDATE_FIELDS)
        if not values:
            current = self.get(session, capability_key)
            if current is None or current.revision != expected_revision:
                return None
            return current
        statement = (
            update(CapabilityRoute)
            .where(
                CapabilityRoute.capability_key == capability_key,
                CapabilityRoute.revision == expected_revision,
            )
            .values(
                **values,
                updated_at=updated_at,
                revision=CapabilityRoute.revision + 1,
            )
            .returning(CapabilityRoute)
            .execution_options(
                synchronize_session=False,
                populate_existing=True,
            )
        )
        return session.scalars(statement).one_or_none()

    @log_repository_errors("列出引用模型的能力路由")
    def list_referencing_model(
        self,
        session: Session,
        model_profile_id: str,
    ) -> tuple[CapabilityRoute, ...]:
        return tuple(
            session.scalars(
                select(CapabilityRoute)
                .where(
                    or_(
                        CapabilityRoute.primary_model_profile_id
                        == model_profile_id,
                        CapabilityRoute.fallback_model_profile_id
                        == model_profile_id,
                    )
                )
                .order_by(CapabilityRoute.capability_key.asc())
            ).all()
        )

    @log_repository_errors("统计 Prompt 路由引用")
    def count_by_prompt(
        self,
        session: Session,
        prompt_profile_id: str,
    ) -> int:
        count = session.scalar(
            select(func.count(CapabilityRoute.id)).where(
                CapabilityRoute.prompt_profile_id == prompt_profile_id
            )
        )
        return int(count or 0)
