from __future__ import annotations

import logging
from datetime import datetime
from uuid import uuid4

from fastapi import HTTPException

from domain.models.account import Account, AccountGroup, AccountGroupMember
from repositories.account_repository import AccountRepository
from schemas.accounts import (
    AccountCreateInput,
    AccountDto,
    AccountGroupCreateInput,
    AccountGroupDto,
    AccountGroupMemberCreateInput,
    AccountGroupUpdateInput,
    AccountRefreshStatsDto,
    AccountUpdateInput,
)

log = logging.getLogger(__name__)


class AccountService:
    def __init__(self, repository: AccountRepository) -> None:
        self._repository = repository

    def list_accounts(
        self,
        *,
        status: str | None = None,
        platform: str | None = None,
        group_id: str | None = None,
        q: str | None = None,
    ) -> list[AccountDto]:
        try:
            accounts = self._repository.list_accounts(
                status=status,
                platform=platform,
                group_id=group_id,
                q=q,
            )
        except Exception as exc:
            log.exception("查询账号列表失败")
            raise HTTPException(status_code=500, detail="查询账号列表失败") from exc
        return [self._to_dto(a) for a in accounts]

    def create_account(self, payload: AccountCreateInput) -> AccountDto:
        now = _utc_now()
        account = Account(
            id=str(uuid4()),
            name=payload.name.strip(),
            platform=payload.platform,
            username=payload.username,
            avatar_url=payload.avatarUrl,
            status=payload.status,
            auth_expires_at=payload.authExpiresAt,
            follower_count=payload.followerCount,
            following_count=payload.followingCount,
            video_count=payload.videoCount,
            tags=payload.tags,
            notes=payload.notes,
            created_at=now,
            updated_at=now,
        )
        try:
            saved = self._repository.create_account(account)
        except Exception as exc:
            log.exception("创建账号失败")
            raise HTTPException(status_code=500, detail="创建账号失败") from exc
        return self._to_dto(saved)

    def get_account(self, account_id: str) -> AccountDto:
        try:
            account = self._repository.get_account(account_id)
        except Exception as exc:
            log.exception("查询账号详情失败")
            raise HTTPException(status_code=500, detail="查询账号详情失败") from exc
        if account is None:
            raise HTTPException(status_code=404, detail="账号不存在")
        return self._to_dto(account)

    def update_account(self, account_id: str, payload: AccountUpdateInput) -> AccountDto:
        changes: dict[str, object] = {}
        if payload.name is not None:
            changes["name"] = payload.name.strip()
        if payload.platform is not None:
            changes["platform"] = payload.platform
        if "username" in payload.model_fields_set:
            changes["username"] = payload.username
        if "avatarUrl" in payload.model_fields_set:
            changes["avatar_url"] = payload.avatarUrl
        if payload.status is not None:
            changes["status"] = payload.status
        if "authExpiresAt" in payload.model_fields_set:
            changes["auth_expires_at"] = payload.authExpiresAt
        if "followerCount" in payload.model_fields_set:
            changes["follower_count"] = payload.followerCount
        if "followingCount" in payload.model_fields_set:
            changes["following_count"] = payload.followingCount
        if "videoCount" in payload.model_fields_set:
            changes["video_count"] = payload.videoCount
        if "tags" in payload.model_fields_set:
            changes["tags"] = payload.tags
        if "notes" in payload.model_fields_set:
            changes["notes"] = payload.notes
        try:
            account = self._repository.update_account(account_id, changes=changes)
        except Exception as exc:
            log.exception("更新账号失败")
            raise HTTPException(status_code=500, detail="更新账号失败") from exc
        if account is None:
            raise HTTPException(status_code=404, detail="账号不存在")
        return self._to_dto(account)

    def delete_account(self, account_id: str) -> dict[str, bool]:
        try:
            deleted = self._repository.delete_account(account_id)
        except Exception as exc:
            log.exception("删除账号失败")
            raise HTTPException(status_code=500, detail="删除账号失败") from exc
        if not deleted:
            raise HTTPException(status_code=404, detail="账号不存在")
        return {"deleted": True}

    def refresh_stats(self, account_id: str) -> AccountRefreshStatsDto:
        try:
            account = self._repository.touch_account(account_id)
        except Exception as exc:
            log.exception("刷新账号统计失败")
            raise HTTPException(status_code=500, detail="刷新账号统计失败") from exc
        if account is None:
            raise HTTPException(status_code=404, detail="账号不存在")
        return AccountRefreshStatsDto(
            id=account.id,
            status=account.status,
            updatedAt=account.updated_at,
            providerStatus="pending_provider",
        )

    # --- Groups ---

    def list_groups(self) -> list[AccountGroupDto]:
        try:
            groups = self._repository.list_groups()
        except Exception as exc:
            log.exception("查询账号分组失败")
            raise HTTPException(status_code=500, detail="查询账号分组失败") from exc
        return [self._to_group_dto(g) for g in groups]

    def create_group(self, payload: AccountGroupCreateInput) -> AccountGroupDto:
        group = AccountGroup(
            id=str(uuid4()),
            name=payload.name.strip(),
            description=payload.description,
            color=payload.color,
            created_at=_utc_now(),
        )
        try:
            saved = self._repository.create_group(group)
        except Exception as exc:
            log.exception("创建账号分组失败")
            raise HTTPException(status_code=500, detail="创建账号分组失败") from exc
        return self._to_group_dto(saved)

    def update_group(self, group_id: str, payload: AccountGroupUpdateInput) -> AccountGroupDto:
        changes: dict[str, object] = {}
        if payload.name is not None:
            changes["name"] = payload.name.strip()
        if "description" in payload.model_fields_set:
            changes["description"] = payload.description
        if "color" in payload.model_fields_set:
            changes["color"] = payload.color
        try:
            group = self._repository.update_group(group_id, changes=changes)
        except Exception as exc:
            log.exception("更新账号分组失败")
            raise HTTPException(status_code=500, detail="更新账号分组失败") from exc
        if group is None:
            raise HTTPException(status_code=404, detail="账号分组不存在")
        return self._to_group_dto(group)

    def delete_group(self, group_id: str) -> dict[str, bool]:
        try:
            deleted = self._repository.delete_group(group_id)
        except Exception as exc:
            log.exception("删除账号分组失败")
            raise HTTPException(status_code=500, detail="删除账号分组失败") from exc
        if not deleted:
            raise HTTPException(status_code=404, detail="账号分组不存在")
        return {"deleted": True}

    def list_group_members(self, group_id: str) -> list[AccountDto]:
        self._require_group(group_id)
        try:
            members = self._repository.list_group_members(group_id)
        except Exception as exc:
            log.exception("查询分组成员失败")
            raise HTTPException(status_code=500, detail="查询分组成员失败") from exc
        return [self._to_dto(m) for m in members]

    def add_group_member(self, group_id: str, payload: AccountGroupMemberCreateInput) -> dict[str, object]:
        self._require_group(group_id)
        self.get_account(payload.accountId)
        member = AccountGroupMember(
            id=str(uuid4()),
            group_id=group_id,
            account_id=payload.accountId,
            created_at=_utc_now(),
        )
        try:
            saved = self._repository.add_group_member(member)
        except Exception as exc:
            log.exception("添加分组成员失败")
            raise HTTPException(status_code=500, detail="添加分组成员失败") from exc
        return {
            "id": saved.id,
            "groupId": saved.group_id,
            "accountId": saved.account_id,
            "createdAt": saved.created_at,
        }

    def remove_group_member(self, *, group_id: str, account_id: str) -> dict[str, bool]:
        self._require_group(group_id)
        try:
            deleted = self._repository.remove_group_member(group_id=group_id, account_id=account_id)
        except Exception as exc:
            log.exception("移除分组成员失败")
            raise HTTPException(status_code=500, detail="移除分组成员失败") from exc
        if not deleted:
            raise HTTPException(status_code=404, detail="成员不存在")
        return {"deleted": True}

    def _require_group(self, group_id: str) -> None:
        try:
            group = self._repository.get_group(group_id)
        except Exception as exc:
            log.exception("查询账号分组失败")
            raise HTTPException(status_code=500, detail="查询账号分组失败") from exc
        if group is None:
            raise HTTPException(status_code=404, detail="账号分组不存在")

    def _to_dto(self, account: Account) -> AccountDto:
        return AccountDto(
            id=account.id,
            name=account.name,
            platform=account.platform,
            username=account.username,
            avatarUrl=account.avatar_url,
            status=account.status,
            authExpiresAt=account.auth_expires_at,
            followerCount=account.follower_count,
            followingCount=account.following_count,
            videoCount=account.video_count,
            tags=account.tags,
            notes=account.notes,
            createdAt=account.created_at,
            updatedAt=account.updated_at,
        )

    def _to_group_dto(self, group: AccountGroup) -> AccountGroupDto:
        return AccountGroupDto(
            id=group.id,
            name=group.name,
            description=group.description,
            color=group.color,
            createdAt=group.created_at,
        )


def _utc_now() -> str:
    return datetime.utcnow().isoformat()
