from __future__ import annotations

from pydantic import BaseModel


class AccountCreateInput(BaseModel):
    name: str
    platform: str = "tiktok"
    username: str | None = None
    avatarUrl: str | None = None
    status: str = "active"
    authExpiresAt: str | None = None
    followerCount: int | None = None
    followingCount: int | None = None
    videoCount: int | None = None
    tags: str | None = None
    notes: str | None = None


class AccountUpdateInput(BaseModel):
    name: str | None = None
    platform: str | None = None
    username: str | None = None
    avatarUrl: str | None = None
    status: str | None = None
    authExpiresAt: str | None = None
    followerCount: int | None = None
    followingCount: int | None = None
    videoCount: int | None = None
    tags: str | None = None
    notes: str | None = None


class AccountDto(BaseModel):
    id: str
    name: str
    platform: str
    username: str | None = None
    avatarUrl: str | None = None
    status: str
    authExpiresAt: str | None = None
    followerCount: int | None = None
    followingCount: int | None = None
    videoCount: int | None = None
    tags: str | None = None
    notes: str | None = None
    createdAt: str
    updatedAt: str


class AccountRefreshStatsDto(BaseModel):
    id: str
    status: str
    updatedAt: str
    providerStatus: str


class AccountGroupCreateInput(BaseModel):
    name: str
    description: str | None = None
    color: str | None = None


class AccountGroupUpdateInput(BaseModel):
    name: str | None = None
    description: str | None = None
    color: str | None = None


class AccountGroupDto(BaseModel):
    id: str
    name: str
    description: str | None = None
    color: str | None = None
    createdAt: str


class AccountGroupMemberCreateInput(BaseModel):
    accountId: str


class AccountBindingUpsertInput(BaseModel):
    browserInstanceId: str
    status: str = "active"
    source: str | None = None
    metadataJson: str | None = None


class AccountBindingDto(BaseModel):
    id: str
    accountId: str
    browserInstanceId: str
    status: str
    source: str | None = None
    maskedMetadataJson: str | None = None
    createdAt: str
    updatedAt: str
