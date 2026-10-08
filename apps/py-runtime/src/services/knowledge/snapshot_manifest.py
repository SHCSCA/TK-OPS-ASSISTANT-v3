from __future__ import annotations

from domain.models.knowledge import KnowledgeSource
from services.accounts.unit_of_work import AccountTransaction


def build_snapshot_manifest_v2(
    transaction: AccountTransaction,
    *,
    account_id: str,
    sources: tuple[KnowledgeSource, ...],
) -> list[dict[str, object]]:
    """冻结来源修订与派生块哈希，旧快照不自动获得新索引。"""
    manifest: list[dict[str, object]] = []
    for source in sorted(sources, key=lambda item: item.id):
        source_revision = int(source.revision)
        chunks = transaction.knowledge_assets.list_chunks(
            account_id,
            transaction.session,
            source_id=source.id,
            source_revision=source_revision,
        )
        manifest.append(
            {
                "manifestVersion": 2,
                "accountId": account_id,
                "sourceId": source.id,
                "contentHash": source.content_hash,
                "indexedRevision": source_revision,
                "sourceRevision": source_revision,
                "chunks": [
                    {
                        "ordinal": int(chunk.ordinal),
                        "contentHash": chunk.content_hash,
                        "tokenCount": int(chunk.token_count),
                        "extractorVersion": int(chunk.extractor_version),
                    }
                    for chunk in chunks
                ],
            }
        )
    return manifest


__all__ = ["build_snapshot_manifest_v2"]
