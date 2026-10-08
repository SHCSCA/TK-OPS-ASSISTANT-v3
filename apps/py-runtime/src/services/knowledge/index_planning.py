from __future__ import annotations

from services.accounts.guards import require_account
from services.accounts.unit_of_work import AccountUnitOfWork
from services.knowledge.index_manifest import build_index_plan
from services.knowledge.index_state_support import source_invalid
from services.knowledge.index_types import (
    KnowledgeIndexPlan,
    KnowledgeIndexSource,
)


class KnowledgeIndexPlanner:
    def __init__(self, unit_of_work: AccountUnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    def plan(
        self,
        account_id: str,
        source_ids: tuple[str, ...] | None,
    ) -> KnowledgeIndexPlan:
        if source_ids is not None and (
            not source_ids or len(set(source_ids)) != len(source_ids)
        ):
            raise source_invalid("知识索引必须选择不重复的来源")
        with self._unit_of_work.read() as transaction:
            require_account(
                account_id,
                transaction.session,
                transaction.accounts,
            )
            sources = transaction.knowledge.list_sources_for_index(
                account_id,
                transaction.session,
                source_ids=source_ids,
            )
            if not sources or (
                source_ids is not None and len(sources) != len(source_ids)
            ):
                raise source_invalid(
                    "知识索引来源不存在、已移除或不属于当前账号"
                )
            assets = transaction.knowledge_assets.list_assets_for_sources(
                account_id,
                transaction.session,
                source_ids=tuple(source.id for source in sources),
            )
            return build_index_plan(account_id, sources, assets)

    def source(
        self,
        account_id: str,
        source_id: str,
    ) -> KnowledgeIndexSource:
        with self._unit_of_work.read() as transaction:
            require_account(
                account_id,
                transaction.session,
                transaction.accounts,
            )
            source = transaction.knowledge.get_source(
                account_id,
                transaction.session,
                source_id=source_id,
            )
            if source is None or source.deleted_at is not None:
                raise source_invalid(
                    "知识索引来源不存在、已移除或不属于当前账号"
                )
            return KnowledgeIndexSource(
                id=source.id,
                source_mode=source.source_mode,
                source_ref=source.source_ref,
                source_url=source.source_url,
                revision=int(source.revision),
                status=source.status,
            )
