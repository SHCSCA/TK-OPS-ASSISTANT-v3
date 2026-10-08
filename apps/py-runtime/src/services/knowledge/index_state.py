from __future__ import annotations

from uuid import uuid4

from domain.models.account_asset import KnowledgeIndexChunk
from errors import DomainError, ErrorCode
from services.accounts.lifecycle_sync import AccountLifecycleSynchronizer
from services.accounts.unit_of_work import AccountUnitOfWork
from services.knowledge.index_types import KnowledgeIndexChunkWrite, KnowledgeIndexPlan, KnowledgeIndexSource
from services.knowledge.index_state_support import (
    base_error_evidence as _base_error_evidence,
    locked_resources as _locked_resources,
    require_source as _require_source,
    source_invalid as _source_invalid,
    update_account as _update_account,
)
from services.knowledge.index_planning import KnowledgeIndexPlanner
from services.knowledge.index_events import append_knowledge_index_event
from services.knowledge.support import (
    knowledge_base_missing,
    knowledge_status_from_source_counts,
    utc_now_text,
)


class KnowledgeIndexStateStore:
    def __init__(
        self,
        unit_of_work: AccountUnitOfWork,
        *,
        lifecycle_synchronizer: AccountLifecycleSynchronizer | None = None,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._lifecycle = lifecycle_synchronizer
        self._planner = KnowledgeIndexPlanner(unit_of_work)

    def plan(
        self,
        account_id: str,
        source_ids: tuple[str, ...] | None,
    ) -> KnowledgeIndexPlan:
        return self._planner.plan(account_id, source_ids)

    def source(
        self,
        account_id: str,
        source_id: str,
    ) -> KnowledgeIndexSource:
        return self._planner.source(account_id, source_id)

    def mark_indexing(
        self,
        account_id: str,
        source_id: str,
        *,
        task_id: str,
        config_revision: int,
    ) -> int:
        return self._write_source_state(
            account_id,
            source_id,
            source_status="indexing",
            content_hash=None,
            base_status="indexing",
            increment_index_revision=False,
            error_code=None,
            error_log_id=None,
            task_id=task_id,
            config_revision=config_revision,
        )

    def mark_ready(
        self,
        account_id: str,
        source_id: str,
        *,
        content_hash: str,
        asset_status: str,
        chunks: tuple[KnowledgeIndexChunkWrite, ...],
        task_id: str,
        config_revision: int,
    ) -> int:
        with self._unit_of_work.write() as transaction:
            account, knowledge_base = _locked_resources(
                transaction,
                account_id=account_id,
                allow_archived=False,
            )
            current = _require_source(
                transaction,
                account_id=account_id,
                source_id=source_id,
            )
            if current.status != "indexing":
                raise DomainError(
                    ErrorCode.TASK_STATE_CONFLICT,
                    "知识来源索引状态已变化，不能写入过期结果",
                    status_code=409,
                )
            now = utc_now_text()
            updated_source = transaction.knowledge.set_source_index_state(
                account_id,
                transaction.session,
                source_id=source_id,
                status="ready",
                content_hash=content_hash,
                error_code=None,
                error_log_id=None,
                updated_at=now,
            )
            if updated_source is None:
                raise _source_invalid("知识来源已在索引期间移除")
            transaction.knowledge_assets.add_chunks(
                account_id,
                transaction.session,
                (
                    KnowledgeIndexChunk(
                        id=f"kchunk_{uuid4().hex}",
                        account_id=account_id,
                        knowledge_source_id=source_id,
                        source_revision=int(updated_source.revision),
                        ordinal=chunk.ordinal,
                        content_ref=chunk.content_ref,
                        content_hash=chunk.content_hash,
                        token_count=chunk.token_count,
                        extractor_version=chunk.extractor_version,
                        created_at=now,
                    )
                    for chunk in chunks
                ),
            )
            updated_asset = (
                transaction.knowledge_assets.set_asset_state_for_source(
                    account_id,
                    transaction.session,
                    source_id=source_id,
                    status=asset_status,
                    content_hash=content_hash,
                    error_code=None,
                    error_log_id=None,
                    updated_at=now,
                )
            )
            if current.source_mode == "file" and updated_asset is None:
                raise DomainError(
                    ErrorCode.INTERNAL_ERROR,
                    "受控文件来源缺少账号资产关联",
                    status_code=500,
                    loggable=True,
                )
            counts = transaction.knowledge.source_state_counts(
                account_id,
                transaction.session,
            )
            base_status = knowledge_status_from_source_counts(counts)
            base_error_code, base_error_log_id = _base_error_evidence(
                transaction,
                account_id=account_id,
                base_status=base_status,
            )
            updated_base = transaction.knowledge.set_base_index_state(
                account_id,
                transaction.session,
                status=base_status,
                index_revision=int(knowledge_base.index_revision) + 1,
                last_indexed_at=now,
                error_code=base_error_code,
                error_log_id=base_error_log_id,
                updated_at=now,
            )
            if updated_base is None:
                raise knowledge_base_missing()
            updated_account = _update_account(
                transaction,
                account,
                lifecycle=self._lifecycle,
                updated_at=now,
            )
            append_knowledge_index_event(
                transaction,
                account_id=account_id,
                source_id=source_id,
                source_status="ready",
                base_status=base_status,
                account_revision=int(updated_account.revision),
                task_id=task_id,
                config_revision=config_revision,
                error_code=None,
                error_log_id=None,
            )
            return int(updated_account.revision)

    def mark_failed(
        self,
        account_id: str,
        source_id: str,
        *,
        error_code: str,
        error_log_id: str,
        task_id: str,
        config_revision: int,
    ) -> int | None:
        return self._write_source_state(
            account_id,
            source_id,
            source_status="failed",
            content_hash=None,
            base_status="attention",
            increment_index_revision=False,
            error_code=error_code,
            error_log_id=error_log_id,
            task_id=task_id,
            config_revision=config_revision,
            allow_archived=True,
            missing_ok=True,
        )

    def mark_cancelled(
        self,
        account_id: str,
        source_id: str,
        *,
        task_id: str,
        config_revision: int,
    ) -> int | None:
        return self.mark_stale(
            account_id,
            source_id,
            error_code=None,
            error_log_id=None,
            task_id=task_id,
            config_revision=config_revision,
            base_status=None,
        )

    def mark_stale(
        self,
        account_id: str,
        source_id: str,
        *,
        error_code: str | None,
        error_log_id: str | None,
        task_id: str | None,
        config_revision: int,
        base_status: str | None = "stale",
    ) -> int | None:
        return self._write_source_state(
            account_id,
            source_id,
            source_status="stale",
            content_hash=None,
            base_status=base_status,
            increment_index_revision=False,
            error_code=error_code,
            error_log_id=error_log_id,
            task_id=task_id,
            config_revision=config_revision,
            allow_archived=True,
            missing_ok=True,
        )

    def mark_orphaned(
        self,
        account_id: str,
        source_id: str,
        *,
        config_revision: int,
    ) -> int | None:
        return self.mark_stale(
            account_id,
            source_id,
            error_code=ErrorCode.TASK_STATE_CONFLICT.value,
            error_log_id=None,
            task_id=None,
            config_revision=config_revision,
            base_status=None,
        )

    def _write_source_state(
        self,
        account_id: str,
        source_id: str,
        *,
        source_status: str,
        content_hash: str | None,
        base_status: str | None,
        increment_index_revision: bool,
        error_code: str | None,
        error_log_id: str | None,
        task_id: str | None,
        config_revision: int,
        allow_archived: bool = False,
        missing_ok: bool = False,
    ) -> int | None:
        with self._unit_of_work.write() as transaction:
            account, knowledge_base = _locked_resources(
                transaction,
                account_id=account_id,
                allow_archived=allow_archived,
            )
            source = transaction.knowledge.get_source(
                account_id,
                transaction.session,
                source_id=source_id,
            )
            if source is None or source.deleted_at is not None:
                if missing_ok:
                    return None
                raise _source_invalid(
                    "知识索引来源不存在、已移除或不属于当前账号"
                )
            now = utc_now_text()
            retained_hash = (
                source.content_hash
                if content_hash is None
                else content_hash
            )
            updated_source = transaction.knowledge.set_source_index_state(
                account_id,
                transaction.session,
                source_id=source_id,
                status=source_status,
                content_hash=retained_hash,
                error_code=error_code,
                error_log_id=error_log_id,
                updated_at=now,
            )
            if updated_source is None:
                if missing_ok:
                    return None
                raise _source_invalid("知识来源已在索引期间移除")
            asset_status = {
                "indexing": "pending",
                "failed": "failed",
                "stale": "stale",
            }.get(source_status)
            if asset_status is not None:
                transaction.knowledge_assets.set_asset_state_for_source(
                    account_id,
                    transaction.session,
                    source_id=source_id,
                    status=asset_status,
                    content_hash=content_hash,
                    error_code=error_code,
                    error_log_id=error_log_id,
                    updated_at=now,
                )
            resolved_base_status = (
                base_status
                or knowledge_status_from_source_counts(
                    transaction.knowledge.source_state_counts(
                        account_id,
                        transaction.session,
                    )
                )
            )
            base_error_code = error_code
            base_error_log_id = error_log_id
            if resolved_base_status == "attention" and error_code is None:
                base_error_code, base_error_log_id = _base_error_evidence(
                    transaction,
                    account_id=account_id,
                    base_status=resolved_base_status,
                )
            updated_base = transaction.knowledge.set_base_index_state(
                account_id,
                transaction.session,
                status=resolved_base_status,
                index_revision=(
                    int(knowledge_base.index_revision) + 1
                    if increment_index_revision
                    else int(knowledge_base.index_revision)
                ),
                last_indexed_at=knowledge_base.last_indexed_at,
                error_code=base_error_code,
                error_log_id=base_error_log_id,
                updated_at=now,
            )
            if updated_base is None:
                raise knowledge_base_missing()
            updated_account = _update_account(
                transaction,
                account,
                lifecycle=self._lifecycle,
                updated_at=now,
            )
            append_knowledge_index_event(
                transaction,
                account_id=account_id,
                source_id=source_id,
                source_status=source_status,
                base_status=resolved_base_status,
                account_revision=int(updated_account.revision),
                task_id=task_id,
                config_revision=config_revision,
                error_code=error_code,
                error_log_id=error_log_id,
            )
            return int(updated_account.revision)
