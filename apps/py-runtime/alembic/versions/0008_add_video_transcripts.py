"""add video transcripts

Revision ID: 0008_add_video_transcripts
Revises: 0007_add_ai_provider_models_and_browser_instances
Create Date: 2026-04-25
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0008_add_video_transcripts"
down_revision = "0007_add_ai_provider_models_and_browser_instances"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "video_transcripts",
        sa.Column("video_id", sa.String(), nullable=False),
        sa.Column("language", sa.String(), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["video_id"], ["imported_videos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("video_id"),
    )


def downgrade() -> None:
    op.drop_table("video_transcripts")
