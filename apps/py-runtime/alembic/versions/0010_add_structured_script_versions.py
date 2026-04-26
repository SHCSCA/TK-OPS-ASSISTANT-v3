from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0010_add_structured_script_versions"
down_revision = "0009_add_video_deconstruction_artifacts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "script_versions",
        sa.Column("format", sa.String(), nullable=False, server_default="legacy_markdown"),
    )
    op.add_column("script_versions", sa.Column("document_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("script_versions", "document_json")
    op.drop_column("script_versions", "format")
