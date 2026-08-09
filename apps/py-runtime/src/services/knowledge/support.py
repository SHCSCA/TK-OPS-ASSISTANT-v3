from __future__ import annotations

from datetime import UTC, datetime

from domain.models.account import Account
from errors import DomainError, ErrorCode
from services.accounts.unit_of_work import AccountTransaction


def bump_account(
    transaction: AccountTransaction,
    *,
    account_id: str,
    expected_revision: int,
    updated_at: str,
) -> Account:
    updated = transaction.accounts.bump_revision(
        transaction.session,
        account_id=account_id,
        expected_revision=expected_revision,
        updated_at=updated_at,
    )
    if updated is None:
        raise DomainError(
            ErrorCode.REVISION_CONFLICT,
            "账号数据已被更新，请重新加载后再试",
            status_code=412,
        )
    return updated


def knowledge_base_missing() -> DomainError:
    return DomainError(
        ErrorCode.INTERNAL_ERROR,
        "账号知识库尚未初始化，请运行数据修复",
        status_code=500,
        loggable=True,
    )


def latest_snapshot_id(
    transaction: AccountTransaction,
    account_id: str,
) -> str | None:
    latest = transaction.knowledge.latest_snapshot(
        account_id,
        transaction.session,
    )
    return None if latest is None else latest.id


def knowledge_invalidations(account_id: str) -> list[str]:
    return [
        "accounts:list",
        f"account:{account_id}:knowledge",
        f"account:{account_id}:knowledge:sources",
        f"account:{account_id}:workspace",
        f"account:{account_id}:readiness",
    ]


def knowledge_status_from_source_counts(
    counts: dict[str, int],
) -> str:
    total = sum(counts.values())
    if total == 0:
        return "empty"
    if counts.get("indexing", 0):
        return "indexing"
    if counts.get("failed", 0):
        return "attention"
    if counts.get("stale", 0) or counts.get("pending", 0):
        return "stale"
    return "ready"


def utc_now_text() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace(
        "+00:00",
        "Z",
    )
