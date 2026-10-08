from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from domain.models.ai_execution_snapshot import AIDependencySnapshot
from repositories.ai_configuration_v1._support import log_repository_errors


class AIDependencySnapshotRepository:
    """只追加并读取不可变依赖快照。"""

    @log_repository_errors("新增 AI 依赖快照")
    def add(
        self,
        session: Session,
        row: AIDependencySnapshot,
    ) -> AIDependencySnapshot:
        session.add(row)
        session.flush([row])
        return row

    @log_repository_errors("读取 AI 依赖快照")
    def get(
        self,
        session: Session,
        snapshot_id: str,
    ) -> AIDependencySnapshot | None:
        return session.get(AIDependencySnapshot, snapshot_id)

    @log_repository_errors("按归属读取 AI 依赖快照")
    def get_owner(
        self,
        session: Session,
        *,
        owner_type: str,
        owner_id: str,
        owner_revision: int,
    ) -> AIDependencySnapshot | None:
        return session.scalars(
            select(AIDependencySnapshot).where(
                AIDependencySnapshot.owner_type == owner_type,
                AIDependencySnapshot.owner_id == owner_id,
                AIDependencySnapshot.owner_revision == owner_revision,
            )
        ).one_or_none()


__all__ = ["AIDependencySnapshotRepository"]
