from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0012_add_browser_runtime_fields"
down_revision = "0011_add_render_task_error_code"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("browser_instances", sa.Column("process_id", sa.Integer(), nullable=True))
    op.add_column("browser_instances", sa.Column("debug_port", sa.Integer(), nullable=True))
    op.add_column("browser_instances", sa.Column("debug_host", sa.String(), nullable=True))
    op.add_column("browser_instances", sa.Column("runtime_mode", sa.String(), nullable=True))
    op.add_column("browser_instances", sa.Column("executable_path", sa.Text(), nullable=True))
    op.add_column("browser_instances", sa.Column("runtime_evidence_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("browser_instances", "runtime_evidence_json")
    op.drop_column("browser_instances", "executable_path")
    op.drop_column("browser_instances", "runtime_mode")
    op.drop_column("browser_instances", "debug_host")
    op.drop_column("browser_instances", "debug_port")
    op.drop_column("browser_instances", "process_id")
