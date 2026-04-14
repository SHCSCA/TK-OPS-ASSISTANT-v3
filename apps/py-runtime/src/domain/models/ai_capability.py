from __future__ import annotations

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from domain.models.base import Base


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
