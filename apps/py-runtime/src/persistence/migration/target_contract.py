from __future__ import annotations

import hashlib
import logging
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import NoReturn
from urllib.parse import quote

from persistence.migration.fingerprint import (
    inspect_database_schema,
    validate_database_integrity,
)
from persistence.migration.target_checks import P0_CHECK_CONTRACTS
from persistence.migration.target_columns import P0_TABLE_COLUMN_CONTRACTS
from persistence.migration.target_indexes import (
    P0_REQUIRED_INDEX_PREDICATES,
    P0_REQUIRED_INDEXES,
)
from persistence.migration.target_relations import (
    P0_REQUIRED_FOREIGN_KEYS,
    P0_REQUIRED_UNIQUE_COLUMN_SETS,
)
from persistence.migration.target_triggers import P0_REQUIRED_TRIGGERS
from persistence.migration.types import (
    DatabaseSchemaKind,
    SchemaInspection,
    TableSignature,
)

log = logging.getLogger(__name__)

_P0_REQUIRED_COLUMNS = {
    "accounts": {"revision", "wizard_completed_at", "archived_at"},
    "device_workspaces": {
        "account_id",
        "root_ref",
        "ownership_state",
        "revision",
        "error_code",
        "error_log_id",
    },
    "browser_instances": {
        "account_id",
        "ownership_state",
        "revision",
        "error_log_id",
    },
    "execution_bindings": {
        "browser_instance_id",
        "revision",
        "error_code",
        "error_log_id",
    },
    "system_config": {"ai_config_revision"},
    "runtime_tasks": {
        "completion_kind",
        "failure_kind",
        "progress",
        "idempotency_key_hash",
        "request_hash",
        "handler_version",
    },
}
_P0_REQUIRED_NAMED_CONSTRAINTS = {
    "accounts": {
        "ck_accounts_stable_id",
        "ck_accounts_status",
        "ck_accounts_revision",
    },
    "account_connections": {
        "ck_account_connections_auth_status",
        "ck_account_connections_health_status",
        "ck_account_connections_revision",
    },
    "positioning_profiles": {
        "ck_positioning_profiles_status",
        "ck_positioning_profiles_version",
    },
    "account_knowledge_bases": {
        "ck_knowledge_bases_status",
        "ck_knowledge_bases_revision",
    },
    "knowledge_sources": {
        "ck_knowledge_sources_kind",
        "ck_knowledge_sources_status",
        "ck_knowledge_sources_revision",
        "ck_knowledge_sources_source_mode",
        "ck_knowledge_sources_source_url",
    },
    "brand_kits": {"ck_brand_kits_status", "ck_brand_kits_version"},
    "account_config_copy_runs": {"ck_copy_runs_status", "ck_copy_runs_accounts"},
    "provider_profiles": {
        "ck_provider_profiles_adapter",
        "ck_provider_profiles_health",
        "ck_provider_profiles_limits",
    },
    "model_profiles": {"ck_model_profiles_discovery", "ck_model_profiles_revision"},
    "model_capabilities": {
        "ck_model_capabilities_contract_revision",
        "ck_model_capabilities_verified_at",
    },
    "prompt_profiles": {"ck_prompt_profiles_status", "ck_prompt_profiles_version"},
    "capability_routes": {
        "ck_capability_routes_validation",
        "ck_capability_routes_revision",
    },
    "composition_template_profiles": {
        "ck_composition_templates_status",
        "ck_composition_templates_type",
        "ck_composition_templates_version",
    },
    "account_ai_recipes": {
        "ck_account_ai_recipes_status",
        "ck_account_ai_recipes_validation",
        "ck_account_ai_recipes_content_hash",
        "ck_account_ai_recipes_version",
    },
    "runtime_tasks": {
        "ck_runtime_tasks_scope",
        "ck_runtime_tasks_account_scope",
        "ck_runtime_tasks_task_type",
        "ck_runtime_tasks_status",
        "ck_runtime_tasks_completion_kind",
        "ck_runtime_tasks_failure_kind",
        "ck_runtime_tasks_terminal_kind",
        "ck_runtime_tasks_progress",
        "ck_runtime_tasks_attempt_revision",
        "ck_runtime_tasks_idempotency_hash",
        "ck_runtime_tasks_request_hash",
        "ck_runtime_tasks_handler_version",
    },
    "runtime_events": {
        "ck_runtime_events_topic",
        "ck_runtime_events_account_topic",
        "ck_runtime_events_sequence",
        "uq_runtime_events_topic_sequence",
    },
    "runtime_mutation_idempotency": {
        "ck_runtime_mutation_scope",
        "ck_runtime_mutation_account_scope",
        "ck_runtime_mutation_operation",
        "ck_runtime_mutation_idempotency_hash",
        "ck_runtime_mutation_request_hash",
        "ck_runtime_mutation_response",
        "ck_runtime_mutation_resource",
        "ck_runtime_mutation_retention",
    },
    "account_login_sessions": {
        "ck_account_login_sessions_state",
        "ck_account_login_sessions_revision",
    },
}


