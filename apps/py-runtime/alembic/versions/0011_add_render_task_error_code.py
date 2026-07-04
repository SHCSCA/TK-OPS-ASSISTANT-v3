from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0011_add_render_task_error_code"
down_revision = "0010_add_structured_script_versions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("render_tasks", sa.Column("error_code", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("render_tasks", "error_code")
