from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from domain.models.base import Base


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
    )
    kind: Mapped[str] = mapped_column(String, nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_name: Mapped[str] = mapped_column(Text, nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String, nullable=True)
    source: Mapped[str] = mapped_column(String, nullable=False)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
