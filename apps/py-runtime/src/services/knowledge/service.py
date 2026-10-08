from __future__ import annotations

from collections.abc import Callable

from common.pagination import CursorPosition
from schemas.v1.knowledge import (
    KnowledgeDto,
    KnowledgeRulesPatchInput,
    KnowledgeSnapshotDto,
    KnowledgeSnapshotInput,
    KnowledgeSnapshotPageDto,
    KnowledgeSourceInput,
    KnowledgeSourcePageDto,
)
from services.accounts.results import AccountServiceResponse
from services.accounts.lifecycle_sync import AccountLifecycleSynchronizer
from services.accounts.unit_of_work import (
    AccountMutationExecutor,
    AccountUnitOfWork,
    MutationExecution,
)
from services.knowledge.content_store import KnowledgeContentStore
from services.knowledge.ports import ControlledFileResolver
from services.knowledge.queries import KnowledgeQueryService
from services.knowledge.rules import KnowledgeRulesService
from services.knowledge.snapshots import KnowledgeSnapshotService
from services.knowledge.sources import KnowledgeSourceService
from services.knowledge.source_material import (
    KnowledgeSourceMaterialPreparer,
)


class AccountKnowledgeService:
    """保留稳定入口，并把知识职责委托给独立纵向模块。"""

    def __init__(
        self,
        unit_of_work: AccountUnitOfWork,
        mutation_executor: AccountMutationExecutor,
        *,
        content_store: KnowledgeContentStore,
        controlled_file_resolver: ControlledFileResolver,
        controlled_file_max_bytes: Callable[[], int],
        lifecycle_synchronizer: AccountLifecycleSynchronizer,
    ) -> None:
        self._queries = KnowledgeQueryService(unit_of_work)
        self._rules = KnowledgeRulesService(unit_of_work)
        self._sources = KnowledgeSourceService(
            mutation_executor,
            material_preparer=KnowledgeSourceMaterialPreparer(
                content_store=content_store,
                controlled_files=controlled_file_resolver,
                max_controlled_file_bytes=controlled_file_max_bytes,
            ),
            lifecycle_synchronizer=lifecycle_synchronizer,
        )
        self._snapshots = KnowledgeSnapshotService(mutation_executor)

    def get(self, account_id: str) -> KnowledgeDto:
        return self._queries.get(account_id)

    def patch_rules(
        self,
        account_id: str,
        payload: KnowledgeRulesPatchInput,
        *,
        expected_revision: int,
    ) -> AccountServiceResponse:
        return self._rules.patch(
            account_id,
            payload,
            expected_revision=expected_revision,
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
        return self._queries.list_sources(
            account_id,
            limit=limit,
            cursor=cursor,
            kind=kind,
            status=status,
        )

    def create_source(
        self,
        account_id: str,
        payload: KnowledgeSourceInput,
        *,
        idempotency_key: str,
    ) -> MutationExecution:
        return self._sources.create(
            account_id,
            payload,
            idempotency_key=idempotency_key,
        )

    def remove_source(
        self,
        account_id: str,
        source_id: str,
        *,
        expected_revision: int,
        idempotency_key: str,
    ) -> MutationExecution:
        return self._sources.remove(
            account_id,
            source_id,
            expected_revision=expected_revision,
            idempotency_key=idempotency_key,
        )

    def list_snapshots(
        self,
        account_id: str,
        *,
        limit: int,
        cursor: CursorPosition | None,
    ) -> tuple[KnowledgeSnapshotPageDto, CursorPosition | None]:
        return self._queries.list_snapshots(
            account_id,
            limit=limit,
            cursor=cursor,
        )

    def get_snapshot(
        self,
        account_id: str,
        snapshot_id: str,
    ) -> KnowledgeSnapshotDto:
        return self._queries.get_snapshot(account_id, snapshot_id)

    def create_snapshot(
        self,
        account_id: str,
        payload: KnowledgeSnapshotInput,
        *,
        idempotency_key: str,
    ) -> MutationExecution:
        return self._snapshots.create(
            account_id,
            payload,
            idempotency_key=idempotency_key,
        )
