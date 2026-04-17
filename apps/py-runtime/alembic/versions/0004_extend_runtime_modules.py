"""extend runtime modules

Revision ID: 0004_extend_runtime_modules
Revises: 0003_add_business_modules
Create Date: 2026-04-17
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0004_extend_runtime_modules"
down_revision = "0003_add_business_modules"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "browser_instances",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("profile_path", sa.Text(), nullable=False),
        sa.Column("browser_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["device_workspaces.id"], ondelete="CASCADE"),
    )

    with op.batch_alter_table("execution_bindings") as batch_op:
        batch_op.add_column(sa.Column("browser_instance_id", sa.String(), nullable=True))
        batch_op.create_foreign_key(
            "fk_execution_bindings_browser_instance_id",
            "browser_instances",
            ["browser_instance_id"],
            ["id"],
            ondelete="SET NULL",
        )

    op.create_table(
        "publish_receipts",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("plan_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("external_url", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["plan_id"], ["publish_plans.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("plan_id"),
    )

    op.create_table(
        "export_profiles",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("format", sa.String(), nullable=False),
        sa.Column("resolution", sa.String(), nullable=False),
        sa.Column("fps", sa.Integer(), nullable=False),
        sa.Column("video_bitrate", sa.String(), nullable=False),
        sa.Column("audio_policy", sa.String(), nullable=False),
        sa.Column("subtitle_policy", sa.String(), nullable=False),
        sa.Column("config_json", sa.Text(), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
    )

    op.create_table(
        "video_transcripts",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("imported_video_id", sa.String(), nullable=False),
        sa.Column("language", sa.String(), nullable=True),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(
            ["imported_video_id"], ["imported_videos.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint("imported_video_id"),
    )

    op.create_table(
        "video_segments",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("imported_video_id", sa.String(), nullable=False),
        sa.Column("segment_index", sa.Integer(), nullable=False),
        sa.Column("start_ms", sa.Integer(), nullable=False),
        sa.Column("end_ms", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(), nullable=True),
        sa.Column("transcript_text", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(
            ["imported_video_id"], ["imported_videos.id"], ondelete="CASCADE"
        ),
    )

    op.create_table(
        "video_structure_extractions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("imported_video_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("script_json", sa.Text(), nullable=True),
        sa.Column("storyboard_json", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(
            ["imported_video_id"], ["imported_videos.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint("imported_video_id"),
    )


def downgrade() -> None:
    op.drop_table("video_structure_extractions")
    op.drop_table("video_segments")
    op.drop_table("video_transcripts")
    op.drop_table("export_profiles")
    op.drop_table("publish_receipts")
    with op.batch_alter_table("execution_bindings") as batch_op:
        batch_op.drop_constraint(
            "fk_execution_bindings_browser_instance_id",
            type_="foreignkey",
        )
        batch_op.drop_column("browser_instance_id")
    op.drop_table("browser_instances")
