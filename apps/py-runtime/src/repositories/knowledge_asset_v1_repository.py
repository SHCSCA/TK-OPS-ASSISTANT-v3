from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from domain.models.account_asset import (
    AccountAsset,
    KnowledgeIndexChunk,
    KnowledgeSourceAsset,
)


class KnowledgeAssetV1Repository:
    """持久化账号受控文件、来源关联和派生文本块。"""

    def add_asset(
        self,
        account_id: str,
        session: Session,
        asset: AccountAsset,
    ) -> AccountAsset:
        _require_account(account_id, asset.account_id)
        session.add(asset)
        session.flush()
        return asset

    def link_source(
        self,
        account_id: str,
        session: Session,
        link: KnowledgeSourceAsset,
    ) -> KnowledgeSourceAsset:
        _require_account(account_id, link.account_id)
        session.add(link)
        session.flush()
        return link

    def get_asset_for_source(
        self,
        account_id: str,
        session: Session,
        *,
        source_id: str,
    ) -> AccountAsset | None:
        return session.scalars(
            select(AccountAsset)
            .join(
                KnowledgeSourceAsset,
                KnowledgeSourceAsset.account_asset_id == AccountAsset.id,
            )
            .where(
                AccountAsset.account_id == account_id,
                KnowledgeSourceAsset.account_id == account_id,
                KnowledgeSourceAsset.knowledge_source_id == source_id,
            )
        ).one_or_none()

    def list_assets_for_sources(
        self,
        account_id: str,
        session: Session,
        *,
        source_ids: tuple[str, ...],
    ) -> dict[str, AccountAsset]:
        if not source_ids:
            return {}
        rows = session.execute(
            select(KnowledgeSourceAsset.knowledge_source_id, AccountAsset)
            .join(
                AccountAsset,
                AccountAsset.id == KnowledgeSourceAsset.account_asset_id,
            )
            .where(
                KnowledgeSourceAsset.account_id == account_id,
                AccountAsset.account_id == account_id,
                KnowledgeSourceAsset.knowledge_source_id.in_(source_ids),
            )
        ).all()
        return {str(source_id): asset for source_id, asset in rows}

    def set_asset_state_for_source(
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
    ) -> AccountAsset | None:
        asset = self.get_asset_for_source(
            account_id,
            session,
            source_id=source_id,
        )
        if asset is None:
            return None
        asset.status = status
        if content_hash is not None:
            asset.content_hash = content_hash
        asset.error_code = error_code
        asset.error_log_id = error_log_id
        asset.updated_at = updated_at
        asset.revision += 1
        session.flush()
        return asset

    def add_chunks(
        self,
        account_id: str,
        session: Session,
        chunks: Iterable[KnowledgeIndexChunk],
    ) -> tuple[KnowledgeIndexChunk, ...]:
        items = tuple(chunks)
        for chunk in items:
            _require_account(account_id, chunk.account_id)
            session.add(chunk)
        if items:
            session.flush()
        return items

    def list_chunks(
        self,
        account_id: str,
        session: Session,
        *,
        source_id: str,
        source_revision: int,
    ) -> tuple[KnowledgeIndexChunk, ...]:
        return tuple(
            session.scalars(
                select(KnowledgeIndexChunk)
                .where(
                    KnowledgeIndexChunk.account_id == account_id,
                    KnowledgeIndexChunk.knowledge_source_id == source_id,
                    KnowledgeIndexChunk.source_revision == source_revision,
                )
                .order_by(KnowledgeIndexChunk.ordinal.asc())
            ).all()
        )


def _require_account(expected: str, actual: str) -> None:
    if expected != actual:
        raise ValueError("账号资产仓储拒绝跨账号写入")
