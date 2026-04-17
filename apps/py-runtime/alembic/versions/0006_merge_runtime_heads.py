"""merge runtime migration heads

Revision ID: 0006_merge_runtime_heads
Revises: 0004_add_prompt_templates_and_video_stage_runs, 0005_add_voice_profiles
Create Date: 2026-04-17
"""
from __future__ import annotations

revision = '0006_merge_runtime_heads'
down_revision = (
    '0004_add_prompt_templates_and_video_stage_runs',
    '0005_add_voice_profiles',
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass