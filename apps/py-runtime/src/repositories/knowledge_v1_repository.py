from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from common.pagination import CursorPosition
from domain.models.knowledge import (
    AccountKnowledgeBase,
    KnowledgeSnapshot,
    KnowledgeSource,
)


@dataclass(frozen=True, slots=True)
class KnowledgeSourcePage:
    items: tuple[KnowledgeSource, ...]
    next_position: CursorPosition | None
    total_known: int | None = None


@dataclass(frozen=True, slots=True)
class KnowledgeSnapshotPage:
    items: tuple[KnowledgeSnapshot, ...]
    next_position: CursorPosition | None
    total_known: int | None = None


class KnowledgeV1Repository:
    def get_base(
        self,
        account_id: str,
        session: Session,
    ) -> AccountKnowledgeBase | None:
        return session.scalars(
            select(AccountKnowledgeBase).where(
                AccountKnowledgeBase.account_id == account_id
            )
        ).one_or_none()

    def add_base(
        self,
        account_id: str,
        session: Session,
        knowledge_base: AccountKnowledgeBase,
    ) -> AccountKnowledgeBase:
        _require_account_id(account_id, knowledge_base.account_id)
        session.add(knowledge_base)
        session.flush()
        return knowledge_base

    def update_rules(
        self,
        account_id: str,
        session: Session,
        *,
        rules_json: str,
        updated_at: str,
    ) -> AccountKnowledgeBase | None:
        knowledge_base = self.get_base(account_id, session)
        if knowledge_base is None:
            return None
        knowledge_base.rules_json = rules_json
        knowledge_base.rules_version += 1
        knowledge_base.revision += 1
        knowledge_base.updated_at = updated_at
        session.flush()
        return knowledge_base

    def source_counts(
        self,
        account_id: str,
        session: Session,
    ) -> dict[str, int]:
        rows = session.execute(
            select(KnowledgeSource.kind, func.count(KnowledgeSource.id))
            .where(
                KnowledgeSource.account_id == account_id,
                KnowledgeSource.deleted_at.is_(None),
            )
            .group_by(KnowledgeSource.kind)
        ).all()
        return {str(kind): int(count) for kind, count in rows}

    def get_source(
        self,
        account_id: str,
        session: Session,
        *,
        source_id: str,
    ) -> KnowledgeSource | None:
        return session.scalars(
            select(KnowledgeSource).where(
                KnowledgeSource.account_id == account_id,
                KnowledgeSource.id == source_id,
            )
        ).one_or_none()

    def get_sources(
        self,
        account_id: str,
        session: Session,
        *,
        source_ids: tuple[str, ...],
    ) -> tuple[KnowledgeSource, ...]:
        if not source_ids:
            return ()
        rows = session.scalars(
            select(KnowledgeSource).where(
                KnowledgeSource.account_id == account_id,
                KnowledgeSource.id.in_(source_ids),
                KnowledgeSource.deleted_at.is_(None),
            )
        ).all()
        by_id = {row.id: row for row in rows}
        return tuple(
            by_id[source_id]
            for source_id in source_ids
            if source_id in by_id
        )

    def list_sources(
        self,
        account_id: str,
        session: Session,
        *,
        limit: int,
        cursor: CursorPosition | None,
        kind: str | None = None,
        status: str | None = None,
        include_removed: bool = False,
    ) -> KnowledgeSourcePage:
        statement = select(KnowledgeSource).where(
            KnowledgeSource.account_id == account_id
        )
        if kind is not None:
            statement = statement.where(KnowledgeSource.kind == kind)
        if status == "removed":
            statement = statement.where(KnowledgeSource.deleted_at.is_not(None))
        elif status is not None:
            statement = statement.where(
                KnowledgeSource.status == status,
                KnowledgeSource.deleted_at.is_(None),
            )
        elif not include_removed:
            statement = statement.where(KnowledgeSource.deleted_at.is_(None))
        if cursor is not None:
            statement = statement.where(
                or_(
                    KnowledgeSource.updated_at < cursor.sort_value,
                    and_(
                        KnowledgeSource.updated_at == cursor.sort_value,
                        KnowledgeSource.id < cursor.resource_id,
                    ),
                )
            )
        rows = tuple(
            session.scalars(
                statement.order_by(
                    KnowledgeSource.updated_at.desc(),
                    KnowledgeSource.id.desc(),
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
        return KnowledgeSourcePage(
            items=items,
            next_position=next_position,
        )

    def list_sources_for_index(
        self,
        account_id: str,
        session: Session,
        *,
        source_ids: tuple[str, ...] | None,
    ) -> tuple[KnowledgeSource, ...]:
        statement = select(KnowledgeSource).where(
            KnowledgeSource.account_id == account_id,
            KnowledgeSource.deleted_at.is_(None),
        )
        if source_ids is not None:
            if not source_ids:
                return ()
            statement = statement.where(KnowledgeSource.id.in_(source_ids))
        rows = tuple(
            session.scalars(
                statement.order_by(
                    KnowledgeSource.created_at.asc(),
                    KnowledgeSource.id.asc(),
                )
            ).all()
        )
        if source_ids is None:
            return rows
        by_id = {row.id: row for row in rows}
        return tuple(
            by_id[source_id]
            for source_id in source_ids
            if source_id in by_id
        )

    def list_sources_with_status(
        self,
        account_id: str,
        session: Session,
        *,
        status: str,
    ) -> tuple[KnowledgeSource, ...]:
        return tuple(
            session.scalars(
                select(KnowledgeSource)
                .where(
                    KnowledgeSource.account_id == account_id,
                    KnowledgeSource.status == status,
                    KnowledgeSource.deleted_at.is_(None),
                )
                .order_by(
                    KnowledgeSource.updated_at.asc(),
                    KnowledgeSource.id.asc(),
                )
            ).all()
        )

    def list_text_source_references(
        self,
        account_id: str,
        session: Session,
    ) -> tuple[str, ...]:
        """返回包含软删除墓碑在内的内联正文引用。"""
        return tuple(
            session.scalars(
                select(KnowledgeSource.source_ref)
                .where(
                    KnowledgeSource.account_id == account_id,
                    KnowledgeSource.source_mode == "text",
                )
                .order_by(KnowledgeSource.id.asc())
            ).all()
        )

    def first_source_with_status(
        self,
        account_id: str,
        session: Session,
        *,
        status: str,
    ) -> KnowledgeSource | None:
        return session.scalars(
            select(KnowledgeSource)
            .where(
                KnowledgeSource.account_id == account_id,
                KnowledgeSource.status == status,
                KnowledgeSource.deleted_at.is_(None),
            )
            .order_by(
                KnowledgeSource.updated_at.desc(),
                KnowledgeSource.id.desc(),
            )
            .limit(1)
        ).one_or_none()

    def source_state_counts(
        self,
        account_id: str,
        session: Session,
    ) -> dict[str, int]:
        rows = session.execute(
            select(KnowledgeSource.status, func.count(KnowledgeSource.id))
            .where(
                KnowledgeSource.account_id == account_id,
                KnowledgeSource.deleted_at.is_(None),
            )
            .group_by(KnowledgeSource.status)
        ).all()
        return {str(status): int(count) for status, count in rows}

    def add_source(
        self,
        account_id: str,
        session: Session,
        source: KnowledgeSource,
    ) -> KnowledgeSource:
        _require_account_id(account_id, source.account_id)
        session.add(source)
        session.flush()
        return source

    def mark_source_removed(
        self,
        account_id: str,
        session: Session,
        *,
        source_id: str,
        removed_at: str,
    ) -> KnowledgeSource | None:
        source = self.get_source(
            account_id,
            session,
            source_id=source_id,
        )
        if source is None:
            return None
        if source.deleted_at is None:
            source.deleted_at = removed_at
            source.updated_at = removed_at
            source.revision += 1
            session.flush()
        return source

    def set_source_index_state(
        self,
        account_id: str,
        session: Session,
        *,
        source_id: str,
        status: str,
        content_hash: str | None,
        error_code: str | None,
        error_log_id: str | None,
        updated_at: str,
    ) -> KnowledgeSource | None:
        source = self.get_source(
            account_id,
            session,
            source_id=source_id,
        )
        if source is None or source.deleted_at is not None:
            return None
        source.status = status
        source.content_hash = content_hash
        source.error_code = error_code
        source.error_log_id = error_log_id
        source.updated_at = updated_at
        source.revision += 1
        session.flush()
        return source

    def set_base_index_state(
        self,
        account_id: str,
        session: Session,
        *,
        status: str,
        index_revision: int,
        last_indexed_at: str | None,
        error_code: str | None,
        error_log_id: str | None,
        updated_at: str,
    ) -> AccountKnowledgeBase | None:
        knowledge_base = self.get_base(account_id, session)
        if knowledge_base is None:
            return None
        knowledge_base.status = status
        knowledge_base.index_revision = index_revision
        knowledge_base.last_indexed_at = last_indexed_at
        knowledge_base.error_code = error_code
        knowledge_base.error_log_id = error_log_id
        knowledge_base.revision += 1
        knowledge_base.updated_at = updated_at
        session.flush()
        return knowledge_base

    def next_snapshot_version(
        self,
        account_id: str,
        session: Session,
    ) -> int:
        maximum = session.scalar(
            select(func.max(KnowledgeSnapshot.snapshot_version)).where(
                KnowledgeSnapshot.account_id == account_id
            )
        )
        return int(maximum or 0) + 1

    def get_snapshot(
        self,
        account_id: str,
        session: Session,
        *,
        snapshot_id: str,
    ) -> KnowledgeSnapshot | None:
        return session.scalars(
            select(KnowledgeSnapshot).where(
                KnowledgeSnapshot.account_id == account_id,
                KnowledgeSnapshot.id == snapshot_id,
            )
        ).one_or_none()

    def latest_snapshot(
        self,
        account_id: str,
        session: Session,
    ) -> KnowledgeSnapshot | None:
        return session.scalars(
            select(KnowledgeSnapshot)
            .where(KnowledgeSnapshot.account_id == account_id)
            .order_by(
                KnowledgeSnapshot.snapshot_version.desc(),
                KnowledgeSnapshot.id.desc(),
            )
            .limit(1)
        ).one_or_none()

    def list_snapshots(
        self,
        account_id: str,
        session: Session,
        *,
        limit: int,
        cursor: CursorPosition | None,
    ) -> KnowledgeSnapshotPage:
        statement = select(KnowledgeSnapshot).where(
            KnowledgeSnapshot.account_id == account_id
        )
        if cursor is not None:
            statement = statement.where(
                or_(
                    KnowledgeSnapshot.created_at < cursor.sort_value,
                    and_(
                        KnowledgeSnapshot.created_at == cursor.sort_value,
                        KnowledgeSnapshot.id < cursor.resource_id,
                    ),
                )
            )
        rows = tuple(
            session.scalars(
                statement.order_by(
                    KnowledgeSnapshot.created_at.desc(),
                    KnowledgeSnapshot.id.desc(),
                ).limit(limit + 1)
            ).all()
        )
        has_more = len(rows) > limit
        items = rows[:limit]
        next_position = (
            CursorPosition(
                sort_value=items[-1].created_at,
                resource_id=items[-1].id,
            )
            if has_more and items
            else None
        )
        return KnowledgeSnapshotPage(
            items=items,
            next_position=next_position,
        )

    def add_snapshot(
        self,
        account_id: str,
        session: Session,
        snapshot: KnowledgeSnapshot,
    ) -> KnowledgeSnapshot:
        _require_account_id(account_id, snapshot.account_id)
        session.add(snapshot)
        session.flush()
        return snapshot


def _require_account_id(expected: str, actual: str) -> None:
    if expected != actual:
        raise ValueError("知识对象与请求账号不一致")
