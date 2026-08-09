"""封装 P0-C 账号纵向链的旧数据校验与保守映射。"""

from __future__ import annotations

import logging
from typing import NoReturn

import sqlalchemy as sa
from sqlalchemy import Connection

log = logging.getLogger(__name__)

STABLE_ACCOUNT_ID_CHECK = (
    "id IS NOT NULL "
    "AND length(id) BETWEEN 1 AND 128 "
    "AND substr(id, 1, 1) GLOB '[A-Za-z0-9]' "
    "AND id NOT GLOB '*[^A-Za-z0-9._-]*'"
)


def validate_required_schema(connection: Connection) -> None:
    inspector = sa.inspect(connection)
    required_columns = {
        "accounts": {
            "created_at",
            "id",
            "status",
            "wizard_completed_at",
            "status_reason_code",
            "revision",
            "updated_at",
        },
        "device_workspaces": {"id", "account_id"},
        "browser_instances": {"id", "workspace_id", "account_id"},
        "execution_bindings": {
            "id",
            "account_id",
            "device_workspace_id",
            "browser_instance_id",
        },
        "account_connections": {
            "account_id",
            "active_execution_binding_id",
        },
        "account_knowledge_bases": {
            "id",
            "account_id",
            "status",
            "rules_json",
            "rules_version",
            "index_revision",
            "last_indexed_at",
            "error_code",
            "error_log_id",
            "revision",
            "created_at",
            "updated_at",
        },
        "account_publish_defaults": {
            "account_id",
            "timezone",
            "privacy_level",
            "allow_comments",
            "allow_duet",
            "allow_stitch",
            "caption_rules_json",
            "revision",
            "created_at",
            "updated_at",
        },
        "knowledge_sources": {
            "account_id",
            "knowledge_base_id",
            "kind",
            "source_ref",
            "updated_at",
        },
        "knowledge_snapshots": {
            "account_id",
            "knowledge_base_id",
            "positioning_profile_id",
        },
        "positioning_profiles": {"id", "account_id"},
    }
    missing_tables = sorted(
        set(required_columns) - set(inspector.get_table_names())
    )
    if missing_tables:
        _fail(f"缺少账号纵向链目标表：{', '.join(missing_tables)}")
    for table_name, expected in required_columns.items():
        present = {
            str(column["name"]) for column in inspector.get_columns(table_name)
        }
        missing = sorted(expected - present)
        if missing:
            _fail(f"表 {table_name} 缺少字段：{', '.join(missing)}")
    if "label" in {
        str(column["name"])
        for column in inspector.get_columns("knowledge_snapshots")
    }:
        _fail("knowledge_snapshots.label 已存在，无法确认字段来源")
    if "runtime_mutation_idempotency" in inspector.get_table_names():
        _fail("runtime_mutation_idempotency 已存在，无法确认表来源")
    knowledge_source_columns = {
        str(column["name"])
        for column in inspector.get_columns("knowledge_sources")
    }
    unexpected_source_columns = {
        "source_mode",
        "source_url",
    } & knowledge_source_columns
    if unexpected_source_columns:
        _fail("knowledge_sources 摄取字段已存在，无法确认字段来源")


def validate_account_identifiers(connection: Connection) -> None:
    """在任何回填前拒绝无法进入 V1 资源边界的历史账号 ID。"""

    invalid_count = int(
        connection.execute(
            sa.text(
                f"""
                SELECT COUNT(*)
                FROM accounts
                WHERE NOT ({STABLE_ACCOUNT_ID_CHECK})
                """
            )
        ).scalar_one()
    )
    if invalid_count:
        _fail(
            "accounts.id 存在不符合稳定资源 ID 语法的记录，"
            f"共 {invalid_count} 条；必须匹配 "
            "^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$，"
            "迁移不会自动重映射账号 ID"
        )


