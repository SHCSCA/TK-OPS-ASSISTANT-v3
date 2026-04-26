from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from domain.models.base import Base


class ScriptVersion(Base):
    __tablename__ = "script_versions"

    project_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("projects.id", ondelete="CASCADE"),
        primary_key=True,
    )
    revision: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    format: Mapped[str] = mapped_column(String, nullable=False, default="legacy_markdown")
    document_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider: Mapped[str | None] = mapped_column(String, nullable=True)
    model: Mapped[str | None] = mapped_column(String, nullable=True)
    ai_job_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("ai_job_records.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
