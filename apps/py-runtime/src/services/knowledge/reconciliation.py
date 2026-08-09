from __future__ import annotations

import logging
from collections.abc import Callable, Collection, Iterable, Mapping
from dataclasses import dataclass

from services.accounts.guards import require_account
from services.accounts.lifecycle_sync import AccountLifecycleSynchronizer
from services.accounts.unit_of_work import AccountUnitOfWork
from services.knowledge.index_policy import KnowledgeIndexPolicy
from services.knowledge.index_state import KnowledgeIndexStateStore

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class KnowledgeIndexReconciliationReport:
    checked_account_count: int
    protected_active_source_count: int
    reconciled_source_count: int


class KnowledgeIndexReconciler:
    """在任务恢复前后对账没有活动任务承接的 indexing 来源。"""

    def __init__(
        self,
        unit_of_work: AccountUnitOfWork,
        *,
        policy_provider: Callable[[], KnowledgeIndexPolicy],
        lifecycle_synchronizer: AccountLifecycleSynchronizer,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._state = KnowledgeIndexStateStore(
            unit_of_work,
            lifecycle_synchronizer=lifecycle_synchronizer,
        )
        self._policy_provider = policy_provider

    def reconcile(
        self,
        account_ids: Iterable[str],
        *,
        active_source_ids_by_account: Mapping[str, Collection[str]],
    ) -> KnowledgeIndexReconciliationReport:
        unique_account_ids = tuple(dict.fromkeys(account_ids))
        active = {
            account_id: frozenset(source_ids)
            for account_id, source_ids in active_source_ids_by_account.items()
        }
        policy = self._policy_provider()
        checked = 0
        protected = 0
        reconciled = 0
        failures: list[str] = []
        for account_id in unique_account_ids:
            checked += 1
            try:
                source_ids = self._orphan_source_ids(account_id)
                for source_id in source_ids:
                    if source_id in active.get(account_id, frozenset()):
                        protected += 1
                        continue
                    if self._state.mark_orphaned(
                        account_id,
                        source_id,
                        config_revision=policy.config_revision,
                    ) is not None:
                        reconciled += 1
            except Exception:
                failures.append(account_id)
                log.exception(
                    "启动时对账知识索引孤儿状态失败",
                    extra={
                        "account_id": account_id,
                        "resource_type": "account_knowledge_base",
                        "config_revision": policy.config_revision,
                    },
                )
        if failures:
            raise RuntimeError(
                f"以下账号的知识索引孤儿状态对账失败：{','.join(failures)}"
            )
        return KnowledgeIndexReconciliationReport(
            checked_account_count=checked,
            protected_active_source_count=protected,
            reconciled_source_count=reconciled,
        )

    def _orphan_source_ids(self, account_id: str) -> tuple[str, ...]:
        with self._unit_of_work.read() as transaction:
            require_account(
                account_id,
                transaction.session,
                transaction.accounts,
                allow_archived=True,
            )
            sources = transaction.knowledge.list_sources_with_status(
                account_id,
                transaction.session,
                status="indexing",
            )
            return tuple(source.id for source in sources)
