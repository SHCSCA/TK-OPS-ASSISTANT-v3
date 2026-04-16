from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from domain.models.base import Base, generate_uuid


class ReviewSummary(Base):
    __tablename__ = "review_summaries"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    project_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_views: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_likes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_comments: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_watch_time_sec: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    completion_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    suggestions_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_analyzed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )
