from __future__ import annotations

from domain.models.account import Account
from domain.models.knowledge import (
    AccountKnowledgeBase,
    KnowledgeSource,
)
from errors import DomainError, ErrorCode
from services.accounts.guards import require_account
from services.accounts.lifecycle_sync import AccountLifecycleSynchronizer
from services.accounts.unit_of_work import (
    AccountTransaction,
    AccountUnitOfWork,
)
from services.knowledge.index_types import (
    KnowledgeIndexPlan,
    KnowledgeIndexSource,
)
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

    def plan(
        self,
        account_id: str,
        source_ids: tuple[str, ...] | None,
    ) -> KnowledgeIndexPlan:
        if source_ids is not None and (
            not source_ids or len(set(source_ids)) != len(source_ids)
        ):
            raise _source_invalid(
                "知识索引必须选择不重复的来源"
            )
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
                raise _source_invalid(
                    "知识索引来源不存在、已移除或不属于当前账号"
                )
            return KnowledgeIndexPlan(
                account_id=account_id,
                source_ids=tuple(source.id for source in sources),
            )

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
                raise _source_invalid(
                    "知识索引来源不存在、已移除或不属于当前账号"
                )
            return KnowledgeIndexSource(
                id=source.id,
                source_mode=source.source_mode,
                source_ref=source.source_ref,
                source_url=source.source_url,
            )

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
            updated_account = self._update_account(
                transaction,
                account,
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
        return self._write_source_state(
            account_id,
            source_id,
            source_status="stale",
            content_hash=None,
            base_status=None,
            increment_index_revision=False,
            error_code=None,
            error_log_id=None,
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
        return self._write_source_state(
            account_id,
            source_id,
            source_status="stale",
            content_hash=None,
            base_status=None,
            increment_index_revision=False,
            error_code=ErrorCode.TASK_STATE_CONFLICT.value,
            error_log_id=None,
            task_id=None,
            config_revision=config_revision,
            allow_archived=True,
            missing_ok=True,
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
            updated_account = self._update_account(
                transaction,
                account,
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

    def _update_account(
        self,
        transaction: AccountTransaction,
        account: Account,
        *,
        updated_at: str,
    ) -> Account:
        if self._lifecycle is None:
            raise DomainError(
                ErrorCode.INTERNAL_ERROR,
                "知识索引生命周期同步器尚未装配",
                status_code=500,
                loggable=True,
            )
        return self._lifecycle.update(
            transaction,
            account,
            updated_at=updated_at,
        )


def _locked_resources(
    transaction: AccountTransaction,
    *,
    account_id: str,
    allow_archived: bool,
) -> tuple[Account, AccountKnowledgeBase]:
    transaction.accounts.acquire_write_lock(
        transaction.session,
        account_id=account_id,
    )
    account = require_account(
        account_id,
        transaction.session,
        transaction.accounts,
        allow_archived=allow_archived,
    )
    knowledge_base = transaction.knowledge.get_base(
        account_id,
        transaction.session,
    )
    if knowledge_base is None:
        raise knowledge_base_missing()
    return account, knowledge_base


def _require_source(
    transaction: AccountTransaction,
    *,
    account_id: str,
    source_id: str,
) -> KnowledgeSource:
    source = transaction.knowledge.get_source(
        account_id,
        transaction.session,
        source_id=source_id,
    )
    if source is None or source.deleted_at is not None:
        raise _source_invalid(
            "知识索引来源不存在、已移除或不属于当前账号"
        )
    return source


def _base_error_evidence(
    transaction: AccountTransaction,
    *,
    account_id: str,
    base_status: str,
) -> tuple[str | None, str | None]:
    if base_status != "attention":
        return None, None
    failed = transaction.knowledge.first_source_with_status(
        account_id,
        transaction.session,
        status="failed",
    )
    if failed is None:
        return ErrorCode.KNOWLEDGE_INDEX_FAILED.value, None
    return failed.error_code, failed.error_log_id
def _source_invalid(message: str) -> DomainError:
    return DomainError(
        ErrorCode.KNOWLEDGE_SOURCE_INVALID,
        message,
        status_code=422,
    )
