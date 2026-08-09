"""验证 P0 数据并收紧约束与账号范围索引。"""

from __future__ import annotations

from collections.abc import Iterable
import logging

from alembic import op
import sqlalchemy as sa


revision = "0017_p0_enforce_and_cutover"
down_revision = "0016_p0_backfill"
branch_labels = None
depends_on = None

log = logging.getLogger(__name__)


_ACTIVE_INDEXES = {
    "uq_positioning_profiles_one_active": (
        "positioning_profiles",
        ("account_id",),
        "status = 'active'",
    ),
    "uq_brand_kits_one_active": ("brand_kits", ("account_id",), "status = 'active'"),
    "uq_prompt_profiles_one_active": (
        "prompt_profiles",
        ("profile_key",),
        "status = 'active'",
    ),
    "uq_composition_templates_one_active": (
        "composition_template_profiles",
        ("template_key",),
        "status = 'active'",
    ),
    "uq_account_ai_recipes_one_active": (
        "account_ai_recipes",
        ("account_id",),
        "status = 'active'",
    ),
}

_ACCOUNT_INDEXES = {
    "ix_accounts_status_last_used": ("accounts", ("status", "last_used_at")),
    "ix_device_workspaces_account_updated": (
        "device_workspaces",
        ("account_id", "updated_at"),
    ),
    "ix_browser_instances_account_updated": (
        "browser_instances",
        ("account_id", "updated_at"),
    ),
    "ix_execution_bindings_account_updated": (
        "execution_bindings",
        ("account_id", "updated_at"),
    ),
    "ix_account_connections_account_updated": (
        "account_connections",
        ("account_id", "updated_at"),
    ),
    "ix_positioning_profiles_account_created": (
        "positioning_profiles",
        ("account_id", "created_at"),
    ),
    "ix_knowledge_bases_account_updated": (
        "account_knowledge_bases",
        ("account_id", "updated_at"),
    ),
    "ix_knowledge_sources_account_updated": (
        "knowledge_sources",
        ("account_id", "updated_at"),
    ),
    "ix_knowledge_snapshots_account_created": (
        "knowledge_snapshots",
        ("account_id", "created_at"),
    ),
    "ix_brand_kits_account_created": ("brand_kits", ("account_id", "created_at")),
    "ix_publish_defaults_account_updated": (
        "account_publish_defaults",
        ("account_id", "updated_at"),
    ),
    "ix_copy_runs_source_created": (
        "account_config_copy_runs",
        ("source_account_id", "created_at"),
    ),
    "ix_copy_runs_target_created": (
        "account_config_copy_runs",
        ("target_account_id", "created_at"),
    ),
    "ix_account_ai_recipes_account_created": (
        "account_ai_recipes",
        ("account_id", "created_at"),
    ),
    "ix_runtime_tasks_account_updated": ("runtime_tasks", ("account_id", "updated_at")),
    "ix_runtime_tasks_status_updated": ("runtime_tasks", ("status", "updated_at")),
    "ix_runtime_events_account_occurred": (
        "runtime_events",
        ("account_id", "occurred_at"),
    ),
    "ix_runtime_events_unpublished": ("runtime_events", ("published_at", "occurred_at")),
}