def backfill_account_defaults(connection: Connection) -> None:
    collision_count = int(
        connection.execute(
            sa.text(
                """
                SELECT COUNT(*)
                FROM accounts AS account_row
                JOIN account_knowledge_bases AS existing
                  ON existing.id = (
                      'kb_p0c_' ||
                      lower(hex(CAST(account_row.id AS BLOB)))
                  )
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM account_knowledge_bases AS own_base
                    WHERE own_base.account_id = account_row.id
                )
                  AND existing.account_id <> account_row.id
                """
            )
        ).scalar_one()
    )
    if collision_count:
        _fail(
            "账号知识库确定性回填 ID 与既有对象冲突，"
            f"共 {collision_count} 条"
        )

    base_result = connection.execute(
        sa.text(
            """
            INSERT INTO account_knowledge_bases (
                id, account_id, status, rules_json, rules_version,
                index_revision, last_indexed_at, error_code, error_log_id,
                revision, created_at, updated_at
            )
            SELECT
                'kb_p0c_' || lower(hex(CAST(account_row.id AS BLOB))),
                account_row.id,
                'empty',
                '{"inclusionRules":{},"exclusionRules":{},"citationPolicy":{}}',
                0,
                0,
                NULL,
                NULL,
                NULL,
                1,
                COALESCE(
                    NULLIF(trim(account_row.created_at), ''),
                    strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                ),
                COALESCE(
                    NULLIF(trim(account_row.updated_at), ''),
                    strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                )
            FROM accounts AS account_row
            WHERE NOT EXISTS (
                SELECT 1
                FROM account_knowledge_bases AS existing
                WHERE existing.account_id = account_row.id
            )
            """
        )
    )
    defaults_result = connection.execute(
        sa.text(
            """
            INSERT INTO account_publish_defaults (
                account_id, timezone, privacy_level, allow_comments,
                allow_duet, allow_stitch, caption_rules_json, revision,
                created_at, updated_at
            )
            SELECT
                account_row.id,
                'UTC',
                'private',
                0,
                0,
                0,
                '{}',
                1,
                COALESCE(
                    NULLIF(trim(account_row.created_at), ''),
                    strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                ),
                COALESCE(
                    NULLIF(trim(account_row.updated_at), ''),
                    strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                )
            FROM accounts AS account_row
            WHERE NOT EXISTS (
                SELECT 1
                FROM account_publish_defaults AS existing
                WHERE existing.account_id = account_row.id
            )
            """
        )
    )
    missing_count = int(
        connection.execute(
            sa.text(
                """
                SELECT COUNT(*)
                FROM accounts AS account_row
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM account_knowledge_bases AS base
                    WHERE base.account_id = account_row.id
                )
                   OR NOT EXISTS (
                    SELECT 1
                    FROM account_publish_defaults AS defaults
                    WHERE defaults.account_id = account_row.id
                )
                """
            )
        ).scalar_one()
    )
    if missing_count:
        _fail(f"账号基础对象回填后仍缺失，共 {missing_count} 个账号")

    log.info(
        "P0-C 账号基础对象回填完成",
        extra={
            "knowledge_base_count": _safe_rowcount(base_result.rowcount),
            "publish_defaults_count": _safe_rowcount(defaults_result.rowcount),
        },
    )


def validate_account_relations(connection: Connection) -> None:
    checks = (
        (
            "执行绑定与设备或浏览器账号不一致",
            """
            SELECT COUNT(*) FROM execution_bindings AS binding
            LEFT JOIN device_workspaces AS workspace
              ON workspace.id = binding.device_workspace_id
            LEFT JOIN browser_instances AS browser
              ON browser.id = binding.browser_instance_id
            WHERE workspace.id IS NULL
               OR workspace.account_id IS NULL
               OR workspace.account_id <> binding.account_id
               OR (
                    binding.browser_instance_id IS NOT NULL
                    AND (
                        browser.id IS NULL
                        OR browser.account_id IS NULL
                        OR browser.account_id <> binding.account_id
                        OR browser.workspace_id <> binding.device_workspace_id
                    )
               )
            """,
        ),
        (
            "账号连接没有引用真实且同账号的执行环境",
            """
            SELECT COUNT(*) FROM account_connections AS connection
            LEFT JOIN execution_bindings AS binding
              ON binding.id = connection.active_execution_binding_id
            LEFT JOIN device_workspaces AS workspace
              ON workspace.id = binding.device_workspace_id
            LEFT JOIN browser_instances AS browser
              ON browser.id = binding.browser_instance_id
            WHERE connection.active_execution_binding_id IS NOT NULL
              AND (
                    binding.id IS NULL
                    OR binding.account_id <> connection.account_id
                    OR workspace.id IS NULL
                    OR workspace.account_id <> connection.account_id
                    OR browser.id IS NULL
                    OR browser.account_id <> connection.account_id
                    OR browser.workspace_id <> workspace.id
              )
            """,
        ),
        (
            "浏览器实例与设备工作区账号不一致",
            """
            SELECT COUNT(*) FROM browser_instances AS browser
            LEFT JOIN device_workspaces AS workspace
              ON workspace.id = browser.workspace_id
            WHERE workspace.id IS NULL
               OR (
                    workspace.account_id IS NULL
                    AND browser.account_id IS NOT NULL
               )
               OR (
                    workspace.account_id IS NOT NULL
                    AND (
                        browser.account_id IS NULL
                        OR workspace.account_id <> browser.account_id
                    )
              )
            """,
        ),
        (
            "知识来源与知识库账号不一致",
            """
            SELECT COUNT(*) FROM knowledge_sources AS source
            LEFT JOIN account_knowledge_bases AS base
              ON base.id = source.knowledge_base_id
            WHERE base.id IS NULL OR base.account_id <> source.account_id
            """,
        ),
        (
            "知识快照与知识库或定位版本账号不一致",
            """
            SELECT COUNT(*) FROM knowledge_snapshots AS snapshot
            LEFT JOIN account_knowledge_bases AS base
              ON base.id = snapshot.knowledge_base_id
            LEFT JOIN positioning_profiles AS profile
              ON profile.id = snapshot.positioning_profile_id
            WHERE base.id IS NULL
               OR base.account_id <> snapshot.account_id
               OR (
                    snapshot.positioning_profile_id IS NOT NULL
                    AND (
                        profile.id IS NULL
                        OR profile.account_id <> snapshot.account_id
                    )
               )
            """,
        ),
    )
    for issue, statement in checks:
        count = int(connection.execute(sa.text(statement)).scalar_one())
        if count:
            _fail(f"{issue}，共 {count} 条")


