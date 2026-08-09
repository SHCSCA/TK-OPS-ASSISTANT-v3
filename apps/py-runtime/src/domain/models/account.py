from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from domain.models.base import Base


class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = (
        CheckConstraint(
            "id IS NOT NULL "
            "AND length(id) BETWEEN 1 AND 128 "
            "AND substr(id, 1, 1) GLOB '[A-Za-z0-9]' "
            "AND id NOT GLOB '*[^A-Za-z0-9._-]*'",
            name="ck_accounts_stable_id",
        ),
        CheckConstraint(
            "status IN ('draft','unbound','ready','attention','archived')",
            name="ck_accounts_status",
        ),
        CheckConstraint("revision >= 1", name="ck_accounts_revision"),
        Index("ix_accounts_status_last_used", "status", "last_used_at"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    platform: Mapped[str] = mapped_column(String, nullable=False, default="tiktok")
    username: Mapped[str | None] = mapped_column(Text, nullable=True)
    platform_account_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="draft")
    wizard_completed_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    status_reason_code: Mapped[str | None] = mapped_column(String, nullable=True)
    last_used_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_health_checked_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    archived_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    auth_expires_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    follower_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    following_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    video_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tags: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON 数组字符串
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_validated_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class AccountGroup(Base):
    __tablename__ = "account_groups"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    color: Mapped[str | None] = mapped_column(String, nullable=True)  # 十六进制颜色
    created_at: Mapped[str] = mapped_column(Text, nullable=False)


class AccountGroupMember(Base):
    __tablename__ = "account_group_members"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    group_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("account_groups.id", ondelete="CASCADE"),
        nullable=False,
    )
    account_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
