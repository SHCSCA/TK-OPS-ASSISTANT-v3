from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config
import pytest

from persistence.engine import create_runtime_engine, initialize_domain_schema
from persistence.migration import DatabaseSchemaKind, inspect_database_schema


REVISION_0014 = "0014_magic_cut_suggestion_drafts"
REVISION_0015 = "0015_p0_expand"
REVISION_0016 = "0016_p0_backfill"
REVISION_0017 = "0017_p0_enforce_and_cutover"
REVISION_0018 = "0018_p0_runtime_kernel"
REVISION_0020 = "0020_p0e_ai_vertical_chain"
REVISION_0021 = "0021_p0g_execution_environment_closure"
REVISION_0022 = "0022_p0g_production_hardening"


def test_empty_database_upgrades_downgrades_and_reupgrades(tmp_path: Path) -> None:
    database_path = tmp_path / "empty.db"
    config = _config(database_path)

    command.upgrade(config, "head")

    assert _version(database_path) == REVISION_0022
    assert {
        "asset_groups",
        "device_workspace_logs",
        "export_profiles",
        "publish_receipts",
        "account_connections",
        "positioning_profiles",
        "account_knowledge_bases",
        "knowledge_sources",
        "knowledge_snapshots",
        "brand_kits",
        "account_publish_defaults",
        "account_config_copy_runs",
        "provider_profiles",
        "model_profiles",
        "model_capabilities",
        "prompt_profiles",
        "capability_routes",
        "composition_template_profiles",
        "account_ai_recipes",
        "runtime_tasks",
        "runtime_events",
        "account_login_sessions",
    }.issubset(_tables(database_path))
    assert "ck_accounts_status" in _check_constraints(database_path, "accounts")
    assert "uq_runtime_events_topic_sequence" in _indexes(
        database_path, "runtime_events", include_auto=True
    )
    assert {
        "idempotency_key_hash",
        "request_hash",
        "handler_version",
    }.issubset(_columns(database_path, "runtime_tasks"))
    assert {
        "uq_runtime_tasks_system_idempotency",
        "uq_runtime_tasks_account_idempotency",
    }.issubset(_indexes(database_path, "runtime_tasks"))
    assert "revision" in _columns(database_path, "prompt_profiles")
    assert "content_hash" in _columns(database_path, "account_ai_recipes")

    command.downgrade(config, REVISION_0014)

    assert _version(database_path) == REVISION_0014
    assert "runtime_events" not in _tables(database_path)
    command.upgrade(config, "head")
    assert _version(database_path) == REVISION_0022


def test_standard_0014_reconciles_orm_only_tables_and_columns(tmp_path: Path) -> None:
    database_path = tmp_path / "standard-0014.db"
    config = _config(database_path)
    command.upgrade(config, REVISION_0014)

    assert not {
        "asset_groups",
        "device_workspace_logs",
        "export_profiles",
        "publish_receipts",
    }.intersection(_tables(database_path))
    assert "deleted_at" not in _columns(database_path, "projects")
    assert "group_id" not in _columns(database_path, "assets")

    command.upgrade(config, "head")

    assert _version(database_path) == REVISION_0022
    assert {
        "asset_groups",
        "device_workspace_logs",
        "export_profiles",
        "publish_receipts",
    }.issubset(_tables(database_path))
    assert {"deleted_at"}.issubset(_columns(database_path, "projects"))
    assert {"group_id", "thumbnail_generated_at"}.issubset(
        _columns(database_path, "assets")
    )
    assert {"version", "config_json", "updated_at"}.issubset(
        _columns(database_path, "voice_tracks")
    )
    assert {"metadata_json", "updated_at"}.issubset(
        _columns(database_path, "subtitle_tracks")
    )
    assert {"account_id"}.issubset(_columns(database_path, "device_workspaces"))
    assert {"account_id"}.issubset(_columns(database_path, "browser_instances"))
    assert {"browser_instance_id"}.issubset(
        _columns(database_path, "execution_bindings")
    )


