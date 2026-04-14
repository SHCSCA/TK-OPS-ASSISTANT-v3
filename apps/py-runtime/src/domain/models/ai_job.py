from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from domain.models.base import Base


class AIJobRecord(Base):
    __tablename__ = "ai_job_records"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
    )
    capability_id: Mapped[str] = mapped_column(String, nullable=False)
    provider: Mapped[str] = mapped_column(String, nullable=False)
    model: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    provider_request_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    completed_at: Mapped[str | None] = mapped_column(Text, nullable=True)