class TargetSchemaContractError(RuntimeError):
    """数据库没有满足当前 Alembic head 的运行契约。"""


def validate_target_schema_contract(
    database_path: Path,
    *,
    target_revision: str,
) -> SchemaInspection:
    """校验版本、字段、索引、外键、约束语义和隔离触发器。"""

    validate_database_integrity(database_path)
    inspection = inspect_database_schema(database_path)
    if (
        inspection.kind is not DatabaseSchemaKind.VERSIONED
        or inspection.revision != target_revision
    ):
        _fail("迁移后的 Alembic 版本未到达目标版本")

    table_map = {table.name: table for table in inspection.tables}
    required_tables = (
        set(P0_TABLE_COLUMN_CONTRACTS)
        | set(_P0_REQUIRED_COLUMNS)
        | {definition[0] for definition in P0_REQUIRED_INDEXES.values()}
        | {foreign_key[0] for foreign_key in P0_REQUIRED_FOREIGN_KEYS}
        | {foreign_key[2] for foreign_key in P0_REQUIRED_FOREIGN_KEYS}
        | set(_P0_REQUIRED_NAMED_CONSTRAINTS)
    )
    missing_tables = sorted(required_tables - table_map.keys())
    if missing_tables:
        _fail(f"迁移后缺少目标表：{', '.join(missing_tables)}")

    _validate_table_columns(table_map)

    for table_name, required_columns in _P0_REQUIRED_COLUMNS.items():
        table = table_map.get(table_name)
        if table is None:
            _fail(f"迁移后缺少目标表：{table_name}")
        present_columns = {column.name for column in table.columns}
        missing_columns = sorted(required_columns - present_columns)
        if missing_columns:
            _fail(f"迁移后表 {table_name} 缺少字段：{', '.join(missing_columns)}")

    _validate_indexes(table_map)
    _validate_unique_constraints(table_map)
    _validate_foreign_keys(table_map)
    _validate_named_constraints(database_path)
    return inspection


def _validate_indexes(table_map: dict[str, TableSignature]) -> None:
    for index_name, (
        table_name,
        columns,
        unique,
        partial,
    ) in P0_REQUIRED_INDEXES.items():
        table = table_map[table_name]
        indexes = {index.name: index for index in table.indexes}
        index = indexes.get(index_name)
        if index is None:
            _fail(f"迁移后缺少目标索引：{index_name}")
        actual_columns = tuple(column.column_name for column in index.columns)
        if (
            actual_columns != columns
            or index.unique is not unique
            or index.partial is not partial
        ):
            _fail(f"迁移后索引结构不匹配：{index_name}")


def _validate_table_columns(table_map: dict[str, TableSignature]) -> None:
    for table_name, expected_columns in P0_TABLE_COLUMN_CONTRACTS.items():
        table = table_map[table_name]
        actual_columns = tuple(
            (
                column.name,
                column.declared_type,
                column.not_null,
                column.primary_key_position,
            )
            for column in table.columns
        )
        has_unsupported_metadata = any(
            column.default_value is not None or column.hidden != 0
            for column in table.columns
        )
        if actual_columns != expected_columns or has_unsupported_metadata:
            _fail(f"迁移后目标表字段契约不匹配：{table_name}")


def _validate_unique_constraints(table_map: dict[str, TableSignature]) -> None:
    for table_name, expected_column_sets in P0_REQUIRED_UNIQUE_COLUMN_SETS.items():
        actual_column_sets = {
            tuple(column.column_name for column in index.columns)
            for index in table_map[table_name].indexes
            if index.unique and not index.partial
        }
        missing = expected_column_sets - actual_column_sets
        if missing:
            _fail(f"迁移后表 {table_name} 缺少唯一约束")


