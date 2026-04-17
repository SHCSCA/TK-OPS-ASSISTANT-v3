"""add prompt templates and video stage runs

Revision ID: 0004_add_prompt_templates_and_video_stage_runs
Revises: 0003_add_business_modules
Create Date: 2026-04-17
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0004_add_prompt_templates_and_video_stage_runs"
down_revision = "0003_add_business_modules"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "prompt_templates",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
    )
    op.create_table(
        "video_stage_runs",
        sa.Column("video_id", sa.String(), nullable=False),
        sa.Column("stage_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("progress_pct", sa.Integer(), nullable=False),
        sa.Column("result_summary", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["video_id"], ["imported_videos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("video_id", "stage_id"),
    )


def downgrade() -> None:
    op.drop_table("video_stage_runs")
    op.drop_table("prompt_templates")
