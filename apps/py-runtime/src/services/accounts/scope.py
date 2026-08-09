from __future__ import annotations

from dataclasses import dataclass

from services.accounts.types import AccountStatus


@dataclass(frozen=True, slots=True)
class AccountScope:
    account_id: str
    account_revision: int
    status: AccountStatus
    request_id: str