def test_recognized_fresh_runtime_cohort_explicitly_stamps_and_round_trips(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "fresh-runtime.db"
    config = _config(database_path)
    engine = create_runtime_engine(database_path)
    initialize_domain_schema(engine)
    engine.dispose()

    inspection = inspect_database_schema(database_path)
    assert inspection.kind is DatabaseSchemaKind.LEGACY_FRESH_RUNTIME
    assert inspection.table_count == 38
    assert _foreign_key_target(database_path, "assets", "group_id") == "asset_groups"

    # 本测试先显式核验冻结指纹，再模拟 runner 已批准后的 stamp。
    command.stamp(config, REVISION_0014)
    command.upgrade(config, "head")

    assert _version(database_path) == REVISION_0022
    assert _foreign_key_target(database_path, "assets", "group_id") == "asset_groups"
    assert (
        _foreign_key_target(database_path, "execution_bindings", "browser_instance_id")
        == "browser_instances"
    )

    command.downgrade(config, REVISION_0014)

    assert _version(database_path) == REVISION_0014
    assert "group_id" not in _columns(database_path, "assets")
    assert _foreign_key_target(database_path, "assets", "group_id") is None
    command.upgrade(config, "head")
    assert _version(database_path) == REVISION_0022


def test_revision_boundaries_and_conservative_backfill(tmp_path: Path) -> None:
    database_path = tmp_path / "backfill.db"
    config = _config(database_path)
    command.upgrade(config, REVISION_0014)
    _insert_legacy_records(database_path)

    command.upgrade(config, REVISION_0015)
    assert _version(database_path) == REVISION_0015
    assert _scalar(database_path, "SELECT COUNT(*) FROM provider_profiles") == 0
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "UPDATE execution_bindings SET browser_instance_id = 'browser-bound' "
            "WHERE id = 'binding-bound'"
        )
        connection.execute(
            "UPDATE execution_bindings SET browser_instance_id = 'browser-shared' "
            "WHERE id IN ('binding-shared-a', 'binding-shared-b')"
        )
        connection.commit()

    command.upgrade(config, REVISION_0016)

    assert _version(database_path) == REVISION_0016
    assert _row(
        database_path,
        "SELECT status, status_reason_code FROM accounts WHERE id = 'account-unbound'",
    ) == ("unbound", "EXECUTION_BINDING_REQUIRED")
    assert _row(
        database_path,
        "SELECT status, status_reason_code FROM accounts WHERE id = 'account-bound'",
    ) == ("attention", "MIGRATED_CONFIGURATION_UNVERIFIED")
    assert _row(
        database_path,
        "SELECT status, status_reason_code FROM accounts WHERE id = 'account-unknown'",
    ) == ("attention", "MIGRATED_STATUS_UNKNOWN")
    assert _row(
        database_path,
        "SELECT account_id FROM device_workspaces WHERE id = 'workspace-bound'",
    ) == ("account-bound",)
    assert _row(
        database_path,
        "SELECT account_id FROM device_workspaces WHERE id = 'workspace-shared'",
    ) == (None,)
    assert _row(
        database_path,
        "SELECT account_id FROM browser_instances WHERE id = 'browser-shared'",
    ) == (None,)
    assert _rows(
        database_path,
        "SELECT status, browser_instance_id FROM execution_bindings "
        "WHERE id IN ('binding-shared-a', 'binding-shared-b') ORDER BY id",
    ) == [("inactive", None), ("inactive", None)]
    assert _row(
        database_path,
        "SELECT account_id FROM browser_instances WHERE id = 'browser-bound'",
    ) == ("account-bound",)
    assert _row(
        database_path,
        "SELECT enabled, health_status, credential_ref FROM provider_profiles "
        "WHERE id = 'openai'",
    ) == (0, "unknown", None)
    assert _row(
        database_path,
        "SELECT enabled, discovery_source FROM model_profiles WHERE id = 'legacy-model'",
    ) == (0, "migrated")
    assert _row(
        database_path,
        "SELECT declared_supported, adapter_supported, contract_verified "
        "FROM model_capabilities WHERE model_profile_id = 'legacy-model' "
        "AND capability_key = 'script_generation'",
    ) == (1, 0, 0)
    assert _row(
        database_path,
        "SELECT enabled, validation_status FROM capability_routes "
        "WHERE capability_key = 'script_generation'",
    ) == (0, "incomplete")
    assert _scalar(
        database_path,
        "SELECT COUNT(*) FROM capability_routes WHERE capability_key = 'magic_cut'",
    ) == 0
    assert _scalar(
        database_path,
        "SELECT COUNT(*) FROM prompt_profiles "
        "WHERE capability_key IN ('magic_cut', 'unknown_capability')",
    ) == 0
    assert _scalar(
        database_path,
        "SELECT COUNT(*) FROM prompt_profiles WHERE status <> 'draft'",
    ) == 0
    assert _scalar(
        database_path,
        "SELECT ai_config_revision FROM system_config WHERE id = 1",
    ) == 1
    event_payload = json.loads(
        str(
            _scalar(
                database_path,
                "SELECT payload_json FROM runtime_events "
                "WHERE event_id = 'migration:0016_p0_backfill'",
            )
        )
    )
    assert event_payload["readinessPolicy"] == "unverified"
    assert {"magic_cut", "unknown_capability"}.issubset(
        set(event_payload["skippedCapabilityKeys"])
    )
    assert event_payload["mappedRows"]["detachedBindings"] == 2
    assert "旧系统提示词" not in json.dumps(event_payload, ensure_ascii=False)

    command.upgrade(config, REVISION_0017)
    assert _version(database_path) == REVISION_0017
    assert "uq_positioning_profiles_one_active" in _indexes(
        database_path, "positioning_profiles"
    )
    assert "ix_runtime_tasks_account_updated" in _indexes(
        database_path, "runtime_tasks"
    )
    command.upgrade(config, REVISION_0018)
    assert _version(database_path) == REVISION_0018
    migration_event = _row(
        database_path,
        "SELECT topic, sequence, published_at FROM runtime_events "
        "WHERE event_id = 'migration:0016_p0_backfill'",
    )
    assert migration_event[:2] == ("system:migrations", 1)
    assert migration_event[2] not in (None, "")


