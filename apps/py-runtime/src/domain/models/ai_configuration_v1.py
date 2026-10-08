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

from domain.models.ai_composition import CompositionTemplateProfile
from domain.models.ai_prompt import CapabilityRoute, PromptProfile
from domain.models.ai_provider import ModelCapability, ModelProfile, ProviderProfile
from domain.models.ai_recipe import AccountAIRecipe
from domain.models.base import Base


class ProviderProfileRevision(Base):
    """保存 Provider 的不可变执行配置。"""

    __tablename__ = "provider_profile_revisions"
    __table_args__ = (
        CheckConstraint("revision >= 1", name="ck_provider_revisions_revision"),
        UniqueConstraint(
            "provider_profile_id",
            "revision",
            name="uq_provider_revisions_profile_revision",
        ),
        UniqueConstraint(
            "provider_profile_id",
            "id",
            name="uq_provider_revisions_profile_id",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    provider_profile_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("provider_profiles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    adapter_type: Mapped[str] = mapped_column(String, nullable=False)
    base_url: Mapped[str] = mapped_column(Text, nullable=False)
    base_url_hash: Mapped[str] = mapped_column(String, nullable=False)
    region: Mapped[str | None] = mapped_column(String, nullable=True)
    proxy_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    timeout_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    max_concurrency: Mapped[int] = mapped_column(Integer, nullable=False)
    extra_params_json: Mapped[str] = mapped_column(Text, nullable=False)
    cost_policy_json: Mapped[str] = mapped_column(Text, nullable=False)
    credential_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_hash: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)


class ModelProfileRevision(Base):
    """保存模型与 Provider 修订的不可变绑定。"""

    __tablename__ = "model_profile_revisions"
    __table_args__ = (
        CheckConstraint("revision >= 1", name="ck_model_revisions_revision"),
        UniqueConstraint(
            "model_profile_id",
            "revision",
            name="uq_model_revisions_profile_revision",
        ),
        UniqueConstraint(
            "model_profile_id",
            "id",
            name="uq_model_revisions_profile_id",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    model_profile_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("model_profiles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    provider_profile_revision_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("provider_profile_revisions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    model_id: Mapped[str] = mapped_column(String, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    context_window: Mapped[int | None] = mapped_column(Integer, nullable=True)
    base_limits_json: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)


class CapabilityRouteRevision(Base):
    """保存能力路由草稿、激活状态和执行策略。"""

    __tablename__ = "capability_route_revisions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft','active','archived')",
            name="ck_route_revisions_status",
        ),
        CheckConstraint(
            "revision >= 1 AND timeout_ms > 0 AND max_retries >= 0 "
            "AND max_concurrency > 0 AND max_cost_micros >= 0",
            name="ck_route_revisions_limits",
        ),
        UniqueConstraint(
            "capability_route_id",
            "revision",
            name="uq_route_revisions_route_revision",
        ),
        UniqueConstraint(
            "capability_route_id",
            "id",
            name="uq_route_revisions_route_id",
        ),
        Index(
            "uq_route_revisions_one_active",
            "capability_route_id",
            unique=True,
            sqlite_where=text("status = 'active'"),
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    capability_route_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("capability_routes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    capability_key: Mapped[str] = mapped_column(String, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    prompt_profile_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("prompt_profiles.id", ondelete="RESTRICT"),
        nullable=True,
    )
    candidate_policy_json: Mapped[str] = mapped_column(Text, nullable=False)
    timeout_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False)
    retry_policy_json: Mapped[str] = mapped_column(Text, nullable=False)
    max_concurrency: Mapped[int] = mapped_column(Integer, nullable=False)
    max_cost_micros: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    dependency_snapshot_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("ai_dependency_snapshots.id", ondelete="RESTRICT"),
        nullable=True,
    )
    content_hash: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)

__all__ = [
    "AccountAIRecipe",
    "CapabilityRoute",
    "CapabilityRouteRevision",
    "CompositionTemplateProfile",
    "ModelCapability",
    "ModelProfile",
    "ModelProfileRevision",
    "PromptProfile",
    "ProviderProfile",
    "ProviderProfileRevision",
]
