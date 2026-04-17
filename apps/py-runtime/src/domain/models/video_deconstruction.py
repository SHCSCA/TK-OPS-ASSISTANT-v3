from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from domain.models.base import Base, generate_uuid


class VideoTranscript(Base):
    __tablename__ = "video_transcripts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    imported_video_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("imported_videos.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    language: Mapped[str | None] = mapped_column(String, nullable=True)
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending_provider")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )


class VideoSegment(Base):
    __tablename__ = "video_segments"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    imported_video_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("imported_videos.id", ondelete="CASCADE"),
        nullable=False,
    )
    segment_index: Mapped[int] = mapped_column(Integer, nullable=False)
    start_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    end_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str | None] = mapped_column(String, nullable=True)
    transcript_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )


class VideoStructureExtraction(Base):
    __tablename__ = "video_structure_extractions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    imported_video_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("imported_videos.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending_provider")
    script_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    storyboard_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )
