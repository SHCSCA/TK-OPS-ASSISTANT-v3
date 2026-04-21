from __future__ import annotations

from sqlalchemy import Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from domain.models.base import Base, generate_uuid


class AICapabilityConfig(Base):
    __tablename__ = "ai_capability_configs"

    capability_id: Mapped[str] = mapped_column(String, primary_key=True)
    enabled: Mapped[int] = mapped_column(Integer, nullable=False)
    provider: Mapped[str] = mapped_column(String, nullable=False)
    model: Mapped[str] = mapped_column(String, nullable=False)
    agent_role: Mapped[str] = mapped_column(Text, nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    user_prompt_template: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class AIProviderSetting(Base):
    __tablename__ = "ai_provider_settings"

    provider_id: Mapped[str] = mapped_column(String, primary_key=True)
    base_url: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class AIProviderModel(Base):
    __tablename__ = "ai_provider_models"
    __table_args__ = (
        UniqueConstraint(
            "provider_id",
            "model_id",
            name="uq_ai_provider_models_provider_model",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    provider_id: Mapped[str] = mapped_column(String, nullable=False)
    model_id: Mapped[str] = mapped_column(String, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    capability_kinds_json: Mapped[str] = mapped_column(Text, nullable=False)
    input_modalities_json: Mapped[str] = mapped_column(Text, nullable=False)
    output_modalities_json: Mapped[str] = mapped_column(Text, nullable=False)
    context_window: Mapped[int | None] = mapped_column(Integer, nullable=True)
    default_for_json: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class AIProviderHealth(Base):
    __tablename__ = "ai_provider_health"

    provider_id: Mapped[str] = mapped_column(String, primary_key=True)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    readiness: Mapped[str] = mapped_column(String, nullable=False)
    last_checked_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)
