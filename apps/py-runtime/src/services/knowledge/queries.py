from __future__ import annotations

from common.pagination import CursorPosition
from errors import DomainError, ErrorCode
from schemas.v1.knowledge import (
    KNOWLEDGE_KINDS,
    KNOWLEDGE_SOURCE_STATUSES,
    KnowledgeDto,
    KnowledgeSnapshotDto,
    KnowledgeSnapshotPageDto,
    KnowledgeSourcePageDto,
)
from services.accounts.guards import require_account
from services.accounts.unit_of_work import AccountUnitOfWork
from services.knowledge.presentation import (
    knowledge_to_dto,
    snapshot_to_dto,
    source_to_dto,
)
from services.knowledge.support import knowledge_base_missing


class KnowledgeQueryService:
    def __init__(self, unit_of_work: AccountUnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    def get(self, account_id: str) -> KnowledgeDto:
        with self._unit_of_work.read() as transaction:
            account = require_account(
                account_id,
                transaction.session,
                transaction.accounts,
            )
            knowledge_base = transaction.knowledge.get_base(
                account_id,
                transaction.session,
            )
            if knowledge_base is None:
                raise knowledge_base_missing()
            latest = transaction.knowledge.latest_snapshot(
                account_id,
                transaction.session,
            )
            return knowledge_to_dto(
                account_id,
                knowledge_base,
                source_counts=transaction.knowledge.source_counts(
                    account_id,
                    transaction.session,
                ),
                latest_snapshot_id=None if latest is None else latest.id,
                account_revision=int(account.revision),
            )

    def list_sources(
        self,
        account_id: str,
        *,
        limit: int,
        cursor: CursorPosition | None,
        kind: str | None = None,
        status: str | None = None,
    ) -> tuple[KnowledgeSourcePageDto, CursorPosition | None]:
        _validate_source_filters(kind=kind, status=status)
        with self._unit_of_work.read() as transaction:
            require_account(
                account_id,
                transaction.session,
                transaction.accounts,
            )
            page = transaction.knowledge.list_sources(
                account_id,
                transaction.session,
                limit=limit,
                cursor=cursor,
                kind=kind,
                status=status,
            )
            return (
                KnowledgeSourcePageDto(
                    items=[source_to_dto(item) for item in page.items],
                    totalKnown=page.total_known,
                ),
                page.next_position,
            )

    def list_snapshots(
        self,
        account_id: str,
        *,
        limit: int,
        cursor: CursorPosition | None,
    ) -> tuple[KnowledgeSnapshotPageDto, CursorPosition | None]:
        with self._unit_of_work.read() as transaction:
            require_account(
                account_id,
                transaction.session,
                transaction.accounts,
            )
            page = transaction.knowledge.list_snapshots(
                account_id,
                transaction.session,
                limit=limit,
                cursor=cursor,
            )
            return (
                KnowledgeSnapshotPageDto(
                    items=[snapshot_to_dto(item) for item in page.items],
                    totalKnown=page.total_known,
                ),
                page.next_position,
            )

    def get_snapshot(
        self,
        account_id: str,
        snapshot_id: str,
    ) -> KnowledgeSnapshotDto:
        with self._unit_of_work.read() as transaction:
            require_account(
                account_id,
                transaction.session,
                transaction.accounts,
            )
            snapshot = transaction.knowledge.get_snapshot(
                account_id,
                transaction.session,
                snapshot_id=snapshot_id,
            )
            if snapshot is None:
                raise DomainError(
                    ErrorCode.KNOWLEDGE_SNAPSHOT_NOT_FOUND,
                    "知识快照不存在",
                    status_code=404,
                )
            return snapshot_to_dto(snapshot)


def _validate_source_filters(
    *,
    kind: str | None,
    status: str | None,
) -> None:
    if kind is not None and kind not in KNOWLEDGE_KINDS:
        raise DomainError(
            ErrorCode.REQUEST_VALIDATION_FAILED,
            "知识来源类型筛选值无效",
            status_code=422,
        )
    if status is not None and status not in KNOWLEDGE_SOURCE_STATUSES:
        raise DomainError(
            ErrorCode.REQUEST_VALIDATION_FAILED,
            "知识来源状态筛选值无效",
            status_code=422,
        )
