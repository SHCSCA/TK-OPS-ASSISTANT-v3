from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from domain.models.ai_execution_snapshot import (
    AIExecutionCandidate,
    AIExecutionSnapshot,
)


class AIExecutionSnapshotRepository:
    """持久化不可变执行快照与候选顺序。"""

    def add_snapshot(
        self,
        session: Session,
        row: AIExecutionSnapshot,
    ) -> AIExecutionSnapshot:
        session.add(row)
        session.flush([row])
        return row

    def add_candidates(
        self,
        session: Session,
        rows: tuple[AIExecutionCandidate, ...],
    ) -> tuple[AIExecutionCandidate, ...]:
        session.add_all(rows)
        if rows:
            session.flush()
        return rows

    def get_snapshot(
        self,
        session: Session,
        account_id: str,
        snapshot_id: str,
    ) -> AIExecutionSnapshot | None:
        return session.scalars(
            select(AIExecutionSnapshot).where(
                AIExecutionSnapshot.account_id == account_id,
                AIExecutionSnapshot.id == snapshot_id,
            )
        ).one_or_none()

    def list_candidates(
        self,
        session: Session,
        account_id: str,
        snapshot_id: str,
    ) -> tuple[AIExecutionCandidate, ...]:
        return tuple(
            session.scalars(
                select(AIExecutionCandidate)
                .where(
                    AIExecutionCandidate.account_id == account_id,
                    AIExecutionCandidate.execution_snapshot_id
                    == snapshot_id,
                )
                .order_by(AIExecutionCandidate.ordinal.asc())
            ).all()
        )


__all__ = ["AIExecutionSnapshotRepository"]