def test_0017_rejects_duplicate_active_versions(tmp_path: Path) -> None:
    database_path = tmp_path / "duplicate-active.db"
    config = _config(database_path)
    command.upgrade(config, REVISION_0016)
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO accounts (
                id, name, platform, status, created_at, updated_at,
                wizard_completed_at, revision
            ) VALUES ('account-1', '账号', 'tiktok', 'unbound', '2026-01-01',
                      '2026-01-01', '2026-01-01', 1)
            """
        )
        for version in (1, 2):
            connection.execute(
                """
                INSERT INTO positioning_profiles (
                    id, account_id, version, status, audience_json,
                    content_pillars_json, voice_style_json, prohibited_terms_json,
                    publishing_constraints_json, summary, revision, created_at
                ) VALUES (?, 'account-1', ?, 'active', '{}', '[]', '{}', '[]',
                          '{}', '', 1, '2026-01-01')
                """,
                (f"position-{version}", version),
            )
        connection.commit()

    with pytest.raises(RuntimeError, match="重复活动版本"):
        command.upgrade(config, REVISION_0017)

    assert _version(database_path) == REVISION_0016


def test_data_bearing_p0_schema_refuses_lossy_downgrade(tmp_path: Path) -> None:
    database_path = tmp_path / "downgrade-refusal.db"
    config = _config(database_path)
    command.upgrade(config, "head")
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO provider_profiles (
                id, name, adapter_type, base_url, timeout_ms, max_concurrency,
                enabled, health_status, revision, created_at, updated_at
            ) VALUES ('provider-1', 'Provider', 'direct_api', '', 30000, 1,
                      0, 'unknown', 1, '2026-01-01', '2026-01-01')
            """
        )
        connection.commit()

    with pytest.raises(RuntimeError, match="P0_DOWNGRADE_REQUIRES_BACKUP"):
        command.downgrade(config, REVISION_0014)

    assert _version(database_path) == REVISION_0020
    assert _scalar(
        database_path,
        "SELECT COUNT(*) FROM provider_profiles WHERE id = 'provider-1'",
    ) == 1
    assert "revision" in _columns(database_path, "prompt_profiles")
    assert "content_hash" in _columns(database_path, "account_ai_recipes")


