from __future__ import annotations

import logging

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, sessionmaker

from common.time import utc_now_iso
from domain.models.account import Account, AccountGroup, AccountGroupMember

log = logging.getLogger(__name__)


class AccountRepository:
    def __init__(self, *, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def list_accounts(
        self,
        *,
        status: str | None = None,
        platform: str | None = None,
        group_id: str | None = None,
        q: str | None = None,
    ) -> list[Account]:
        with self._session_factory() as session:
            stmt = select(Account).order_by(Account.created_at.desc())
            if status is not None:
                stmt = stmt.where(Account.status == status)
            if platform is not None:
                stmt = stmt.where(Account.platform == platform)
            if group_id is not None:
                # filter through membership
                stmt = stmt.where(
                    Account.id.in_(
                        select(AccountGroupMember.account_id).where(
                            AccountGroupMember.group_id == group_id
                        )
                    )
                )
            if q is not None:
                pattern = f"%{q}%"
                stmt = stmt.where(
                    or_(Account.name.ilike(pattern), Account.username.ilike(pattern))
                )
            accounts = session.scalars(stmt).all()
            session.expunge_all()
            return list(accounts)

    def create_account(self, account: Account) -> Account:
        with self._session_factory() as session:
            session.add(account)
            session.commit()
            session.refresh(account)
            session.expunge(account)
            return account

    def get_account(self, account_id: str) -> Account | None:
        with self._session_factory() as session:
            account = session.get(Account, account_id)
            if account is not None:
                session.expunge(account)
            return account

    def update_account(self, account_id: str, *, changes: dict[str, object]) -> Account | None:
        with self._session_factory() as session:
            account = session.get(Account, account_id)
            if account is None:
                return None
            for key, value in changes.items():
                setattr(account, key, value)
            account.updated_at = _utc_now()
            session.commit()
            session.refresh(account)
            session.expunge(account)
            return account

    def touch_account(self, account_id: str) -> Account | None:
        """更新 updated_at（用于 refresh-stats V1 占位）"""
        return self.update_account(account_id, changes={})

    def delete_account(self, account_id: str) -> bool:
        with self._session_factory() as session:
            account = session.get(Account, account_id)
            if account is None:
                return False
            session.delete(account)
            session.commit()
            return True

    # --- Groups ---

    def list_groups(self) -> list[AccountGroup]:
        with self._session_factory() as session:
            groups = session.scalars(
                select(AccountGroup).order_by(AccountGroup.created_at.asc())
            ).all()
            session.expunge_all()
            return list(groups)

    def create_group(self, group: AccountGroup) -> AccountGroup:
        with self._session_factory() as session:
            session.add(group)
            session.commit()
            session.refresh(group)
            session.expunge(group)
            return group

    def get_group(self, group_id: str) -> AccountGroup | None:
        with self._session_factory() as session:
            group = session.get(AccountGroup, group_id)
            if group is not None:
                session.expunge(group)
            return group

    def update_group(self, group_id: str, *, changes: dict[str, object]) -> AccountGroup | None:
        with self._session_factory() as session:
            group = session.get(AccountGroup, group_id)
            if group is None:
                return None
            for key, value in changes.items():
                setattr(group, key, value)
            session.commit()
            session.refresh(group)
            session.expunge(group)
            return group

    def delete_group(self, group_id: str) -> bool:
        with self._session_factory() as session:
            group = session.get(AccountGroup, group_id)
            if group is None:
                return False
            session.delete(group)
            session.commit()
            return True

    # --- Members ---

    def list_group_members(self, group_id: str) -> list[Account]:
        with self._session_factory() as session:
            account_ids = session.scalars(
                select(AccountGroupMember.account_id).where(
                    AccountGroupMember.group_id == group_id
                )
            ).all()
            if not account_ids:
                return []
            accounts = session.scalars(
                select(Account).where(Account.id.in_(account_ids))
            ).all()
            session.expunge_all()
            return list(accounts)

    def add_group_member(self, member: AccountGroupMember) -> AccountGroupMember:
        with self._session_factory() as session:
            # avoid duplicates
            existing = session.scalar(
                select(AccountGroupMember).where(
                    AccountGroupMember.group_id == member.group_id,
                    AccountGroupMember.account_id == member.account_id,
                )
            )
            if existing is not None:
                session.expunge(existing)
                return existing
            session.add(member)
            session.commit()
            session.refresh(member)
            session.expunge(member)
            return member

    def remove_group_member(self, *, group_id: str, account_id: str) -> bool:
        with self._session_factory() as session:
            member = session.scalar(
                select(AccountGroupMember).where(
                    AccountGroupMember.group_id == group_id,
                    AccountGroupMember.account_id == account_id,
                )
            )
            if member is None:
                return False
            session.delete(member)
            session.commit()
            return True


def _utc_now() -> str:
    return utc_now_iso()
