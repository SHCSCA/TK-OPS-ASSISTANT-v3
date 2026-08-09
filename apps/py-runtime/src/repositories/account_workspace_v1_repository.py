from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal

from sqlalchemy import Select, and_, func, or_, select, update
from sqlalchemy.orm import Session

from common.pagination import CursorPosition
from domain.models.account import Account
from domain.models.account_configuration import PositioningProfile
from domain.models.runtime_task import RuntimeTask

log = logging.getLogger(__name__)

AccountFilterStatus = Literal[
    "draft",
    "unbound",
    "ready",
    "attention",
    "archived",
]


@dataclass(frozen=True, slots=True)
class AccountPage:
    items: tuple[Account, ...]
    next_position: CursorPosition | None
    total_known: int | None = None


@dataclass(frozen=True, slots=True)
class AccountTaskCounts:
    running: int
    failed: int


class AccountWorkspaceV1Repository:
    def get(self, session: Session, account_id: str) -> Account | None:
        return session.scalars(
            select(Account).where(Account.id == account_id)
        ).one_or_none()

    def add(self, session: Session, account: Account) -> Account:
        session.add(account)
        session.flush()
        return account

    def list_page(
        self,
        session: Session,
        *,
        limit: int,
        cursor: CursorPosition | None,
        query: str | None,
        status: AccountFilterStatus | None,
    ) -> AccountPage:
        statement = select(Account)
        if status is not None:
            statement = statement.where(Account.status == status)
        normalized_query = (query or "").strip()
        if normalized_query:
            pattern = f"%{_escape_like(normalized_query)}%"
            statement = statement.where(
                or_(
                    Account.name.ilike(pattern, escape="\\"),
                    Account.username.ilike(pattern, escape="\\"),
                )
            )
        statement = self._apply_cursor(statement, cursor)
        rows = tuple(
            session.scalars(
                statement.order_by(
                    Account.updated_at.desc(),
                    Account.id.desc(),
                ).limit(limit + 1)
            ).all()
        )
        has_more = len(rows) > limit
        items = rows[:limit]
        next_position = (
            CursorPosition(
                sort_value=items[-1].updated_at,
                resource_id=items[-1].id,
            )
            if has_more and items
            else None
        )
        return AccountPage(items=items, next_position=next_position)

    def active_positioning_summaries(
        self,
        session: Session,
        *,
        account_ids: tuple[str, ...],
    ) -> dict[str, str]:
        if not account_ids:
            return {}
        rows = session.execute(
            select(
                PositioningProfile.account_id,
                PositioningProfile.summary,
            ).where(
                PositioningProfile.account_id.in_(account_ids),
                PositioningProfile.status == "active",
            )
        ).all()
        return {
            str(account_id): str(summary)
            for account_id, summary in rows
        }

    def update_identity(
        self,
        session: Session,
        *,
        account_id: str,
        expected_revision: int,
        values: dict[str, object],
        updated_at: str,
    ) -> Account | None:
        return session.scalars(
            update(Account)
            .where(
                Account.id == account_id,
                Account.revision == expected_revision,
                Account.status != "archived",
            )
            .values(
                **values,
                revision=Account.revision + 1,
                updated_at=updated_at,
            )
            .returning(Account)
            .execution_options(
                synchronize_session=False,
                populate_existing=True,
            )
        ).one_or_none()

    def set_lifecycle(
        self,
        session: Session,
        *,
        account_id: str,
        expected_revision: int,
        status: AccountFilterStatus,
        status_reason_code: str | None,
        wizard_completed_at: str | None,
        archived_at: str | None,
        health_checked_at: str | None,
        updated_at: str,
    ) -> Account | None:
        return session.scalars(
            update(Account)
            .where(
                Account.id == account_id,
                Account.revision == expected_revision,
            )
            .values(
                status=status,
                status_reason_code=status_reason_code,
                wizard_completed_at=wizard_completed_at,
                archived_at=archived_at,
                last_health_checked_at=health_checked_at,
                revision=Account.revision + 1,
                updated_at=updated_at,
            )
            .returning(Account)
            .execution_options(
                synchronize_session=False,
                populate_existing=True,
            )
        ).one_or_none()

    def bump_revision(
        self,
        session: Session,
        *,
        account_id: str,
        expected_revision: int,
        updated_at: str,
    ) -> Account | None:
        return session.scalars(
            update(Account)
            .where(
                Account.id == account_id,
                Account.revision == expected_revision,
            )
            .values(
                revision=Account.revision + 1,
                updated_at=updated_at,
            )
            .returning(Account)
            .execution_options(
                synchronize_session=False,
                populate_existing=True,
            )
        ).one_or_none()

    def activate_workspace(
        self,
        session: Session,
        *,
        account_id: str,
        expected_revision: int,
        activated_at: str,
    ) -> Account | None:
        return session.scalars(
            update(Account)
            .where(
                Account.id == account_id,
                Account.revision == expected_revision,
                Account.status != "archived",
            )
            .values(
                last_used_at=activated_at,
                updated_at=activated_at,
                revision=Account.revision + 1,
            )
            .returning(Account)
            .execution_options(
                synchronize_session=False,
                populate_existing=True,
            )
        ).one_or_none()

    def acquire_write_lock(
        self,
        session: Session,
        *,
        account_id: str,
    ) -> bool:
        result = session.execute(
            update(Account)
            .where(Account.id == account_id)
            .values(revision=Account.revision)
        )
        return bool(result.rowcount)

    def task_counts(
        self,
        session: Session,
        *,
        account_id: str,
    ) -> AccountTaskCounts:
        rows = session.execute(
            select(RuntimeTask.status, func.count(RuntimeTask.id))
            .where(
                RuntimeTask.scope == "account",
                RuntimeTask.account_id == account_id,
                RuntimeTask.status.in_(
                    ("queued", "running", "cancelling", "failed")
                ),
            )
            .group_by(RuntimeTask.status)
        ).all()
        counts = {str(status): int(count) for status, count in rows}
        return AccountTaskCounts(
            running=sum(
                counts.get(status, 0)
                for status in ("queued", "running", "cancelling")
            ),
            failed=counts.get("failed", 0),
        )

    @staticmethod
    def _apply_cursor(
        statement: Select[tuple[Account]],
        cursor: CursorPosition | None,
    ) -> Select[tuple[Account]]:
        if cursor is None:
            return statement
        return statement.where(
            or_(
                Account.updated_at < cursor.sort_value,
                and_(
                    Account.updated_at == cursor.sort_value,
                    Account.id < cursor.resource_id,
                ),
            )
        )


def _escape_like(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )
