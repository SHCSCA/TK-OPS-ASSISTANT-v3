from __future__ import annotations

from uuid import uuid4

from domain.models.knowledge import KnowledgeSnapshot
from errors import DomainError, ErrorCode
from schemas.v1.knowledge import KnowledgeSnapshotInput
from services.accounts.events import append_account_event
from services.accounts.guards import require_account
from services.accounts.idempotency import MutationCommand
from services.accounts.json_codec import combined_content_hash, dump_json
from services.accounts.unit_of_work import (
    AccountMutationExecutor,
    AccountTransaction,
    MutationExecution,
    MutationWorkResult,
)
from services.knowledge.presentation import snapshot_to_dto
from services.knowledge.support import (
    bump_account,
    knowledge_base_missing,
    utc_now_text,
)


class KnowledgeSnapshotService:
    def __init__(
        self,
        mutation_executor: AccountMutationExecutor,
    ) -> None:
        self._mutations = mutation_executor

    def create(
        self,
        account_id: str,
        payload: KnowledgeSnapshotInput,
        *,
        idempotency_key: str,
    ) -> MutationExecution:
        return self._mutations.execute(
            MutationCommand(
                account_id=account_id,
                operation_name="account.knowledge.snapshot.create",
                idempotency_key=idempotency_key,
                request_payload=payload.model_dump(mode="json"),
            ),
            lambda transaction: self._create(
                transaction,
                account_id=account_id,
                payload=payload,
            ),
        )

    @staticmethod
    def _create(
        transaction: AccountTransaction,
        *,
        account_id: str,
        payload: KnowledgeSnapshotInput,
    ) -> MutationWorkResult:
        source_ids = tuple(payload.sourceIds)
        if not source_ids or len(set(source_ids)) != len(source_ids):
            raise _snapshot_invalid(
                "知识快照必须选择不重复的可用来源"
            )
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
        sources = transaction.knowledge.get_sources(
            account_id,
            transaction.session,
            source_ids=source_ids,
        )
        if len(sources) != len(source_ids) or any(
            source.status != "ready" or source.content_hash is None
            for source in sources
        ):
            raise _snapshot_invalid(
                "知识快照只能引用当前账号已索引成功的来源"
            )
        manifest = [
            {
                "sourceId": source.id,
                "contentHash": source.content_hash,
                "indexedRevision": int(source.revision),
            }
            for source in sources
        ]
        positioning = transaction.configuration.get_active_positioning(
            account_id,
            transaction.session,
        )
        now = utc_now_text()
        snapshot = transaction.knowledge.add_snapshot(
            account_id,
            transaction.session,
            KnowledgeSnapshot(
                id=f"ksnap_{uuid4().hex}",
                account_id=account_id,
                knowledge_base_id=knowledge_base.id,
                snapshot_version=(
                    transaction.knowledge.next_snapshot_version(
                        account_id,
                        transaction.session,
                    )
                ),
                positioning_profile_id=(
                    None if positioning is None else positioning.id
                ),
                rules_version=int(knowledge_base.rules_version),
                index_revision=int(knowledge_base.index_revision),
                source_manifest_json=dump_json(manifest),
                content_hash=combined_content_hash(
                    {
                        "accountId": account_id,
                        "rulesVersion": knowledge_base.rules_version,
                        "indexRevision": knowledge_base.index_revision,
                        "positioningProfileId": (
                            None if positioning is None else positioning.id
                        ),
                        "sources": manifest,
                    }
                ),
                created_at=now,
                label=(
                    None if payload.label is None else payload.label.strip()
                ),
            ),
        )
        updated = bump_account(
            transaction,
            account_id=account_id,
            expected_revision=int(account.revision),
            updated_at=now,
        )
        dto = snapshot_to_dto(snapshot)
        invalidations = [
            f"account:{account_id}:knowledge",
            f"account:{account_id}:knowledge:snapshots",
        ]
        append_account_event(
            transaction,
            account_id=account_id,
            event_type="knowledge.snapshot.created",
            aggregate_type="knowledge_snapshot",
            aggregate_id=snapshot.id,
            revision=int(updated.revision),
            invalidations=invalidations,
            values={
                "snapshotId": snapshot.id,
                "sourceCount": len(sources),
                "rulesVersion": snapshot.rules_version,
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
            resource_type="knowledge_snapshot",
            resource_id=snapshot.id,
        )


def _snapshot_invalid(message: str) -> DomainError:
    return DomainError(
        ErrorCode.KNOWLEDGE_SNAPSHOT_INVALID,
        message,
        status_code=422,
    )