_CHECKS = {
    "accounts": {
        # P0-A 尚未切换旧 Account API，暂时保留 active 写入兼容。
        "ck_accounts_status": (
            "status IN ('active','draft','unbound','ready','attention','archived')"
        ),
        "ck_accounts_revision": "revision >= 1",
    },
    "account_connections": {
        "ck_account_connections_auth_status": (
            "auth_status IN ('unknown','required','valid','expired','failed')"
        ),
        "ck_account_connections_health_status": (
            "health_status IN ('unknown','checking','ready','attention','failed')"
        ),
        "ck_account_connections_revision": "revision >= 1",
    },
    "positioning_profiles": {
        "ck_positioning_profiles_status": "status IN ('draft','active','archived')",
        "ck_positioning_profiles_version": "version >= 1 AND revision >= 1",
    },
    "account_knowledge_bases": {
        "ck_knowledge_bases_status": (
            "status IN ('empty','indexing','ready','stale','attention')"
        ),
        "ck_knowledge_bases_revision": (
            "rules_version >= 0 AND index_revision >= 0 AND revision >= 1"
        ),
    },
    "knowledge_sources": {
        "ck_knowledge_sources_kind": (
            "kind IN ('document','image','video','audio','text','reference')"
        ),
        "ck_knowledge_sources_status": (
            "status IN ('pending','indexing','ready','failed','stale')"
        ),
        "ck_knowledge_sources_revision": "revision >= 1",
    },
    "brand_kits": {
        "ck_brand_kits_status": "status IN ('draft','active','archived')",
        "ck_brand_kits_version": "version >= 1 AND revision >= 1",
    },
    "account_config_copy_runs": {
        "ck_copy_runs_status": "status IN ('running','succeeded','failed','rolled_back')",
        "ck_copy_runs_accounts": "source_account_id <> target_account_id",
    },
    "provider_profiles": {
        "ck_provider_profiles_adapter": (
            "adapter_type IN ('direct_api','openai_compatible','comfyui','runninghub')"
        ),
        "ck_provider_profiles_health": (
            "health_status IN ('unknown','checking','ready','degraded','failed')"
        ),
        "ck_provider_profiles_limits": (
            "timeout_ms > 0 AND max_concurrency > 0 AND revision >= 1"
        ),
    },
    "model_profiles": {
        "ck_model_profiles_discovery": (
            "discovery_source IN ('discovered','manual','migrated')"
        ),
        "ck_model_profiles_revision": "revision >= 1",
    },
    "model_capabilities": {
        "ck_model_capabilities_contract_revision": "contract_revision >= 0",
        "ck_model_capabilities_verified_at": (
            "contract_verified = 0 OR verified_at IS NOT NULL"
        ),
    },
    "prompt_profiles": {
        "ck_prompt_profiles_status": "status IN ('draft','active','archived')",
        "ck_prompt_profiles_version": "version >= 1",
    },
    "capability_routes": {
        "ck_capability_routes_validation": (
            "validation_status IN ('valid','incomplete','invalid')"
        ),
        "ck_capability_routes_revision": "revision >= 1",
    },
    "composition_template_profiles": {
        "ck_composition_templates_status": "status IN ('draft','active','archived')",
        "ck_composition_templates_type": (
            "template_type IN ('slideshow','talking_head','product_showcase','mixed_media')"
        ),
        "ck_composition_templates_version": "version >= 1 AND revision >= 1",
    },
    "account_ai_recipes": {
        "ck_account_ai_recipes_status": "status IN ('draft','active','archived')",
        "ck_account_ai_recipes_validation": (
            "validation_status IN ('valid','incomplete','invalid')"
        ),
        "ck_account_ai_recipes_version": "version >= 1 AND revision >= 1",
    },
    "runtime_tasks": {
        "ck_runtime_tasks_scope": "scope IN ('system','account')",
        "ck_runtime_tasks_account_scope": "scope <> 'account' OR account_id IS NOT NULL",
        "ck_runtime_tasks_status": (
            "status IN ('queued','running','cancelling','failed','completed')"
        ),
        "ck_runtime_tasks_completion_kind": (
            "completion_kind IS NULL OR completion_kind IN ('succeeded','cancelled')"
        ),
        "ck_runtime_tasks_failure_kind": (
            "failure_kind IS NULL OR failure_kind IN ('error','timed_out','restart_interrupted')"
        ),
        "ck_runtime_tasks_terminal_kind": (
            "(status = 'completed' AND completion_kind IS NOT NULL "
            "AND failure_kind IS NULL AND completed_at IS NOT NULL) "
            "OR (status = 'failed' AND failure_kind IS NOT NULL "
            "AND completion_kind IS NULL AND completed_at IS NOT NULL) "
            "OR (status IN ('queued','running','cancelling') "
            "AND completion_kind IS NULL AND failure_kind IS NULL)"
        ),
        "ck_runtime_tasks_progress": "progress BETWEEN 0 AND 1",
        "ck_runtime_tasks_attempt_revision": "attempt >= 1 AND revision >= 1",
    },
    "runtime_events": {
        "ck_runtime_events_topic": "length(trim(topic)) > 0",
        "ck_runtime_events_account_topic": (
            "topic NOT LIKE 'account:%' OR (account_id IS NOT NULL AND "
            "substr(topic, 1, length('account:' || account_id || ':')) = "
            "'account:' || account_id || ':')"
        ),
        "ck_runtime_events_sequence": "sequence >= 1",
    },
}

