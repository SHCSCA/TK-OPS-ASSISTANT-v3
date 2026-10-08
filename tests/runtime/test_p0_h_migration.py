from __future__ import annotations

import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config
import pytest

REVISION_0022 = "0022_p0g_production_hardening"
REVISION_0023 = "0023_p0h_real_ai_execution"


def test_fresh_database_has_p0h_contract_and_empty_downgrade_round_trip(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "p0h-fresh.db"
    config = _config(database_path)

    command.upgrade(config, "head")

    assert _version(database_path) == REVISION_0023
    assert {
        "provider_profile_revisions",
        "model_profile_revisions",
        "capability_route_revisions",
        "ai_dependency_snapshots",
        "ai_provider_validation_runs",
        "account_assets",
        "knowledge_source_assets",
        "knowledge_index_chunks",
        "ai_execution_snapshots",
        "ai_execution_candidates",
        "ai_executions",
        "ai_execution_jobs",
        "ai_usage_records",
        "ai_execution_outputs",
        "ai_error_evidence",
    }.issubset(_tables(database_path))
    assert "active_revision_id" in _columns(
        database_path,
        "provider_profiles",
    )
    assert "dependency_snapshot_id" in _columns(
        database_path,
        "account_ai_recipes",
    )

    command.downgrade(config, REVISION_0022)
    assert _version(database_path) == REVISION_0022
    assert "ai_dependency_snapshots" not in _tables(database_path)
    command.upgrade(config, "head")
    assert _version(database_path) == REVISION_0023


def test_upgrade_backfills_revisions_fail_closed_and_refuses_lossy_downgrade(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "p0h-backfill.db"
    config = _config(database_path)
    command.upgrade(config, REVISION_0022)
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO provider_profiles (
                id, name, adapter_type, base_url, timeout_ms,
                max_concurrency, enabled, health_status, revision,
                created_at, updated_at
            ) VALUES (
                'provider-backfill', 'Provider', 'openai_compatible',
                'https://example.test/v1', 30000, 1, 1, 'ready', 2,
                '2026-08-09T00:00:00Z', '2026-08-09T00:00:00Z'
            )
            """
        )
        connection.execute(
            """
            INSERT INTO model_profiles (
                id, provider_profile_id, model_id, display_name, enabled,
                discovery_source, context_window, base_limits_json,
                revision, created_at, updated_at
            ) VALUES (
                'model-backfill', 'provider-backfill', 'model-a',
                '模型 A', 1, 'manual', 8192, '{}', 3,
                '2026-08-09T00:00:00Z', '2026-08-09T00:00:00Z'
            )
            """
        )
        connection.execute(
            """
            INSERT INTO capability_routes (
                id, capability_key, primary_model_profile_id,
                fallback_model_profile_id, prompt_profile_id, enabled,
                validation_status, validation_issues_json, revision,
                created_at, updated_at
            ) VALUES (
                'route-backfill', 'script_generation', 'model-backfill',
                NULL, NULL, 1, 'valid', '[]', 4,
                '2026-08-09T00:00:00Z', '2026-08-09T00:00:00Z'
            )
            """
        )
        connection.commit()

    command.upgrade(config, "head")

    assert _version(database_path) == REVISION_0023
    assert _scalar(
        database_path,
        "SELECT COUNT(*) FROM provider_profile_revisions",
    ) == 1
    assert _scalar(
        database_path,
        "SELECT COUNT(*) FROM model_profile_revisions",
    ) == 1
    assert _row(
        database_path,
        "SELECT status, dependency_snapshot_id FROM "
        "capability_route_revisions",
    ) == ("draft", None)
    assert _scalar(
        database_path,
        "SELECT active_revision_id FROM capability_routes "
        "WHERE id='route-backfill'",
    ) is None
    assert _scalar(
        database_path,
        "SELECT COUNT(*) FROM ai_provider_validation_runs",
    ) == 0

    with pytest.raises(RuntimeError, match="P0H_DOWNGRADE_REQUIRES_BACKUP"):
        command.downgrade(config, REVISION_0022)
    assert _version(database_path) == REVISION_0023


def _config(database_path: Path) -> Config:
    repo_root = Path(__file__).resolve().parents[2]
    runtime_root = repo_root / "apps" / "py-runtime"
    config = Config(str(runtime_root / "alembic.ini"))
    config.set_main_option("script_location", str(runtime_root / "alembic"))
    config.attributes["database_url"] = f"sqlite:///{database_path.as_posix()}"
    return config


def _version(database_path: Path) -> str:
    return str(_scalar(database_path, "SELECT version_num FROM alembic_version"))


def _tables(database_path: Path) -> set[str]:
    with sqlite3.connect(database_path) as connection:
        return {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }


def _columns(database_path: Path, table_name: str) -> set[str]:
    with sqlite3.connect(database_path) as connection:
        return {
            str(row[1])
            for row in connection.execute(f'PRAGMA table_info("{table_name}")')
        }


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
