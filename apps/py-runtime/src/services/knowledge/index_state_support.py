from __future__ import annotations

from domain.models.account import Account
from domain.models.knowledge import AccountKnowledgeBase, KnowledgeSource
from errors import DomainError, ErrorCode
from services.accounts.guards import require_account
from services.accounts.lifecycle_sync import AccountLifecycleSynchronizer
from services.accounts.unit_of_work import AccountTransaction
from services.knowledge.support import knowledge_base_missing


def locked_resources(
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


def require_source(
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
        raise source_invalid(
            "知识索引来源不存在、已移除或不属于当前账号"
        )
    return source


def base_error_evidence(
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


def source_invalid(message: str) -> DomainError:
    return DomainError(
        ErrorCode.KNOWLEDGE_SOURCE_INVALID,
        message,
        status_code=422,
    )


def update_account(
    transaction: AccountTransaction,
    account: Account,
    *,
    lifecycle: AccountLifecycleSynchronizer | None,
    updated_at: str,
) -> Account:
    if lifecycle is None:
        raise DomainError(
            ErrorCode.INTERNAL_ERROR,
            "知识索引生命周期同步器尚未装配",
            status_code=500,
            loggable=True,
        )
    return lifecycle.update(
        transaction,
        account,
        updated_at=updated_at,
    )
