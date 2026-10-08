from __future__ import annotations

from collections.abc import Mapping

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from domain.models.ai_configuration_v1 import (
    CapabilityRoute,
    CapabilityRouteRevision,
)
from repositories.ai_configuration_v1._support import (
    acquire_sqlite_write_lock,
    log_repository_errors,
)


class CapabilityRouteRevisionRepository:
    """管理能力路由不可变配置与受控状态转换。"""

    @log_repository_errors("列出能力路由修订")
    def list(
        self,
        session: Session,
        route_id: str,
    ) -> tuple[CapabilityRouteRevision, ...]:
        return tuple(
            session.scalars(
                select(CapabilityRouteRevision)
                .where(
                    CapabilityRouteRevision.capability_route_id == route_id
                )
                .order_by(CapabilityRouteRevision.revision.desc())
            ).all()
        )

    @log_repository_errors("读取能力路由修订")
    def get(
        self,
        session: Session,
        route_id: str,
        revision: int,
    ) -> CapabilityRouteRevision | None:
        return session.scalars(
            select(CapabilityRouteRevision).where(
                CapabilityRouteRevision.capability_route_id == route_id,
                CapabilityRouteRevision.revision == revision,
            )
        ).one_or_none()

    @log_repository_errors("按标识读取能力路由修订")
    def get_by_id(
        self,
        session: Session,
        revision_id: str,
    ) -> CapabilityRouteRevision | None:
        return session.get(CapabilityRouteRevision, revision_id)

    @log_repository_errors("计算下一能力路由修订")
    def next_revision(self, session: Session, route_id: str) -> int:
        maximum = session.scalar(
            select(func.max(CapabilityRouteRevision.revision)).where(
                CapabilityRouteRevision.capability_route_id == route_id
            )
        )
        return int(maximum or 0) + 1

    @log_repository_errors("新增能力路由修订")
    def add(
        self,
        session: Session,
        row: CapabilityRouteRevision,
    ) -> CapabilityRouteRevision:
        session.add(row)
        session.flush([row])
        return row

    @log_repository_errors("绑定能力路由依赖快照")
    def attach_snapshot(
        self,
        session: Session,
        *,
        revision_id: str,
        dependency_snapshot_id: str,
    ) -> CapabilityRouteRevision | None:
        statement = (
            update(CapabilityRouteRevision)
            .where(
                CapabilityRouteRevision.id == revision_id,
                CapabilityRouteRevision.status == "draft",
                CapabilityRouteRevision.dependency_snapshot_id.is_(None),
            )
            .values(dependency_snapshot_id=dependency_snapshot_id)
            .returning(CapabilityRouteRevision)
            .execution_options(
                synchronize_session=False,
                populate_existing=True,
            )
        )
        return session.scalars(statement).one_or_none()

    @log_repository_errors("激活能力路由修订")
    def activate(
        self,
        session: Session,
        *,
        route: CapabilityRoute,
        target: CapabilityRouteRevision,
        expected_aggregate_revision: int,
        mirror_changes: Mapping[str, object],
        updated_at: str,
    ) -> CapabilityRoute | None:
        acquire_sqlite_write_lock(session, "capability_routes")
        session.refresh(route)
        session.refresh(target)
        if (
            int(route.revision) != expected_aggregate_revision
            or target.capability_route_id != route.id
            or target.status != "draft"
            or target.dependency_snapshot_id is None
        ):
            return None
        session.execute(
            update(CapabilityRouteRevision)
            .where(
                CapabilityRouteRevision.capability_route_id == route.id,
                CapabilityRouteRevision.status == "active",
            )
            .values(status="archived")
        )
        target.status = "active"
        route.active_revision_id = target.id
        for field_name, value in mirror_changes.items():
            setattr(route, field_name, value)
        route.updated_at = updated_at
        route.revision = int(route.revision) + 1
        session.flush([target, route])
        return route


__all__ = ["CapabilityRouteRevisionRepository"]
