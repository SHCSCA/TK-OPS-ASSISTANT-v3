from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from domain.models.base import Base


class VideoStageRun(Base):
    __tablename__ = 'video_stage_runs'

    video_id: Mapped[str] = mapped_column(
        String,
        ForeignKey('imported_videos.id', ondelete='CASCADE'),
        primary_key=True,
    )
    stage_id: Mapped[str] = mapped_column(String, primary_key=True)
    status: Mapped[str] = mapped_column(String, nullable=False)
    progress_pct: Mapped[int] = mapped_column(Integer, nullable=False)
    result_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class VideoTranscript(Base):
    __tablename__ = 'video_transcripts'

    video_id: Mapped[str] = mapped_column(
        String,
        ForeignKey('imported_videos.id', ondelete='CASCADE'),
        primary_key=True,
    )
    language: Mapped[str | None] = mapped_column(String, nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str] = mapped_column(String, nullable=False)
    model: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class VideoDeconstructionArtifact(Base):
    __tablename__ = 'video_deconstruction_artifacts'

    video_id: Mapped[str] = mapped_column(
        String,
        ForeignKey('imported_videos.id', ondelete='CASCADE'),
        primary_key=True,
    )
    artifact_type: Mapped[str] = mapped_column(String, primary_key=True)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str | None] = mapped_column(String, nullable=True)
    model: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)
