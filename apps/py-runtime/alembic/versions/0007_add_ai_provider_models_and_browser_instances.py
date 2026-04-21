"""add ai provider models and browser instances

Revision ID: 0007_add_ai_provider_models_and_browser_instances
Revises: 0006_merge_runtime_heads
Create Date: 2026-04-21
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0007_add_ai_provider_models_and_browser_instances"
down_revision = "0006_merge_runtime_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_provider_models",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("provider_id", sa.String(), nullable=False),
        sa.Column("model_id", sa.String(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("capability_kinds_json", sa.Text(), nullable=False),
        sa.Column("input_modalities_json", sa.Text(), nullable=False),
        sa.Column("output_modalities_json", sa.Text(), nullable=False),
        sa.Column("context_window", sa.Integer(), nullable=True),
        sa.Column("default_for_json", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.UniqueConstraint("provider_id", "model_id", name="uq_ai_provider_models_provider_model"),
    )
    op.create_table(
        "ai_provider_health",
        sa.Column("provider_id", sa.String(), primary_key=True),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("readiness", sa.String(), nullable=False),
        sa.Column("last_checked_at", sa.Text(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.Text(), nullable=False),
    )
    op.create_table(
        "browser_instances",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("profile_path", sa.Text(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("last_checked_at", sa.DateTime(), nullable=True),
        sa.Column("last_started_at", sa.DateTime(), nullable=True),
        sa.Column("last_stopped_at", sa.DateTime(), nullable=True),
        sa.Column("error_code", sa.String(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["workspace_id"], ["device_workspaces.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("profile_path"),
    )


def downgrade() -> None:
    op.drop_table("browser_instances")
    op.drop_table("ai_provider_health")
    op.drop_table("ai_provider_models")
