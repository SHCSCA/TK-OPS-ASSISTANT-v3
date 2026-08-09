"""收紧 P0-C 账号纵向链与普通写幂等契约。

Revision ID: 0019_p0_account_vertical_chain
Revises: 0018_p0_runtime_kernel
"""

from __future__ import annotations

import logging
from typing import NoReturn

from alembic import context, op
import sqlalchemy as sa
from sqlalchemy import Connection

from persistence.migration.p0c_account_data_migration import (
    STABLE_ACCOUNT_ID_CHECK,
    backfill_account_defaults,
    map_legacy_active_accounts,
    validate_account_identifiers,
    validate_account_relations,
    validate_required_schema,
)
from persistence.migration.p0c_account_scope_triggers import (
    P0B_ACCOUNT_SCOPE_TRIGGERS,
    P0C_ACCOUNT_SCOPE_TRIGGERS,
)
from persistence.migration.p0c_knowledge_source_migration import (
    downgrade_knowledge_source_ingest_contract,
    upgrade_knowledge_source_ingest_contract,
)

revision = "0019_p0_account_vertical_chain"
down_revision = "0018_p0_runtime_kernel"
branch_labels = None
depends_on = None

log = logging.getLogger(__name__)

_LEGACY_ACCOUNT_STATUS_CHECK = (
    "status IN ('active','draft','unbound','ready','attention','archived')"
)
_STRICT_ACCOUNT_STATUS_CHECK = (
    "status IN ('draft','unbound','ready','attention','archived')"
)
_HASH_CHECK = (
    "length({column}) = 64 "
    "AND {column} NOT GLOB '*[^0-9a-f]*'"
)


def upgrade() -> None:
    connection = op.get_bind()
    validate_required_schema(connection)
    validate_account_identifiers(connection)
    validate_account_relations(connection)
    backfill_account_defaults(connection)
    map_legacy_active_accounts(connection)
    _tighten_account_contract()
    # SQLite 重建 knowledge_sources 时，外部触发器不能继续引用旧表。
    _drop_triggers(connection, P0B_ACCOUNT_SCOPE_TRIGGERS)
    upgrade_knowledge_source_ingest_contract(connection)
    op.add_column(
        "knowledge_snapshots",
        sa.Column("label", sa.Text(), nullable=True),
    )
    _create_mutation_idempotency_table()
    _replace_account_scope_triggers(connection)
    _validate_foreign_keys(connection)


def downgrade() -> None:
    _refuse_data_bearing_downgrade()
    _preflight_cross_revision_downgrade()
    _drop_triggers(op.get_bind(), P0C_ACCOUNT_SCOPE_TRIGGERS)
    _drop_mutation_idempotency_table()
    op.drop_column("knowledge_snapshots", "label")
    downgrade_knowledge_source_ingest_contract()
    _relax_account_contract()
    _create_triggers(op.get_bind(), P0B_ACCOUNT_SCOPE_TRIGGERS)
    _validate_foreign_keys(op.get_bind())


def _tighten_account_contract() -> None:
    with op.batch_alter_table("accounts", recreate="always") as batch:
        batch.drop_constraint("ck_accounts_status", type_="check")
        batch.create_check_constraint(
            "ck_accounts_status",
            _STRICT_ACCOUNT_STATUS_CHECK,
        )
        batch.create_check_constraint(
            "ck_accounts_stable_id",
            STABLE_ACCOUNT_ID_CHECK,
        )


def _relax_account_contract() -> None:
    with op.batch_alter_table("accounts", recreate="always") as batch:
        batch.drop_constraint("ck_accounts_stable_id", type_="check")
        batch.drop_constraint("ck_accounts_status", type_="check")
        batch.create_check_constraint(
            "ck_accounts_status",
            _LEGACY_ACCOUNT_STATUS_CHECK,
        )


