from __future__ import annotations

from sqlalchemy import (
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


class AccountAIRecipe(Base):
    """保存账号级 AI 配方的不可覆盖版本。"""

    __tablename__ = "account_ai_recipes"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft','active','archived')",
            name="ck_account_ai_recipes_status",
        ),
        CheckConstraint(
            "validation_status IN ('valid','incomplete','invalid')",
            name="ck_account_ai_recipes_validation",
        ),
        CheckConstraint(
            "length(content_hash) = 64 "
            "AND content_hash NOT GLOB '*[^0-9a-f]*'",
            name="ck_account_ai_recipes_content_hash",
        ),
        CheckConstraint(
            "version >= 1 AND revision >= 1",
            name="ck_account_ai_recipes_version",
        ),
        UniqueConstraint(
            "account_id",
            "version",
            name="uq_account_ai_recipes_version",
        ),
        Index(
            "ix_account_ai_recipes_account_created",
            "account_id",
            "created_at",
        ),
        Index(
            "uq_account_ai_recipes_one_active",
            "account_id",
            unique=True,
            sqlite_where=text("status = 'active'"),
        ),
        Index(
            "uq_account_ai_recipes_account_id",
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
    name: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    route_overrides_json: Mapped[str] = mapped_column(Text, nullable=False)
    visual_style_json: Mapped[str] = mapped_column(Text, nullable=False)
    voice_profile_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    composition_template_ref: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("composition_template_profiles.id", ondelete="RESTRICT"),
        nullable=True,
    )
    cost_policy_json: Mapped[str] = mapped_column(Text, nullable=False)
    fallback_policy_json: Mapped[str] = mapped_column(Text, nullable=False)
    dependency_snapshot_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("ai_dependency_snapshots.id", ondelete="RESTRICT"),
        nullable=True,
    )
    source_ai_config_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    validation_status: Mapped[str] = mapped_column(String, nullable=False)
    validation_issues_json: Mapped[str] = mapped_column(Text, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    created_from_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("account_ai_recipes.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    activated_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_hash: Mapped[str] = mapped_column(String, nullable=False)