def _validate_foreign_keys(table_map: dict[str, TableSignature]) -> None:
    actual = {
        (
            table_name,
            foreign_key.source_column,
            foreign_key.target_table,
            foreign_key.target_column,
            foreign_key.on_delete,
        )
        for table_name, table in table_map.items()
        for foreign_key in table.foreign_keys
    }
    missing = sorted(P0_REQUIRED_FOREIGN_KEYS - actual)
    if missing:
        _fail("迁移后核心外键结构不完整")


def _validate_named_constraints(database_path: Path) -> None:
    try:
        encoded_path = quote(database_path.resolve().as_posix(), safe="/:")
        connection = sqlite3.connect(f"file:{encoded_path}?mode=ro", uri=True)
        with closing(connection):
            rows = connection.execute(
                """
                SELECT type, name, tbl_name, sql
                FROM sqlite_master
                WHERE type IN ('table', 'index', 'trigger', 'view')
                """
            ).fetchall()
    except sqlite3.DatabaseError as exc:
        log.exception("迁移后命名约束读取失败")
        raise TargetSchemaContractError("迁移后命名约束无法校验") from exc

    create_sql = {
        str(name): str(sql or "")
        for object_type, name, _, sql in rows
        if str(object_type) == "table"
    }
    for table_name, constraint_names in _P0_REQUIRED_NAMED_CONSTRAINTS.items():
        sql = create_sql.get(table_name, "")
        missing = sorted(name for name in constraint_names if name not in sql)
        if missing:
            _fail(f"迁移后表 {table_name} 缺少约束：{', '.join(missing)}")

    for table_name, checks in P0_CHECK_CONTRACTS.items():
        normalized_sql = _normalize_schema_sql(create_sql.get(table_name, ""))
        for check_name, expression in checks.items():
            expected_fragment = _normalize_schema_sql(
                f"CONSTRAINT {check_name} CHECK ({expression})"
            )
            if expected_fragment not in normalized_sql:
                _fail(f"迁移后约束语义不匹配：{check_name}")

    indexes = {
        str(name): _normalize_schema_sql(str(sql or ""))
        for object_type, name, _, sql in rows
        if str(object_type) == "index"
    }
    for index_name, predicate in P0_REQUIRED_INDEX_PREDICATES.items():
        index_sql = indexes.get(index_name, "")
        where_position = index_sql.find(" where ")
        actual_predicate = (
            index_sql[where_position + 1 :]
            if where_position >= 0
            else ""
        )
        if actual_predicate != predicate:
            _fail(f"迁移后索引谓词不匹配：{index_name}")

    triggers = {
        str(name): (str(table_name), _normalize_schema_sql(str(sql or "")))
        for object_type, name, table_name, sql in rows
        if str(object_type) == "trigger"
    }
    unexpected_triggers = sorted(set(triggers) - set(P0_REQUIRED_TRIGGERS))
    if unexpected_triggers:
        _fail(f"迁移后存在未声明触发器：{', '.join(unexpected_triggers)}")
    views = sorted(
        str(name)
        for object_type, name, _, _ in rows
        if str(object_type) == "view"
    )
    if views:
        _fail(f"迁移后存在未声明视图：{', '.join(views)}")
    for trigger_name, (
        expected_table,
        fragments,
        expected_sha256,
    ) in P0_REQUIRED_TRIGGERS.items():
        trigger = triggers.get(trigger_name)
        if trigger is None:
            _fail(f"迁移后缺少账号隔离触发器：{trigger_name}")
        actual_table, normalized_sql = trigger
        actual_sha256 = hashlib.sha256(
            normalized_sql.encode("utf-8")
        ).hexdigest()
        if actual_table != expected_table or any(
            fragment not in normalized_sql for fragment in fragments
        ) or actual_sha256 != expected_sha256:
            _fail(f"迁移后账号隔离触发器结构不匹配：{trigger_name}")


def _normalize_schema_sql(sql: str) -> str:
    return " ".join(sql.lower().strip().split())


def _fail(message: str) -> NoReturn:
    log.error("数据库目标契约校验失败：%s", message)
    raise TargetSchemaContractError(message)