def _config(database_path: Path) -> Config:
    repo_root = Path(__file__).resolve().parents[2]
    runtime_root = repo_root / "apps" / "py-runtime"
    config = Config(str(runtime_root / "alembic.ini"))
    config.set_main_option("script_location", str(runtime_root / "alembic"))
    config.attributes["database_url"] = f"sqlite:///{database_path.as_posix()}"
    return config


def _insert_legacy_records(database_path: Path) -> None:
    with sqlite3.connect(database_path) as connection:
        accounts = (
            ("account-unbound", "未绑定账号", "active"),
            ("account-bound", "已有绑定账号", "active"),
            ("account-unknown", "未知状态账号", "unexpected"),
            ("account-shared-a", "共享账号 A", "active"),
            ("account-shared-b", "共享账号 B", "active"),
        )
        for account_id, name, status in accounts:
            connection.execute(
                """
                INSERT INTO accounts (
                    id, name, platform, status, created_at, updated_at
                ) VALUES (?, ?, 'tiktok', ?, '2026-01-01', '2026-01-01')
                """,
                (account_id, name, status),
            )
        connection.execute(
            """
            INSERT INTO device_workspaces (
                id, name, root_path, status, error_count, created_at, updated_at
            ) VALUES ('workspace-bound', '本机工作区', 'C:/workspace', 'online', 0,
                      '2026-01-01', '2026-01-01')
            """
        )
        connection.execute(
            """
            INSERT INTO device_workspaces (
                id, name, root_path, status, error_count, created_at, updated_at
            ) VALUES ('workspace-shared', '共享工作区', 'C:/workspace-shared', 'online', 0,
                      '2026-01-01', '2026-01-01')
            """
        )
        connection.execute(
            """
            INSERT INTO browser_instances (
                id, workspace_id, name, profile_path, status, created_at, updated_at
            ) VALUES ('browser-bound', 'workspace-bound', '浏览器', 'C:/profile',
                      'stopped', '2026-01-01', '2026-01-01')
            """
        )
        connection.execute(
            """
            INSERT INTO browser_instances (
                id, workspace_id, name, profile_path, status, created_at, updated_at
            ) VALUES ('browser-shared', 'workspace-shared', '共享浏览器',
                      'C:/profile-shared', 'stopped', '2026-01-01', '2026-01-01')
            """
        )
        connection.execute(
            """
            INSERT INTO execution_bindings (
                id, account_id, device_workspace_id, status, created_at, updated_at
            ) VALUES ('binding-bound', 'account-bound', 'workspace-bound', 'active',
                      '2026-01-01', '2026-01-01')
            """
        )
        for account_id, binding_id in (
            ("account-shared-a", "binding-shared-a"),
            ("account-shared-b", "binding-shared-b"),
        ):
            connection.execute(
                """
                INSERT INTO execution_bindings (
                    id, account_id, device_workspace_id, status, created_at, updated_at
                ) VALUES (?, ?, 'workspace-shared', 'active', '2026-01-01', '2026-01-01')
                """,
                (binding_id, account_id),
            )
        connection.execute(
            "INSERT INTO system_config (id, document, revision, updated_at) "
            "VALUES (1, '{}', 1, '2026-01-01')"
        )
        connection.execute(
            "INSERT INTO ai_provider_settings (provider_id, base_url, updated_at) "
            "VALUES ('openai', 'https://api.openai.com/v1', '2026-01-01')"
        )
        connection.execute(
            """
            INSERT INTO ai_provider_health (
                provider_id, label, readiness, updated_at
            ) VALUES ('openai', 'OpenAI', 'ready', '2026-01-01')
            """
        )
        connection.execute(
            """
            INSERT INTO ai_provider_models (
                id, provider_id, model_id, display_name, capability_kinds_json,
                input_modalities_json, output_modalities_json, context_window,
                default_for_json, enabled, created_at, updated_at
            ) VALUES ('legacy-model', 'openai', 'gpt-legacy', '旧模型',
                      '["text_generation"]', '["text"]', '["text"]', 4096,
                      '["script_generation"]', 1, '2026-01-01', '2026-01-01')
            """
        )
        for capability_id in (
            "script_generation",
            "magic_cut",
            "unknown_capability",
        ):
            connection.execute(
                """
                INSERT INTO ai_capability_configs (
                    capability_id, enabled, provider, model, agent_role,
                    system_prompt, user_prompt_template, updated_at
                ) VALUES (?, 1, 'openai', 'gpt-legacy', '旧角色',
                          '旧系统提示词', '旧任务模板', '2026-01-01')
                """,
                (capability_id,),
            )
        connection.execute(
            """
            INSERT INTO prompt_templates (
                id, kind, name, description, content, created_at, updated_at
            ) VALUES ('template-1', 'script_generation', '旧模板', '',
                      '模板正文', '2026-01-01', '2026-01-01')
            """
        )
        connection.execute(
            """
            INSERT INTO prompt_templates (
                id, kind, name, description, content, created_at, updated_at
            ) VALUES ('template-magic-cut', 'magic_cut', '旧剪辑模板', '',
                      '不得迁入 PromptProfile', '2026-01-01', '2026-01-01')
            """
        )
        connection.commit()