_FOREIGN_KEYS = {
    "fk_assets_group_id": ("assets", "asset_groups", ("group_id",), ("id",), "SET NULL"),
    "fk_device_workspaces_account_id": (
        "device_workspaces",
        "accounts",
        ("account_id",),
        ("id",),
        "RESTRICT",
    ),
    "fk_browser_instances_account_id": (
        "browser_instances",
        "accounts",
        ("account_id",),
        ("id",),
        "RESTRICT",
    ),
    "fk_execution_bindings_browser_id": (
        "execution_bindings",
        "browser_instances",
        ("browser_instance_id",),
        ("id",),
        "SET NULL",
    ),
}
_ACCOUNT_SCOPE_TRIGGERS = {
    "trg_knowledge_sources_account_base_insert": """
        CREATE TRIGGER trg_knowledge_sources_account_base_insert
        BEFORE INSERT ON knowledge_sources
        FOR EACH ROW
        WHEN NOT EXISTS (
            SELECT 1
            FROM account_knowledge_bases AS base
            WHERE base.id = NEW.knowledge_base_id
              AND base.account_id = NEW.account_id
        )
        BEGIN
            SELECT RAISE(ABORT, 'KNOWLEDGE_SOURCE_ACCOUNT_MISMATCH');
        END
    """,
    "trg_knowledge_sources_account_base_update": """
        CREATE TRIGGER trg_knowledge_sources_account_base_update
        BEFORE UPDATE OF account_id, knowledge_base_id ON knowledge_sources
        FOR EACH ROW
        WHEN NOT EXISTS (
            SELECT 1
            FROM account_knowledge_bases AS base
            WHERE base.id = NEW.knowledge_base_id
              AND base.account_id = NEW.account_id
        )
        BEGIN
            SELECT RAISE(ABORT, 'KNOWLEDGE_SOURCE_ACCOUNT_MISMATCH');
        END
    """,
    "trg_account_knowledge_bases_account_update": """
        CREATE TRIGGER trg_account_knowledge_bases_account_update
        BEFORE UPDATE OF account_id ON account_knowledge_bases
        FOR EACH ROW
        WHEN EXISTS (
            SELECT 1
            FROM knowledge_sources AS source
            WHERE source.knowledge_base_id = OLD.id
              AND source.account_id <> NEW.account_id
        )
        BEGIN
            SELECT RAISE(ABORT, 'KNOWLEDGE_BASE_ACCOUNT_MISMATCH');
        END
    """,
}
_ADDED_COLUMN_DATA_CHECKS = (
    ("system_config.ai_config_revision", "SELECT 1 FROM system_config WHERE ai_config_revision IS NOT NULL AND ai_config_revision <> 0 LIMIT 1"),
    ("execution_bindings.browser_instance_id", "SELECT 1 FROM execution_bindings WHERE browser_instance_id IS NOT NULL AND trim(browser_instance_id) <> '' LIMIT 1"),
    ("browser_instances.account_id", "SELECT 1 FROM browser_instances WHERE account_id IS NOT NULL AND trim(account_id) <> '' LIMIT 1"),
    ("device_workspaces.account_id", "SELECT 1 FROM device_workspaces WHERE account_id IS NOT NULL AND trim(account_id) <> '' LIMIT 1"),
    ("accounts.revision", "SELECT 1 FROM accounts WHERE revision IS NOT NULL AND revision <> 1 LIMIT 1"),
    ("accounts.archived_at", "SELECT 1 FROM accounts WHERE archived_at IS NOT NULL AND trim(archived_at) <> '' LIMIT 1"),
    ("accounts.last_health_checked_at", "SELECT 1 FROM accounts WHERE last_health_checked_at IS NOT NULL AND trim(last_health_checked_at) <> '' LIMIT 1"),
    ("accounts.last_used_at", "SELECT 1 FROM accounts WHERE last_used_at IS NOT NULL AND trim(last_used_at) <> '' LIMIT 1"),
    ("accounts.status_reason_code", "SELECT 1 FROM accounts WHERE status_reason_code IS NOT NULL AND trim(status_reason_code) <> '' LIMIT 1"),
    ("accounts.wizard_completed_at", "SELECT 1 FROM accounts WHERE wizard_completed_at IS NOT NULL AND trim(wizard_completed_at) <> '' LIMIT 1"),
    ("accounts.platform_account_id", "SELECT 1 FROM accounts WHERE platform_account_id IS NOT NULL AND trim(platform_account_id) <> '' LIMIT 1"),
    ("accounts.last_validated_at", "SELECT 1 FROM accounts WHERE last_validated_at IS NOT NULL AND trim(last_validated_at) <> '' LIMIT 1"),
    ("subtitle_tracks.updated_at", "SELECT 1 FROM subtitle_tracks WHERE updated_at IS NOT NULL AND trim(updated_at) <> '' LIMIT 1"),
    ("subtitle_tracks.metadata_json", "SELECT 1 FROM subtitle_tracks WHERE metadata_json IS NOT NULL AND trim(metadata_json) NOT IN ('', '{}') LIMIT 1"),
    ("voice_tracks.updated_at", "SELECT 1 FROM voice_tracks WHERE updated_at IS NOT NULL AND trim(updated_at) <> '' LIMIT 1"),
    ("voice_tracks.config_json", "SELECT 1 FROM voice_tracks WHERE config_json IS NOT NULL AND trim(config_json) NOT IN ('', '{}') LIMIT 1"),
    ("voice_tracks.version", "SELECT 1 FROM voice_tracks WHERE version IS NOT NULL AND version <> 1 LIMIT 1"),
    ("assets.thumbnail_generated_at", "SELECT 1 FROM assets WHERE thumbnail_generated_at IS NOT NULL AND trim(thumbnail_generated_at) <> '' LIMIT 1"),
    ("assets.group_id", "SELECT 1 FROM assets WHERE group_id IS NOT NULL AND trim(group_id) <> '' LIMIT 1"),
    ("projects.deleted_at", "SELECT 1 FROM projects WHERE deleted_at IS NOT NULL AND trim(deleted_at) <> '' LIMIT 1"),
)

