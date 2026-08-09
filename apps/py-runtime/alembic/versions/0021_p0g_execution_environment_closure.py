"""补齐 P0-G 执行环境与登录会话生产字段。

Revision ID: 0021_p0g_execution_environment_closure
Revises: 0020_p0e_ai_vertical_chain
"""

from __future__ import annotations

import logging

from alembic import op
import sqlalchemy as sa
from sqlalchemy import Connection

from persistence.migration.p0c_account_scope_triggers import (
    P0C_ACCOUNT_SCOPE_TRIGGERS,
)

revision = "0021_p0g_execution_environment_closure"
down_revision = "0020_p0e_ai_vertical_chain"
branch_labels = None
depends_on = None

log = logging.getLogger(__name__)


def upgrade() -> None:
    _expand_execution_objects()
    _backfill_legacy_ownership()
    _create_login_sessions()
    _create_indexes()


def downgrade() -> None:
    _refuse_data_bearing_downgrade()
    connection = op.get_bind()
    # SQLite 重建被触发器引用的表前必须暂时移除账号隔离触发器。
    _drop_triggers(connection)
    op.drop_index("uq_account_login_sessions_active", table_name="account_login_sessions")
    op.drop_index(
        "ix_account_login_sessions_account_updated",
        table_name="account_login_sessions",
    )
    op.drop_table("account_login_sessions")
    op.drop_index("uq_execution_bindings_active_account", table_name="execution_bindings")
    op.drop_index("uq_device_workspaces_root_ref", table_name="device_workspaces")
    with op.batch_alter_table("execution_bindings", recreate="always") as batch:
        batch.drop_column("error_log_id")
        batch.drop_column("error_code")
        batch.drop_column("revision")
    with op.batch_alter_table("browser_instances", recreate="always") as batch:
        batch.drop_column("error_log_id")
        batch.drop_column("revision")
        batch.drop_column("ownership_state")
    with op.batch_alter_table("device_workspaces", recreate="always") as batch:
        batch.drop_column("error_log_id")
        batch.drop_column("error_code")
        batch.drop_column("revision")
        batch.drop_column("ownership_state")
        batch.drop_column("root_ref")
    _create_triggers(connection)


def _refuse_data_bearing_downgrade() -> None:
    connection = op.get_bind()
    blockers: list[str] = []
    checks = {
        "account_login_sessions": "SELECT 1 FROM account_login_sessions LIMIT 1",
        "device_workspaces.root_ref": (
            "SELECT 1 FROM device_workspaces "
            "WHERE root_ref IS NOT NULL OR ownership_state = 'owned' "
            "OR revision > 1 OR error_code IS NOT NULL OR error_log_id IS NOT NULL "
            "LIMIT 1"
        ),
        "browser_instances.ownership_state": (
            "SELECT 1 FROM browser_instances "
            "WHERE ownership_state = 'owned' OR revision > 1 "
            "OR error_log_id IS NOT NULL LIMIT 1"
        ),
        "execution_bindings.revision": (
            "SELECT 1 FROM execution_bindings "
            "WHERE revision > 1 OR error_code IS NOT NULL "
            "OR error_log_id IS NOT NULL LIMIT 1"
        ),
    }
    for name, statement in checks.items():
        if connection.execute(sa.text(statement)).first():
            blockers.append(name)
    if not blockers:
        return
    names = ", ".join(blockers)
    log.error(
        "P0-G 迁移拒绝有数据降级",
        extra={"downgrade_blockers": names},
    )
    raise RuntimeError(
        "P0G_DOWNGRADE_REQUIRES_BACKUP: 已存在执行环境或登录会话数据，"
        f"禁止自动降级；请恢复迁移前备份。涉及对象：{names}"
    )


def _drop_triggers(connection: Connection) -> None:
    for trigger_name in reversed(tuple(P0C_ACCOUNT_SCOPE_TRIGGERS)):
        connection.execute(sa.text(f'DROP TRIGGER IF EXISTS "{trigger_name}"'))


