from __future__ import annotations

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from domain.models.base import Base


class ProviderProfile(Base):
    """保存系统级 AI Provider 连接配置和健康证据。"""

    __tablename__ = "provider_profiles"
    __table_args__ = (
        CheckConstraint(
            "adapter_type IN "
            "('direct_api','openai_compatible','comfyui','runninghub')",
            name="ck_provider_profiles_adapter",
        ),
        CheckConstraint(
            "health_status IN ('unknown','checking','ready','degraded','failed')",
            name="ck_provider_profiles_health",
        ),
        CheckConstraint(
            "timeout_ms > 0 AND max_concurrency > 0 AND revision >= 1",
            name="ck_provider_profiles_limits",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    adapter_type: Mapped[str] = mapped_column(String, nullable=False)
    base_url: Mapped[str] = mapped_column(Text, nullable=False)
    credential_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    region: Mapped[str | None] = mapped_column(String, nullable=True)
    proxy_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    timeout_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    max_concurrency: Mapped[int] = mapped_column(Integer, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    health_status: Mapped[str] = mapped_column(String, nullable=False)
    last_checked_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String, nullable=True)
    last_error_log_id: Mapped[str | None] = mapped_column(String, nullable=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class ModelProfile(Base):
    """保存 Provider 下可路由的具体模型配置。"""

    __tablename__ = "model_profiles"
    __table_args__ = (
        CheckConstraint(
            "discovery_source IN ('discovered','manual','migrated')",
            name="ck_model_profiles_discovery",
        ),
        CheckConstraint(
            "revision >= 1",
            name="ck_model_profiles_revision",
        ),
        UniqueConstraint(
            "provider_profile_id",
            "model_id",
            name="uq_model_profiles_provider_model",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    provider_profile_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("provider_profiles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    model_id: Mapped[str] = mapped_column(String, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    discovery_source: Mapped[str] = mapped_column(String, nullable=False)
    context_window: Mapped[int | None] = mapped_column(Integer, nullable=True)
    base_limits_json: Mapped[str] = mapped_column(Text, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class ModelCapability(Base):
    """保存模型能力声明、适配器支持和契约验证交集。"""

    __tablename__ = "model_capabilities"
    __table_args__ = (
        CheckConstraint(
            "contract_revision >= 0",
            name="ck_model_capabilities_contract_revision",
        ),
        CheckConstraint(
            "contract_verified = 0 OR verified_at IS NOT NULL",
            name="ck_model_capabilities_verified_at",
        ),
        UniqueConstraint(
            "model_profile_id",
            "capability_key",
            name="uq_model_capabilities_model_key",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    model_profile_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("model_profiles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    capability_key: Mapped[str] = mapped_column(String, nullable=False)
    declared_supported: Mapped[bool] = mapped_column(Boolean, nullable=False)
    adapter_supported: Mapped[bool] = mapped_column(Boolean, nullable=False)
    contract_verified: Mapped[bool] = mapped_column(Boolean, nullable=False)
    input_modalities_json: Mapped[str] = mapped_column(Text, nullable=False)
    output_modalities_json: Mapped[str] = mapped_column(Text, nullable=False)
    parameter_schema_json: Mapped[str] = mapped_column(Text, nullable=False)
    source_urls_json: Mapped[str] = mapped_column(Text, nullable=False)
    known_limits_json: Mapped[str] = mapped_column(Text, nullable=False)
    verified_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    contract_revision: Mapped[int] = mapped_column(Integer, nullable=False)
