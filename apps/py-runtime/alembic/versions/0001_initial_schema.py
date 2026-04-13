"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-04-13
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "system_config",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("document", sa.Text(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.CheckConstraint("id = 1"),
    )
    op.create_table(
        "license_grant",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("active", sa.Integer(), nullable=False),
        sa.Column("restricted_mode", sa.Integer(), nullable=False),
        sa.Column("machine_id", sa.Text(), nullable=False),
        sa.Column("machine_bound", sa.Integer(), nullable=False),
        sa.Column("activation_mode", sa.Text(), nullable=False),
        sa.Column("masked_code", sa.Text(), nullable=False),
        sa.Column("activated_at", sa.Text(), nullable=True),
        sa.Column("machine_code", sa.Text(), nullable=False),
        sa.Column("license_type", sa.Text(), nullable=False),
        sa.Column("signed_payload", sa.Text(), nullable=False),
        sa.CheckConstraint("id = 1"),
    )
    op.create_table(
        "session_context",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("current_project_id", sa.String(), nullable=True),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.CheckConstraint("id = 1"),
    )
    op.create_table(
        "projects",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("current_script_version", sa.Integer(), nullable=False),
        sa.Column("current_storyboard_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.Column("last_accessed_at", sa.Text(), nullable=False),
    )
    op.create_table(
        "ai_capability_configs",
        sa.Column("capability_id", sa.String(), primary_key=True),
        sa.Column("enabled", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("agent_role", sa.Text(), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("user_prompt_template", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
    )
    op.create_table(
        "ai_provider_settings",
        sa.Column("provider_id", sa.String(), primary_key=True),
        sa.Column("base_url", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
    )
    op.create_table(
        "ai_job_records",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("project_id", sa.String(), nullable=True),
        sa.Column("capability_id", sa.String(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("provider_request_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("completed_at", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
    )
    op.create_table(
        "script_versions",
        sa.Column("project_id", sa.String(), primary_key=True),
        sa.Column("revision", sa.Integer(), primary_key=True),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("provider", sa.String(), nullable=True),
        sa.Column("model", sa.String(), nullable=True),
        sa.Column("ai_job_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ai_job_id"], ["ai_job_records.id"], ondelete="SET NULL"),
    )
    op.create_table(
        "storyboard_versions",
        sa.Column("project_id", sa.String(), primary_key=True),
        sa.Column("revision", sa.Integer(), primary_key=True),
        sa.Column("based_on_script_revision", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("scenes_json", sa.Text(), nullable=False),
        sa.Column("provider", sa.String(), nullable=True),
        sa.Column("model", sa.String(), nullable=True),
        sa.Column("ai_job_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ai_job_id"], ["ai_job_records.id"], ondelete="SET NULL"),
    )


def downgrade() -> None:
    op.drop_table("storyboard_versions")
    op.drop_table("script_versions")
    op.drop_table("ai_job_records")
    op.drop_table("ai_provider_settings")
    op.drop_table("ai_capability_configs")
    op.drop_table("projects")
    op.drop_table("session_context")
    op.drop_table("license_grant")
    op.drop_table("system_config")
