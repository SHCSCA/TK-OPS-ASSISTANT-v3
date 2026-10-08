from __future__ import annotations

from uuid import uuid4

from domain.models.knowledge import KnowledgeSource
from errors import DomainError, ErrorCode
from schemas.v1.knowledge import KnowledgeSourceInput
from services.accounts.events import append_account_event
from services.accounts.guards import require_account, require_revision
from services.accounts.idempotency import MutationCommand
from services.accounts.json_codec import dump_json
from services.accounts.lifecycle_sync import AccountLifecycleSynchronizer
from services.accounts.unit_of_work import (
    AccountMutationExecutor,
    AccountTransaction,
    MutationExecution,
    MutationWorkResult,
)
from services.knowledge.presentation import source_to_dto
from services.knowledge.source_material import (
    KnowledgeSourceMaterialPreparer,
)
from services.knowledge.support import (
    knowledge_base_missing,
    knowledge_invalidations,
    knowledge_status_from_source_counts,
    utc_now_text,
)


class KnowledgeSourceService:
    def __init__(
        self,
        mutation_executor: AccountMutationExecutor,
        *,
        material_preparer: KnowledgeSourceMaterialPreparer,
        lifecycle_synchronizer: AccountLifecycleSynchronizer,
    ) -> None:
        self._mutations = mutation_executor
        self._materials = material_preparer
        self._lifecycle = lifecycle_synchronizer

    def create(
        self,
        account_id: str,
        payload: KnowledgeSourceInput,
        *,
        idempotency_key: str,
    ) -> MutationExecution:
        request_payload = payload.model_dump(mode="json")
        stored_refs: list[str] = []
        try:
            execution = self._mutations.execute(
                MutationCommand(
                    account_id=account_id,
                    operation_name="account.knowledge.source.create",
                    idempotency_key=idempotency_key,
                    request_payload=request_payload,
                ),
                lambda transaction: self._create(
                    transaction,
                    account_id=account_id,
                    payload=payload,
                    stored_refs=stored_refs,
                ),
            )
            if execution.replayed:
                self._cleanup_stored_refs(account_id, stored_refs)
            return execution
        except Exception:
            self._cleanup_stored_refs(account_id, stored_refs)
            raise

    def remove(
        self,
        account_id: str,
        source_id: str,
        *,
        expected_revision: int,
        idempotency_key: str,
    ) -> MutationExecution:
        return self._mutations.execute(
            MutationCommand(
                account_id=account_id,
                operation_name="account.knowledge.source.remove",
                idempotency_key=idempotency_key,
                request_payload={
                    "sourceId": source_id,
                    "expectedRevision": expected_revision,
                },
            ),
            lambda transaction: self._remove(
                transaction,
                account_id=account_id,
                source_id=source_id,
                expected_revision=expected_revision,
            ),
        )

    def _create(
        self,
        transaction: AccountTransaction,
        *,
        account_id: str,
        payload: KnowledgeSourceInput,
        stored_refs: list[str],
    ) -> MutationWorkResult:
        transaction.accounts.acquire_write_lock(
            transaction.session,
            account_id=account_id,
        )
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
        source_id = f"ksrc_{uuid4().hex}"
        prepared = self._materials.prepare(
            account_id,
            source_id,
            payload,
            stored_refs=stored_refs,
        )
        now = utc_now_text()
        source = transaction.knowledge.add_source(
            account_id,
            transaction.session,
            KnowledgeSource(
                id=source_id,
                account_id=account_id,
                knowledge_base_id=knowledge_base.id,
                kind=payload.kind,
                name=payload.title.strip(),
                source_ref=prepared.source_ref,
                status="pending",
                content_hash=None,
                metadata_json=dump_json(prepared.metadata),
                error_code=None,
                error_log_id=None,
                revision=1,
                created_at=now,
                updated_at=now,
                deleted_at=None,
                source_mode=payload.sourceMode,
                source_url=prepared.source_url,
            ),
        )
        asset = self._materials.persist_controlled_asset(
            transaction,
            account_id=account_id,
            source_id=source.id,
            prepared=prepared,
            now=now,
        )
        updated_base = transaction.knowledge.set_base_index_state(
            account_id,
            transaction.session,
            status="stale",
            index_revision=int(knowledge_base.index_revision),
            last_indexed_at=knowledge_base.last_indexed_at,
            error_code=None,
            error_log_id=None,
            updated_at=now,
        )
        if updated_base is None:
            raise knowledge_base_missing()
        updated = self._lifecycle.update(
            transaction,
            account,
            updated_at=now,
        )
        dto = source_to_dto(source, asset=asset)
        invalidations = knowledge_invalidations(account_id)
        append_account_event(
            transaction,
            account_id=account_id,
            event_type="knowledge.source.created",
            aggregate_type="knowledge_source",
            aggregate_id=source.id,
            revision=int(updated.revision),
            invalidations=invalidations,
            values={
                "sourceId": source.id,
                "kind": source.kind,
                "sourceMode": source.source_mode,
                "status": source.status,
                "knowledgeStatus": updated_base.status,
                "assetId": None if asset is None else asset.id,
            },
            topic_resource="knowledge",
        )
        return MutationWorkResult(
            response={
                "data": dto.model_dump(mode="json"),
                "meta": {
                    "revision": int(updated.revision),
                    "invalidations": invalidations,
                },
            },
            resource_type="knowledge_source",
            resource_id=source.id,
        )

    def _remove(
        self,
        transaction: AccountTransaction,
        *,
        account_id: str,
        source_id: str,
        expected_revision: int,
    ) -> MutationWorkResult:
        transaction.accounts.acquire_write_lock(
            transaction.session,
            account_id=account_id,
        )
        account = require_account(
            account_id,
            transaction.session,
            transaction.accounts,
        )
        require_revision(account, expected_revision)
        source = transaction.knowledge.get_source(
            account_id,
            transaction.session,
            source_id=source_id,
        )
        if source is None:
            raise DomainError(
                ErrorCode.KNOWLEDGE_SOURCE_NOT_FOUND,
                "知识来源不存在",
                status_code=404,
            )
        asset = transaction.knowledge_assets.get_asset_for_source(
            account_id,
            transaction.session,
            source_id=source_id,
        )
        if source.deleted_at is not None:
            return MutationWorkResult(
                response={
                    "data": source_to_dto(
                        source,
                        asset=asset,
                    ).model_dump(mode="json"),
                    "meta": {
                        "revision": int(account.revision),
                        "invalidations": [],
                    },
                },
                resource_type="knowledge_source",
                resource_id=source.id,
            )
        knowledge_base = transaction.knowledge.get_base(
            account_id,
            transaction.session,
        )
        if knowledge_base is None:
            raise knowledge_base_missing()
        now = utc_now_text()
        source = transaction.knowledge.mark_source_removed(
            account_id,
            transaction.session,
            source_id=source_id,
            removed_at=now,
        )
        if source is None:
            raise DomainError(
                ErrorCode.KNOWLEDGE_SOURCE_NOT_FOUND,
                "知识来源不存在",
                status_code=404,
            )
        base_status = knowledge_status_from_source_counts(
            transaction.knowledge.source_state_counts(
                account_id,
                transaction.session,
            )
        )
        failed_source = (
            transaction.knowledge.first_source_with_status(
                account_id,
                transaction.session,
                status="failed",
            )
            if base_status == "attention"
            else None
        )
        updated_base = transaction.knowledge.set_base_index_state(
            account_id,
            transaction.session,
            status=base_status,
            index_revision=int(knowledge_base.index_revision),
            last_indexed_at=knowledge_base.last_indexed_at,
            error_code=(
                failed_source.error_code
                if failed_source is not None
                else None
            ),
            error_log_id=(
                failed_source.error_log_id
                if failed_source is not None
                else None
            ),
            updated_at=now,
        )
        if updated_base is None:
            raise knowledge_base_missing()
        updated = self._lifecycle.update(
            transaction,
            account,
            updated_at=now,
        )
        invalidations = knowledge_invalidations(account_id)
        append_account_event(
            transaction,
            account_id=account_id,
            event_type="knowledge.source.removed",
            aggregate_type="knowledge_source",
            aggregate_id=source.id,
            revision=int(updated.revision),
            invalidations=invalidations,
            values={
                "sourceId": source.id,
                "status": "removed",
                "knowledgeStatus": updated_base.status,
            },
            topic_resource="knowledge",
        )
        return MutationWorkResult(
            response={
                "data": source_to_dto(
                    source,
                    asset=asset,
                ).model_dump(mode="json"),
                "meta": {
                    "revision": int(updated.revision),
                    "invalidations": invalidations,
                },
            },
            resource_type="knowledge_source",
            resource_id=source.id,
        )

    def _cleanup_stored_refs(
        self,
        account_id: str,
        references: list[str],
    ) -> None:
        self._materials.cleanup(account_id, references)
