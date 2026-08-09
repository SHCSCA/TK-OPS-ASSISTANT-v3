from __future__ import annotations

from sqlalchemy.orm import Session

from domain.models.account import Account
from errors import DomainError, ErrorCode
from repositories.account_workspace_v1_repository import (
    AccountWorkspaceV1Repository,
)


def require_account(
    account_id: str,
    session: Session,
    repository: AccountWorkspaceV1Repository,
    *,
    allow_archived: bool = False,
) -> Account:
    account = repository.get(session, account_id)
    if account is None:
        raise DomainError(
            ErrorCode.ACCOUNT_NOT_FOUND,
            "账号不存在或已移除",
            status_code=404,
        )
    if account.status == "archived" and not allow_archived:
        raise DomainError(
            ErrorCode.ACCOUNT_ARCHIVED,
            "账号已归档，请先恢复后再操作",
            status_code=409,
        )
    return account


def require_revision(
    account: Account,
    expected_revision: int,
) -> None:
    if int(account.revision) == expected_revision:
        return
    raise revision_conflict(account)


def revision_conflict(account: Account) -> DomainError:
    return DomainError(
        ErrorCode.REVISION_CONFLICT,
        "账号数据已被更新，请重新加载后再试",
        status_code=412,
        meta={
            "currentRevision": int(account.revision),
            "invalidations": [
                f"account:{account.id}:detail",
                f"account:{account.id}:workspace",
            ],
        },
    )