_P0_DATA_TABLES = tuple(_CHECKS) + (
    "knowledge_snapshots",
    "account_publish_defaults",
    "runtime_events",
    "asset_groups",
    "device_workspace_logs",
    "export_profiles",
    "publish_receipts",
)


def upgrade() -> None:
    _validate_required_schema()
    _validate_references_and_versions()
    _enforce_required_columns()
    for table_name, checks in _CHECKS.items():
        _ensure_checks(table_name, checks)
    for constraint_name, definition in _FOREIGN_KEYS.items():
        _ensure_foreign_key(constraint_name, *definition)
    for index_name, (table_name, columns) in _ACCOUNT_INDEXES.items():
        _ensure_index(index_name, table_name, columns)
    for index_name, (table_name, columns, predicate) in _ACTIVE_INDEXES.items():
        _ensure_index(
            index_name,
            table_name,
            columns,
            unique=True,
            sqlite_where=sa.text(predicate),
        )
    _ensure_account_scope_triggers()


def _validate_required_schema() -> None:
    inspector = sa.inspect(op.get_bind())
    required = set(_CHECKS) | {definition[0] for definition in _FOREIGN_KEYS.values()}
    missing = sorted(required - set(inspector.get_table_names()))
    if missing:
        _fail(f"缺少目标表：{', '.join(missing)}")
    required_columns = {
        "accounts": {"revision", "wizard_completed_at", "archived_at"},
        "device_workspaces": {"account_id"},
        "browser_instances": {"account_id"},
        "execution_bindings": {"browser_instance_id"},
        "system_config": {"ai_config_revision"},
    }
    for table_name, columns in required_columns.items():
        present = {column["name"] for column in inspector.get_columns(table_name)}
        absent = sorted(columns - present)
        if absent:
            _fail(f"表 {table_name} 缺少字段：{', '.join(absent)}")