def _tables(database_path: Path) -> set[str]:
    with sqlite3.connect(database_path) as connection:
        return {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            )
        }


def _columns(database_path: Path, table_name: str) -> set[str]:
    with sqlite3.connect(database_path) as connection:
        return {
            str(row[1])
            for row in connection.execute(f'PRAGMA table_info("{table_name}")')
        }


def _version(database_path: Path) -> str:
    return str(_scalar(database_path, "SELECT version_num FROM alembic_version"))


def _scalar(database_path: Path, query: str) -> object:
    with sqlite3.connect(database_path) as connection:
        row = connection.execute(query).fetchone()
    assert row is not None
    return row[0]


def _row(database_path: Path, query: str) -> tuple[object, ...]:
    with sqlite3.connect(database_path) as connection:
        row = connection.execute(query).fetchone()
    assert row is not None
    return tuple(row)


def _rows(database_path: Path, query: str) -> list[tuple[object, ...]]:
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(query).fetchall()
    return [tuple(row) for row in rows]


def _check_constraints(database_path: Path, table_name: str) -> set[str]:
    sql = str(
        _scalar(
            database_path,
            "SELECT sql FROM sqlite_master "
            f"WHERE type = 'table' AND name = '{table_name}'",
        )
    )
    return {
        token.split()[0]
        for token in sql.replace("\n", " ").split("CONSTRAINT ")[1:]
        if token.split()
    }


def _indexes(
    database_path: Path,
    table_name: str,
    *,
    include_auto: bool = False,
) -> set[str]:
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(f'PRAGMA index_list("{table_name}")').fetchall()
    names = {str(row[1]) for row in rows}
    if include_auto:
        with sqlite3.connect(database_path) as connection:
            sql = str(
                connection.execute(
                    "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?",
                    (table_name,),
                ).fetchone()[0]
            )
        if "uq_runtime_events_topic_sequence" in sql:
            names.add("uq_runtime_events_topic_sequence")
    return names


def _foreign_key_target(
    database_path: Path,
    table_name: str,
    column_name: str,
) -> str | None:
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(f'PRAGMA foreign_key_list("{table_name}")').fetchall()
    for row in rows:
        if str(row[3]) == column_name:
            return str(row[2])
    return None