def _create_mutation_idempotency_table() -> None:
    op.create_table(
        "runtime_mutation_idempotency",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("scope", sa.String(), nullable=False),
        sa.Column("account_id", sa.String(), nullable=True),
        sa.Column("operation_name", sa.String(), nullable=False),
        sa.Column("idempotency_key_hash", sa.String(), nullable=False),
        sa.Column("request_hash", sa.String(), nullable=False),
        sa.Column("response_json", sa.Text(), nullable=False),
        sa.Column("resource_type", sa.String(), nullable=True),
        sa.Column("resource_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
            name="fk_runtime_mutation_account_id",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "scope IN ('system','account')",
            name="ck_runtime_mutation_scope",
        ),
        sa.CheckConstraint(
            "(scope = 'system' AND account_id IS NULL) OR "
            "(scope = 'account' AND account_id IS NOT NULL "
            "AND length(trim(account_id)) > 0)",
            name="ck_runtime_mutation_account_scope",
        ),
        sa.CheckConstraint(
            "length(trim(operation_name)) > 0 "
            "AND operation_name = trim(operation_name)",
            name="ck_runtime_mutation_operation",
        ),
        sa.CheckConstraint(
            _HASH_CHECK.format(column="idempotency_key_hash"),
            name="ck_runtime_mutation_idempotency_hash",
        ),
        sa.CheckConstraint(
            _HASH_CHECK.format(column="request_hash"),
            name="ck_runtime_mutation_request_hash",
        ),
        sa.CheckConstraint(
            "length(trim(response_json)) > 0",
            name="ck_runtime_mutation_response",
        ),
        sa.CheckConstraint(
            "(resource_type IS NULL AND resource_id IS NULL) OR "
            "(resource_type IS NOT NULL AND resource_id IS NOT NULL "
            "AND length(trim(resource_type)) > 0 "
            "AND resource_type = trim(resource_type) "
            "AND length(trim(resource_id)) > 0 "
            "AND resource_id = trim(resource_id))",
            name="ck_runtime_mutation_resource",
        ),
        sa.CheckConstraint(
            "length(trim(created_at)) > 0 "
            "AND length(trim(expires_at)) > 0 "
            "AND expires_at > created_at",
            name="ck_runtime_mutation_retention",
        ),
    )
    op.create_index(
        "uq_runtime_mutation_system_idempotency",
        "runtime_mutation_idempotency",
        ["operation_name", "idempotency_key_hash"],
        unique=True,
        sqlite_where=sa.text("scope = 'system' AND account_id IS NULL"),
    )
    op.create_index(
        "uq_runtime_mutation_account_idempotency",
        "runtime_mutation_idempotency",
        ["account_id", "operation_name", "idempotency_key_hash"],
        unique=True,
        sqlite_where=sa.text("scope = 'account' AND account_id IS NOT NULL"),
    )
    op.create_index(
        "ix_runtime_mutation_expires_at",
        "runtime_mutation_idempotency",
        ["expires_at"],
    )


def _drop_mutation_idempotency_table() -> None:
    op.drop_index(
        "ix_runtime_mutation_expires_at",
        table_name="runtime_mutation_idempotency",
    )
    op.drop_index(
        "uq_runtime_mutation_account_idempotency",
        table_name="runtime_mutation_idempotency",
    )
    op.drop_index(
        "uq_runtime_mutation_system_idempotency",
        table_name="runtime_mutation_idempotency",
    )
    op.drop_table("runtime_mutation_idempotency")


def _replace_account_scope_triggers(connection: Connection) -> None:
    _drop_triggers(connection, P0C_ACCOUNT_SCOPE_TRIGGERS)
    _create_triggers(connection, P0C_ACCOUNT_SCOPE_TRIGGERS)


def _drop_triggers(
    connection: Connection,
    triggers: dict[str, str],
) -> None:
    for trigger_name in reversed(tuple(triggers)):
        connection.execute(sa.text(f'DROP TRIGGER IF EXISTS "{trigger_name}"'))


def _create_triggers(
    connection: Connection,
    triggers: dict[str, str],
) -> None:
    for statement in triggers.values():
        connection.execute(sa.text(statement))


def _refuse_data_bearing_downgrade() -> None:
    connection = op.get_bind()
    blockers: list[str] = []
    if connection.execute(
        sa.text("SELECT 1 FROM runtime_mutation_idempotency LIMIT 1")
    ).first():
        blockers.append("runtime_mutation_idempotency")
    if connection.execute(
        sa.text(
            """
            SELECT 1 FROM knowledge_snapshots
            WHERE label IS NOT NULL
            LIMIT 1
            """
        )
    ).first():
        blockers.append("knowledge_snapshots.label")
    if connection.execute(
        sa.text("SELECT 1 FROM knowledge_sources LIMIT 1")
    ).first():
        blockers.append("knowledge_sources.source_mode")
    if connection.execute(
        sa.text(
            """
            SELECT 1 FROM accounts
            WHERE status IN ('draft','unbound','ready','attention','archived')
            LIMIT 1
            """
        )
    ).first():
        blockers.append("accounts.status")
    if blockers:
        names = ", ".join(blockers)
        log.error(
            "P0-C 迁移拒绝有数据降级",
            extra={"downgrade_blockers": names},
        )
        raise RuntimeError(
            "P0C_DOWNGRADE_REQUIRES_BACKUP: 已存在不可逆账号纵向链数据，"
            f"禁止自动降级；请恢复迁移前备份。涉及对象：{names}"
        )


def _preflight_cross_revision_downgrade() -> None:
    destination = context.get_revision_argument()
    if destination in {down_revision, (down_revision,)}:
        return
    predecessor = context.script.get_revision(down_revision)
    guard = (
        getattr(
            predecessor.module,
            "_preflight_cross_revision_downgrade",
            None,
        )
        if predecessor is not None
        else None
    )
    if not callable(guard):
        _fail("无法加载 0018 跨版本降级保护")
    guard()


def _validate_foreign_keys(connection: Connection) -> None:
    violations = connection.execute(sa.text("PRAGMA foreign_key_check")).all()
    if violations:
        _fail(f"迁移后检测到 {len(violations)} 条孤儿外键")


def _fail(message: str) -> NoReturn:
    log.error(
        "P0-C 迁移数据验证失败",
        extra={"validation_issue": message},
    )
    raise RuntimeError(f"P0C_MIGRATION_VALIDATION_FAILED: {message}")