def _create_triggers(connection: Connection) -> None:
    for statement in P0C_ACCOUNT_SCOPE_TRIGGERS.values():
        connection.execute(sa.text(statement))


def _expand_execution_objects() -> None:
    op.add_column("device_workspaces", sa.Column("root_ref", sa.String(), nullable=True))
    op.add_column(
        "device_workspaces",
        sa.Column(
            "ownership_state",
            sa.String(),
            nullable=False,
            server_default="legacy_unclaimed",
        ),
    )
    op.add_column(
        "device_workspaces",
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column("device_workspaces", sa.Column("error_code", sa.String()))
    op.add_column("device_workspaces", sa.Column("error_log_id", sa.String()))
    op.add_column(
        "browser_instances",
        sa.Column(
            "ownership_state",
            sa.String(),
            nullable=False,
            server_default="legacy_unclaimed",
        ),
    )
    op.add_column(
        "browser_instances",
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column("browser_instances", sa.Column("error_log_id", sa.String()))
    op.add_column(
        "execution_bindings",
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column("execution_bindings", sa.Column("error_code", sa.String()))
    op.add_column("execution_bindings", sa.Column("error_log_id", sa.String()))


def _backfill_legacy_ownership() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            UPDATE device_workspaces
            SET ownership_state = CASE
                WHEN account_id IS NULL THEN 'legacy_unclaimed'
                ELSE 'needs_reauthorization'
            END
            """
        )
    )
    connection.execute(
        sa.text(
            """
            UPDATE browser_instances
            SET ownership_state = CASE
                WHEN account_id IS NULL THEN 'legacy_unclaimed'
                ELSE 'needs_reauthorization'
            END
            """
        )
    )
    connection.execute(
        sa.text(
            "UPDATE execution_bindings SET status = 'inactive' "
            "WHERE status NOT IN ('deleting', 'cleanup_failed')"
        )
    )


def _create_login_sessions() -> None:
    op.create_table(
        "account_login_sessions",
        sa.Column("id", sa.String(), primary_key=True, nullable=False),
        sa.Column("account_id", sa.String(), nullable=False),
        sa.Column("execution_binding_id", sa.String(), nullable=False),
        sa.Column("browser_instance_id", sa.String(), nullable=False),
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("prepare_task_id", sa.String(), nullable=True),
        sa.Column("probe_task_id", sa.String(), nullable=True),
        sa.Column("expected_identity", sa.Text(), nullable=False),
        sa.Column("detected_identity", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.Text(), nullable=False),
        sa.Column("error_code", sa.String(), nullable=True),
        sa.Column("error_log_id", sa.String(), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["account_id"], ["accounts.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["execution_binding_id"],
            ["execution_bindings.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["browser_instance_id"],
            ["browser_instances.id"],
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "state IN ('preparing','waiting_user','probing','completed',"
            "'cancelled','failed','timed_out')",
            name="ck_account_login_sessions_state",
        ),
        sa.CheckConstraint("revision >= 1", name="ck_account_login_sessions_revision"),
    )


def _create_indexes() -> None:
    op.create_index(
        "uq_device_workspaces_root_ref",
        "device_workspaces",
        ["root_ref"],
        unique=True,
        sqlite_where=sa.text("root_ref IS NOT NULL"),
    )
    op.create_index(
        "uq_execution_bindings_active_account",
        "execution_bindings",
        ["account_id"],
        unique=True,
        sqlite_where=sa.text("status = 'active'"),
    )
    op.create_index(
        "ix_account_login_sessions_account_updated",
        "account_login_sessions",
        ["account_id", "updated_at"],
    )
    op.create_index(
        "uq_account_login_sessions_active",
        "account_login_sessions",
        ["account_id"],
        unique=True,
        sqlite_where=sa.text("state IN ('preparing','waiting_user','probing')"),
    )
