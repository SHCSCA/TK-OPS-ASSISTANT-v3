"""add core operational models

Revision ID: 0003_core_operational_models
Revises: 0002_add_imported_videos
Create Date: 2026-04-14
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0003_core_operational_models"
down_revision = "0002_add_imported_videos"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "assets",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("project_id", sa.String(), nullable=True),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("file_name", sa.Text(), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("mime_type", sa.String(), nullable=True),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
    )
    op.create_table(
        "timelines",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("tracks_json", sa.Text(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
    )
    op.create_table(
        "accounts",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("platform", sa.String(), nullable=False),
        sa.Column("handle", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("group_name", sa.Text(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
    )
    op.create_table(
        "device_workspaces",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("device_type", sa.String(), nullable=False),
        sa.Column("root_path", sa.Text(), nullable=False),
        sa.Column("browser_profile", sa.Text(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("health_json", sa.Text(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
    )
    op.create_table(
        "voice_tracks",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("timeline_id", sa.String(), nullable=True),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("provider", sa.String(), nullable=True),
        sa.Column("voice_name", sa.Text(), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=True),
        sa.Column("segments_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["timeline_id"], ["timelines.id"], ondelete="SET NULL"),
    )
    op.create_table(
        "subtitle_tracks",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("timeline_id", sa.String(), nullable=True),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("language", sa.String(), nullable=False),
        sa.Column("style_json", sa.Text(), nullable=False),
        sa.Column("segments_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["timeline_id"], ["timelines.id"], ondelete="SET NULL"),
    )
    op.create_table(
        "execution_bindings",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("account_id", sa.String(), nullable=False),
        sa.Column("device_workspace_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["device_workspace_id"],
            ["device_workspaces.id"],
            ondelete="CASCADE",
        ),
    )
    op.create_table(
        "render_tasks",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("timeline_id", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("output_path", sa.Text(), nullable=True),
        sa.Column("profile_json", sa.Text(), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["timeline_id"], ["timelines.id"], ondelete="SET NULL"),
    )
    op.create_table(
        "automation_tasks",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("project_id", sa.String(), nullable=True),
        sa.Column("binding_id", sa.String(), nullable=True),
        sa.Column("task_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("schedule_json", sa.Text(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["binding_id"],
            ["execution_bindings.id"],
            ondelete="SET NULL",
        ),
    )
    op.create_table(
        "publish_plans",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("account_id", sa.String(), nullable=False),
        sa.Column("binding_id", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("scheduled_at", sa.Text(), nullable=True),
        sa.Column("caption", sa.Text(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["binding_id"],
            ["execution_bindings.id"],
            ondelete="SET NULL",
        ),
    )


def downgrade() -> None:
    op.drop_table("publish_plans")
    op.drop_table("automation_tasks")
    op.drop_table("render_tasks")
    op.drop_table("execution_bindings")
    op.drop_table("subtitle_tracks")
    op.drop_table("voice_tracks")
    op.drop_table("device_workspaces")
    op.drop_table("accounts")
    op.drop_table("timelines")
    op.drop_table("assets")
