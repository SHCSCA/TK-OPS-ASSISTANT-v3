"""补齐 P0-G 生产加固恢复字段。

Revision ID: 0022_p0g_production_hardening
Revises: 0021_p0g_execution_environment_closure
"""

from __future__ import annotations

import logging

from alembic import op
import sqlalchemy as sa
from sqlalchemy import Connection

from persistence.migration.p0c_account_scope_triggers import (
    P0C_ACCOUNT_SCOPE_TRIGGERS,
)


revision = "0022_p0g_production_hardening"
down_revision = "0021_p0g_execution_environment_closure"
branch_labels = None
depends_on = None

log = logging.getLogger(__name__)


def upgrade() -> None:
    op.add_column(
        "execution_bindings",
        sa.Column("last_task_id", sa.String(), nullable=True),
    )
    op.add_column(
        "execution_bindings",
        sa.Column("last_retry_of_task_id", sa.String(), nullable=True),
    )
    op.create_index(
        "ix_execution_bindings_last_task",
        "execution_bindings",
        ["last_task_id"],
    )


def downgrade() -> None:
    connection = op.get_bind()
    has_recovery_evidence = connection.execute(
        sa.text(
            "SELECT 1 FROM execution_bindings "
            "WHERE last_task_id IS NOT NULL OR last_retry_of_task_id IS NOT NULL "
            "LIMIT 1"
        )
    ).first()
    if has_recovery_evidence:
        log.error("P0-G 生产加固迁移拒绝丢弃恢复证据")
        raise RuntimeError(
            "P0G_HARDENING_DOWNGRADE_REQUIRES_BACKUP: 已存在执行环境恢复证据"
        )
    # SQLite 重建被账号隔离触发器引用的表前必须暂时移除触发器。
    _drop_triggers(connection)
    op.drop_index("ix_execution_bindings_last_task", table_name="execution_bindings")
    with op.batch_alter_table("execution_bindings", recreate="always") as batch:
        batch.drop_column("last_retry_of_task_id")
        batch.drop_column("last_task_id")
    _create_triggers(connection)


def _drop_triggers(connection: Connection) -> None:
    for trigger_name in reversed(tuple(P0C_ACCOUNT_SCOPE_TRIGGERS)):
        connection.execute(sa.text(f'DROP TRIGGER IF EXISTS "{trigger_name}"'))


def _create_triggers(connection: Connection) -> None:
    for statement in P0C_ACCOUNT_SCOPE_TRIGGERS.values():
        connection.execute(sa.text(statement))
