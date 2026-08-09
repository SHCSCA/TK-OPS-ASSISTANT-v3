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


class PromptProfile(Base):
    """保存 Prompt 逻辑模板的不可覆盖版本。"""

    __tablename__ = "prompt_profiles"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft','active','archived')",
            name="ck_prompt_profiles_status",
        ),
        CheckConstraint(
            "version >= 1 AND revision >= 1",
            name="ck_prompt_profiles_version",
        ),
        UniqueConstraint(
            "profile_key",
            "version",
            name="uq_prompt_profiles_key_version",
        ),
        Index(
            "uq_prompt_profiles_one_active",
            "profile_key",
            unique=True,
            sqlite_where=text("status = 'active'"),
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    profile_key: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    capability_key: Mapped[str] = mapped_column(String, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    task_template: Mapped[str] = mapped_column(Text, nullable=False)
    variables_schema_json: Mapped[str] = mapped_column(Text, nullable=False)
    output_schema_json: Mapped[str] = mapped_column(Text, nullable=False)
    visual_style_prefix: Mapped[str | None] = mapped_column(Text, nullable=True)
    safety_constraints_json: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String, nullable=False)
    created_from_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("prompt_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    activated_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)


class CapabilityRoute(Base):
    """保存系统能力到模型与 Prompt 版本的原子路由。"""

    __tablename__ = "capability_routes"
    __table_args__ = (
        CheckConstraint(
            "validation_status IN ('valid','incomplete','invalid')",
            name="ck_capability_routes_validation",
        ),
        CheckConstraint(
            "revision >= 1",
            name="ck_capability_routes_revision",
        ),
        UniqueConstraint(
            "capability_key",
            name="uq_capability_routes_key",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    capability_key: Mapped[str] = mapped_column(String, nullable=False)
    primary_model_profile_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("model_profiles.id", ondelete="RESTRICT"),
        nullable=True,
    )
    fallback_model_profile_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("model_profiles.id", ondelete="RESTRICT"),
        nullable=True,
    )
    prompt_profile_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("prompt_profiles.id", ondelete="RESTRICT"),
        nullable=True,
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    validation_status: Mapped[str] = mapped_column(String, nullable=False)
    validation_issues_json: Mapped[str] = mapped_column(Text, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)
