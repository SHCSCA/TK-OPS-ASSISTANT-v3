from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0013_add_render_task_timeline_id"
down_revision = "0012_add_browser_runtime_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("render_tasks")}
    if "timeline_id" not in columns:
        op.add_column("render_tasks", sa.Column("timeline_id", sa.String(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("render_tasks")}
    if "timeline_id" in columns:
        op.drop_column("render_tasks", "timeline_id")