def _validate_references_and_versions() -> None:
    bind = op.get_bind()
    foreign_key_errors = bind.execute(sa.text("PRAGMA foreign_key_check")).all()
    if foreign_key_errors:
        _fail(f"检测到 {len(foreign_key_errors)} 条孤儿外键")
    checks = (
        (
            "账号连接引用了其他账号的执行绑定",
            """
            SELECT COUNT(*) FROM account_connections AS connection
            JOIN execution_bindings AS binding
              ON binding.id = connection.active_execution_binding_id
            WHERE binding.account_id <> connection.account_id
            """,
        ),
        (
            "知识来源与知识库账号不一致",
            """
            SELECT COUNT(*) FROM knowledge_sources AS source
            JOIN account_knowledge_bases AS base ON base.id = source.knowledge_base_id
            WHERE source.account_id <> base.account_id
            """,
        ),
        (
            "知识快照与知识库或定位版本账号不一致",
            """
            SELECT COUNT(*) FROM knowledge_snapshots AS snapshot
            JOIN account_knowledge_bases AS base ON base.id = snapshot.knowledge_base_id
            LEFT JOIN positioning_profiles AS profile
              ON profile.id = snapshot.positioning_profile_id
            WHERE snapshot.account_id <> base.account_id
               OR (profile.id IS NOT NULL AND snapshot.account_id <> profile.account_id)
            """,
        ),
        (
            "设备、浏览器或执行绑定存在跨账号引用",
            """
            SELECT COUNT(*) FROM execution_bindings AS binding
            JOIN device_workspaces AS workspace ON workspace.id = binding.device_workspace_id
            LEFT JOIN browser_instances AS browser ON browser.id = binding.browser_instance_id
            WHERE binding.status = 'active'
              AND (
                    workspace.account_id IS NULL
                 OR workspace.account_id <> binding.account_id
                 OR browser.id IS NULL
                 OR browser.account_id IS NULL
                 OR browser.account_id <> binding.account_id
                 OR browser.workspace_id <> workspace.id
              )
            """,
        ),
        (
            "待新增账号范围外键存在孤儿引用",
            """
            SELECT
                (SELECT COUNT(*) FROM assets AS asset
                 WHERE asset.group_id IS NOT NULL
                   AND NOT EXISTS (SELECT 1 FROM asset_groups AS group_row
                                   WHERE group_row.id = asset.group_id))
              + (SELECT COUNT(*) FROM device_workspaces AS workspace
                 WHERE workspace.account_id IS NOT NULL
                   AND NOT EXISTS (SELECT 1 FROM accounts AS account
                                   WHERE account.id = workspace.account_id))
              + (SELECT COUNT(*) FROM browser_instances AS browser
                 WHERE browser.account_id IS NOT NULL
                   AND NOT EXISTS (SELECT 1 FROM accounts AS account
                                   WHERE account.id = browser.account_id))
              + (SELECT COUNT(*) FROM execution_bindings AS binding
                 WHERE binding.browser_instance_id IS NOT NULL
                   AND NOT EXISTS (SELECT 1 FROM browser_instances AS browser
                                   WHERE browser.id = binding.browser_instance_id))
            """,
        ),
        (
            "事件 topic 为空",
            "SELECT COUNT(*) FROM runtime_events WHERE topic IS NULL OR length(trim(topic)) = 0",
        ),
    )
    for issue, query in checks:
        count = int(bind.execute(sa.text(query)).scalar_one())
        if count:
            _fail(f"{issue}，共 {count} 条")
    for table_name, constraints in _CHECKS.items():
        for constraint_name, condition in constraints.items():
            invalid_count = int(
                bind.execute(
                    sa.text(f"SELECT COUNT(*) FROM {table_name} WHERE NOT ({condition})")
                ).scalar_one()
            )
            if invalid_count:
                _fail(f"约束 {constraint_name} 有 {invalid_count} 条不合规记录")
    for table_name, key_column in (
        ("positioning_profiles", "account_id"),
        ("brand_kits", "account_id"),
        ("prompt_profiles", "profile_key"),
        ("composition_template_profiles", "template_key"),
        ("account_ai_recipes", "account_id"),
    ):
        duplicate_count = int(
            bind.execute(
                sa.text(
                    f"""
                    SELECT COUNT(*) FROM (
                        SELECT {key_column}
                        FROM {table_name}
                        WHERE status = 'active'
                        GROUP BY {key_column}
                        HAVING COUNT(*) > 1
                    )
                    """
                )
            ).scalar_one()
        )
        if duplicate_count:
            _fail(f"表 {table_name} 存在 {duplicate_count} 组重复活动版本")


def _enforce_required_columns() -> None:
    with op.batch_alter_table("accounts", recreate="always") as batch:
        batch.alter_column("revision", existing_type=sa.Integer(), nullable=False)
    with op.batch_alter_table("system_config", recreate="always") as batch:
        batch.alter_column("ai_config_revision", existing_type=sa.Integer(), nullable=False)


def _ensure_checks(table_name: str, checks: dict[str, str]) -> None:
    existing = {
        constraint.get("name")
        for constraint in sa.inspect(op.get_bind()).get_check_constraints(table_name)
    }
    missing = [(name, condition) for name, condition in checks.items() if name not in existing]
    if not missing:
        return
    with op.batch_alter_table(table_name, recreate="always") as batch:
        for constraint_name, condition in missing:
            batch.create_check_constraint(constraint_name, condition)


