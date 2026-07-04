from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0014_magic_cut_suggestion_drafts"
down_revision = "0013_add_render_task_timeline_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "magic_cut_suggestion_drafts" not in inspector.get_table_names():
        op.create_table(
            "magic_cut_suggestion_drafts",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column(
                "project_id",
                sa.String(),
                sa.ForeignKey("projects.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "timeline_id",
                sa.String(),
                sa.ForeignKey("timelines.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "ai_job_id",
                sa.String(),
                sa.ForeignKey("ai_job_records.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("summary", sa.Text(), nullable=False),
            sa.Column("operations_json", sa.Text(), nullable=False),
            sa.Column("timeline_version_token", sa.Text(), nullable=False),
            sa.Column("created_at", sa.Text(), nullable=False),
            sa.Column("updated_at", sa.Text(), nullable=False),
            sa.Column("applied_at", sa.Text(), nullable=True),
        )
    indexes = {index["name"] for index in inspector.get_indexes("magic_cut_suggestion_drafts")}
    if "idx_magic_cut_suggestions_project_timeline" not in indexes:
        op.create_index(
            "idx_magic_cut_suggestions_project_timeline",
            "magic_cut_suggestion_drafts",
            ["project_id", "timeline_id", "created_at"],
        )
    if "idx_magic_cut_suggestions_status" not in indexes:
        op.create_index(
            "idx_magic_cut_suggestions_status",
            "magic_cut_suggestion_drafts",
            ["status"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "magic_cut_suggestion_drafts" not in inspector.get_table_names():
        return
    indexes = {index["name"] for index in inspector.get_indexes("magic_cut_suggestion_drafts")}
    if "idx_magic_cut_suggestions_status" in indexes:
        op.drop_index("idx_magic_cut_suggestions_status", table_name="magic_cut_suggestion_drafts")
    if "idx_magic_cut_suggestions_project_timeline" in indexes:
        op.drop_index(
            "idx_magic_cut_suggestions_project_timeline",
            table_name="magic_cut_suggestion_drafts",
        )
    op.drop_table("magic_cut_suggestion_drafts")