def map_legacy_active_accounts(connection: Connection) -> None:
    connection.execute(
        sa.text(
            """
            UPDATE accounts
            SET status = CASE
                    WHEN wizard_completed_at IS NULL
                      OR length(trim(wizard_completed_at)) = 0
                    THEN 'draft'
                    WHEN EXISTS (
                        SELECT 1
                        FROM account_connections AS connection
                        JOIN execution_bindings AS binding
                          ON binding.id = connection.active_execution_binding_id
                        JOIN device_workspaces AS workspace
                          ON workspace.id = binding.device_workspace_id
                        JOIN browser_instances AS browser
                          ON browser.id = binding.browser_instance_id
                        WHERE connection.account_id = accounts.id
                          AND binding.account_id = accounts.id
                          AND workspace.account_id = accounts.id
                          AND browser.account_id = accounts.id
                          AND browser.workspace_id = workspace.id
                    )
                    THEN 'attention'
                    ELSE 'unbound'
                END,
                status_reason_code = CASE
                    WHEN wizard_completed_at IS NULL
                      OR length(trim(wizard_completed_at)) = 0
                    THEN 'P0C_LEGACY_ACTIVE_DRAFT_REVIEW'
                    WHEN EXISTS (
                        SELECT 1
                        FROM account_connections AS connection
                        JOIN execution_bindings AS binding
                          ON binding.id = connection.active_execution_binding_id
                        JOIN device_workspaces AS workspace
                          ON workspace.id = binding.device_workspace_id
                        JOIN browser_instances AS browser
                          ON browser.id = binding.browser_instance_id
                        WHERE connection.account_id = accounts.id
                          AND binding.account_id = accounts.id
                          AND workspace.account_id = accounts.id
                          AND browser.account_id = accounts.id
                          AND browser.workspace_id = workspace.id
                    )
                    THEN 'P0C_LEGACY_ACTIVE_HEALTH_RECHECK_REQUIRED'
                    ELSE 'P0C_LEGACY_ACTIVE_BINDING_REQUIRED'
                END,
                revision = revision + 1,
                updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
            WHERE status = 'active'
            """
        )
    )
    invalid_count = int(
        connection.execute(
            sa.text(
                """
                SELECT COUNT(*) FROM accounts
                WHERE status NOT IN (
                    'draft','unbound','ready','attention','archived'
                )
                """
            )
        ).scalar_one()
    )
    if invalid_count:
        _fail(f"账号状态收口后仍有 {invalid_count} 条非五状态记录")


def _safe_rowcount(value: int | None) -> int:
    return value if value is not None and value >= 0 else 0


def _fail(message: str) -> NoReturn:
    log.error(
        "P0-C 迁移数据验证失败",
        extra={"validation_issue": message},
    )
    raise RuntimeError(f"P0C_MIGRATION_VALIDATION_FAILED: {message}")
