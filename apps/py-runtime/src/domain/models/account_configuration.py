from __future__ import annotations

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from domain.models.base import Base


class PositioningProfile(Base):
    """保存账号定位的不可覆盖版本。"""

    __tablename__ = "positioning_profiles"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft','active','archived')",
            name="ck_positioning_profiles_status",
        ),
        CheckConstraint(
            "version >= 1 AND revision >= 1",
            name="ck_positioning_profiles_version",
        ),
        UniqueConstraint(
            "account_id",
            "version",
            name="uq_positioning_profiles_account_version",
        ),
        Index(
            "ix_positioning_profiles_account_created",
            "account_id",
            "created_at",
        ),
        Index(
            "uq_positioning_profiles_one_active",
            "account_id",
            unique=True,
            sqlite_where=text("status = 'active'"),
        ),
        Index(
            "uq_positioning_profiles_account_id",
            "account_id",
            "id",
            unique=True,
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    account_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    audience_json: Mapped[str] = mapped_column(Text, nullable=False)
    content_pillars_json: Mapped[str] = mapped_column(Text, nullable=False)
    voice_style_json: Mapped[str] = mapped_column(Text, nullable=False)
    prohibited_terms_json: Mapped[str] = mapped_column(Text, nullable=False)
    publishing_constraints_json: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    activated_at: Mapped[str | None] = mapped_column(Text, nullable=True)


class BrandKit(Base):
    """保存账号品牌资产和表达规则的不可覆盖版本。"""

    __tablename__ = "brand_kits"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft','active','archived')",
            name="ck_brand_kits_status",
        ),
        CheckConstraint(
            "version >= 1 AND revision >= 1",
            name="ck_brand_kits_version",
        ),
        UniqueConstraint(
            "account_id",
            "version",
            name="uq_brand_kits_account_version",
        ),
        Index(
            "ix_brand_kits_account_created",
            "account_id",
            "created_at",
        ),
        Index(
            "uq_brand_kits_one_active",
            "account_id",
            unique=True,
            sqlite_where=text("status = 'active'"),
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    account_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    visual_style_json: Mapped[str] = mapped_column(Text, nullable=False)
    colors_json: Mapped[str] = mapped_column(Text, nullable=False)
    fonts_json: Mapped[str] = mapped_column(Text, nullable=False)
    logo_asset_refs_json: Mapped[str] = mapped_column(Text, nullable=False)
    voice_rules_json: Mapped[str] = mapped_column(Text, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    activated_at: Mapped[str | None] = mapped_column(Text, nullable=True)


class AccountPublishDefaults(Base):
    """保存账号级发布默认值，不触发发布动作。"""

    __tablename__ = "account_publish_defaults"
    __table_args__ = (
        Index(
            "ix_publish_defaults_account_updated",
            "account_id",
            "updated_at",
        ),
    )

    account_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    timezone: Mapped[str] = mapped_column(String, nullable=False)
    privacy_level: Mapped[str] = mapped_column(String, nullable=False)
    allow_comments: Mapped[bool] = mapped_column(Boolean, nullable=False)
    allow_duet: Mapped[bool] = mapped_column(Boolean, nullable=False)
    allow_stitch: Mapped[bool] = mapped_column(Boolean, nullable=False)
    caption_rules_json: Mapped[str] = mapped_column(Text, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class AccountConfigCopyRun(Base):
    """记录账号配置复制的事务结果与可见错误证据。"""

    __tablename__ = "account_config_copy_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('running','succeeded','failed','rolled_back')",
            name="ck_copy_runs_status",
        ),
        CheckConstraint(
            "source_account_id <> target_account_id",
            name="ck_copy_runs_accounts",
        ),
        UniqueConstraint(
            "operation_id",
            name="uq_account_config_copy_runs_operation",
        ),
        Index(
            "ix_copy_runs_source_created",
            "source_account_id",
            "created_at",
        ),
        Index(
            "ix_copy_runs_target_created",
            "target_account_id",
            "created_at",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    source_account_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    target_account_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    requested_sections_json: Mapped[str] = mapped_column(Text, nullable=False)
    copied_sections_json: Mapped[str] = mapped_column(Text, nullable=False)
    skipped_sections_json: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    operation_id: Mapped[str] = mapped_column(String, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String, nullable=True)
    error_log_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    completed_at: Mapped[str | None] = mapped_column(Text, nullable=True)