def _ensure_foreign_key(
    constraint_name: str,
    table_name: str,
    referred_table: str,
    local_columns: tuple[str, ...],
    remote_columns: tuple[str, ...],
    ondelete: str,
) -> None:
    foreign_keys = sa.inspect(op.get_bind()).get_foreign_keys(table_name)
    if any(
        tuple(item.get("constrained_columns") or ()) == local_columns
        and item.get("referred_table") == referred_table
        for item in foreign_keys
    ):
        return
    with op.batch_alter_table(table_name, recreate="always") as batch:
        batch.create_foreign_key(
            constraint_name,
            referred_table,
            list(local_columns),
            list(remote_columns),
            ondelete=ondelete,
        )


def _ensure_index(
    index_name: str,
    table_name: str,
    columns: Iterable[str],
    *,
    unique: bool = False,
    sqlite_where: sa.ClauseElement | None = None,
) -> None:
    existing = {item["name"] for item in sa.inspect(op.get_bind()).get_indexes(table_name)}
    if index_name not in existing:
        op.create_index(
            index_name,
            table_name,
            list(columns),
            unique=unique,
            sqlite_where=sqlite_where,
        )


def _ensure_account_scope_triggers() -> None:
    bind = op.get_bind()
    existing = {
        str(row[0])
        for row in bind.execute(
            sa.text("SELECT name FROM sqlite_master WHERE type = 'trigger'")
        ).all()
    }
    for trigger_name, trigger_sql in _ACCOUNT_SCOPE_TRIGGERS.items():
        if trigger_name not in existing:
            bind.execute(sa.text(trigger_sql))


def _fail(message: str) -> None:
    log.error("P0 迁移数据验证失败", extra={"validation_issue": message})
    raise RuntimeError(f"P0_MIGRATION_VALIDATION_FAILED: {message}")


def downgrade() -> None:
    _refuse_data_bearing_downgrade()
    for trigger_name in reversed(tuple(_ACCOUNT_SCOPE_TRIGGERS)):
        op.execute(sa.text(f'DROP TRIGGER IF EXISTS "{trigger_name}"'))
    for index_name, (table_name, _, _) in reversed(tuple(_ACTIVE_INDEXES.items())):
        _drop_index_if_exists(index_name, table_name)
    for index_name, (table_name, _) in reversed(tuple(_ACCOUNT_INDEXES.items())):
        _drop_index_if_exists(index_name, table_name)
    for constraint_name, definition in reversed(tuple(_FOREIGN_KEYS.items())):
        table_name = definition[0]
        names = {
            item.get("name") for item in sa.inspect(op.get_bind()).get_foreign_keys(table_name)
        }
        if constraint_name in names:
            with op.batch_alter_table(table_name, recreate="always") as batch:
                batch.drop_constraint(constraint_name, type_="foreignkey")
    for table_name, checks in reversed(tuple(_CHECKS.items())):
        existing = {
            constraint.get("name")
            for constraint in sa.inspect(op.get_bind()).get_check_constraints(table_name)
        }
        removable = [name for name in checks if name in existing]
        if removable:
            with op.batch_alter_table(table_name, recreate="always") as batch:
                for constraint_name in removable:
                    batch.drop_constraint(constraint_name, type_="check")
    with op.batch_alter_table("system_config", recreate="always") as batch:
        batch.alter_column("ai_config_revision", existing_type=sa.Integer(), nullable=True)
    with op.batch_alter_table("accounts", recreate="always") as batch:
        batch.alter_column("revision", existing_type=sa.Integer(), nullable=True)


def _drop_index_if_exists(index_name: str, table_name: str) -> None:
    existing = {item["name"] for item in sa.inspect(op.get_bind()).get_indexes(table_name)}
    if index_name in existing:
        op.drop_index(index_name, table_name=table_name)


def _refuse_data_bearing_downgrade() -> None:
    bind = op.get_bind()
    populated = [
        table_name
        for table_name in _P0_DATA_TABLES
        if bind.execute(sa.text(f'SELECT 1 FROM "{table_name}" LIMIT 1')).first()
    ]
    populated_columns = [
        label
        for label, query in _ADDED_COLUMN_DATA_CHECKS
        if bind.execute(sa.text(query)).first()
    ]
    if populated or populated_columns:
        names = ", ".join(sorted(populated)) or "无"
        column_names = ", ".join(sorted(populated_columns)) or "无"
        log.error(
            "P0 切换迁移拒绝有数据降级",
            extra={"table_names": names, "column_names": column_names},
        )
        raise RuntimeError(
            "P0_DOWNGRADE_REQUIRES_BACKUP: 已存在 P0 数据，禁止自动移除切换约束；"
            f"请恢复迁移前备份。涉及表：{names}；涉及字段：{column_names}"
        )
