from __future__ import annotations

from collections.abc import Mapping, Sequence

from sqlalchemy import and_, or_, select, update
from sqlalchemy.orm import Session

from common.pagination import CursorPosition
from domain.models.ai_execution import AIExecution


class AIExecutionRepository:
    """持久化账号级 AI 执行聚合。"""

    def add(
        self,
        session: Session,
        row: AIExecution,
    ) -> AIExecution:
        session.add(row)
        session.flush([row])
        return row

    def get_scoped(
        self,
        session: Session,
        account_id: str,
        execution_id: str,
    ) -> AIExecution | None:
        return session.scalars(
            select(AIExecution).where(
                AIExecution.account_id == account_id,
                AIExecution.id == execution_id,
            )
        ).one_or_none()

    def get_any(
        self,
        session: Session,
        execution_id: str,
    ) -> AIExecution | None:
        return session.get(AIExecution, execution_id)

    def get_by_idempotency(
        self,
        session: Session,
        account_id: str,
        key_hash: str,
    ) -> AIExecution | None:
        return session.scalars(
            select(AIExecution).where(
                AIExecution.account_id == account_id,
                AIExecution.idempotency_key_hash == key_hash,
            )
        ).one_or_none()

    def list_page(
        self,
        session: Session,
        account_id: str,
        *,
        limit: int,
        cursor: CursorPosition | None,
        statuses: tuple[str, ...] | None,
        capability_key: str | None,
    ) -> tuple[tuple[AIExecution, ...], CursorPosition | None]:
        statement = select(AIExecution).where(
            AIExecution.account_id == account_id
        )
        if statuses:
            statement = statement.where(AIExecution.status.in_(statuses))
        if capability_key is not None:
            statement = statement.where(
                AIExecution.capability_key == capability_key
            )
        if cursor is not None:
            statement = statement.where(
                or_(
                    AIExecution.updated_at < cursor.sort_value,
                    and_(
                        AIExecution.updated_at == cursor.sort_value,
                        AIExecution.id < cursor.resource_id,
                    ),
                )
            )
        rows = tuple(
            session.scalars(
                statement.order_by(
                    AIExecution.updated_at.desc(),
                    AIExecution.id.desc(),
                ).limit(limit + 1)
            ).all()
        )
        page = rows[:limit]
        next_position = (
            CursorPosition(
                sort_value=page[-1].updated_at,
                resource_id=page[-1].id,
            )
            if len(rows) > limit and page
            else None
        )
        return page, next_position

    def list_non_terminal(
        self,
        session: Session,
    ) -> tuple[AIExecution, ...]:
        return tuple(
            session.scalars(
                select(AIExecution)
                .where(
                    AIExecution.status.in_(
                        ("queued", "running", "cancelling")
                    )
                )
                .order_by(AIExecution.created_at.asc())
            ).all()
        )

    def transition(
        self,
        session: Session,
        account_id: str,
        execution_id: str,
        *,
        expected_statuses: Sequence[str],
        values: Mapping[str, object],
    ) -> AIExecution | None:
        return session.scalars(
            update(AIExecution)
            .where(
                AIExecution.account_id == account_id,
                AIExecution.id == execution_id,
                AIExecution.status.in_(tuple(expected_statuses)),
            )
            .values(**values, revision=AIExecution.revision + 1)
            .returning(AIExecution)
            .execution_options(
                synchronize_session=False,
                populate_existing=True,
            )
        ).one_or_none()


__all__ = ["AIExecutionRepository"]
