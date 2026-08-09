from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

from alembic import command
import pytest

from tests.runtime.p0c_migration_test_support import (
    column_names,
    database_version,
    insert_account,
    migration_config,
    rows,
)

REVISION_0019 = "0019_p0_account_vertical_chain"
REVISION_0020 = "0020_p0e_ai_vertical_chain"


def test_0020_backfills_prompt_revision_and_deterministic_recipe_hash(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "p0e-backfill.db"
    config = migration_config(database_path)
    command.upgrade(config, REVISION_0019)
    with sqlite3.connect(database_path) as connection:
        _insert_prompt(connection, version=3)
        _insert_recipe(connection, account_id="account-migration")
        connection.commit()

    command.upgrade(config, REVISION_0020)

    assert database_version(database_path) == REVISION_0020
    assert rows(
        database_path,
        "SELECT version, revision FROM prompt_profiles",
    ) == [(3, 3)]
    digest = rows(
        database_path,
        "SELECT content_hash FROM account_ai_recipes",
    )[0][0]
    assert digest == _expected_recipe_hash()
    assert {"revision"} <= column_names(database_path, "prompt_profiles")
    assert {"content_hash"} <= column_names(
        database_path,
        "account_ai_recipes",
    )


def test_0020_constraints_reject_invalid_revision_and_recipe_hash(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "p0e-constraints.db"
    command.upgrade(migration_config(database_path), REVISION_0020)

    with sqlite3.connect(database_path) as connection:
        with pytest.raises(
            sqlite3.IntegrityError,
            match="ck_prompt_profiles_version",
        ):
            _insert_prompt(connection, version=1, revision=0)
        _insert_recipe(
            connection,
            account_id="account-constraint",
            content_hash="a" * 64,
        )
        connection.commit()
        with pytest.raises(
            sqlite3.IntegrityError,
            match="ck_account_ai_recipes_content_hash",
        ):
            connection.execute(
                """
                UPDATE account_ai_recipes
                SET content_hash = 'NOT-A-VALID-HASH'
                WHERE id = 'recipe-migration'
                """
            )


def test_0020_invalid_legacy_recipe_json_rolls_back_atomically(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "p0e-invalid-json.db"
    config = migration_config(database_path)
    command.upgrade(config, REVISION_0019)
    with sqlite3.connect(database_path) as connection:
        _insert_recipe(
            connection,
            account_id="account-invalid-json",
            route_overrides_json="{invalid-json",
        )
        connection.commit()

    with pytest.raises(
        RuntimeError,
        match="P0E_MIGRATION_VALIDATION_FAILED.*JSON 无法解析",
    ):
        command.upgrade(config, REVISION_0020)

    assert database_version(database_path) == REVISION_0019
    assert "revision" not in column_names(
        database_path,
        "prompt_profiles",
    )
    assert "content_hash" not in column_names(
        database_path,
        "account_ai_recipes",
    )


def test_0020_refuses_data_bearing_downgrade(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "p0e-downgrade-guard.db"
    config = migration_config(database_path)
    command.upgrade(config, REVISION_0020)
    with sqlite3.connect(database_path) as connection:
        _insert_prompt(connection, version=1, revision=1)
        connection.commit()

    with pytest.raises(
        RuntimeError,
        match="P0E_DOWNGRADE_REQUIRES_BACKUP",
    ):
        command.downgrade(config, REVISION_0019)

    assert database_version(database_path) == REVISION_0020
    assert "revision" in column_names(database_path, "prompt_profiles")


def test_0020_allows_empty_downgrade_to_0019(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "p0e-empty-downgrade.db"
    config = migration_config(database_path)
    command.upgrade(config, REVISION_0020)

    command.downgrade(config, REVISION_0019)

    assert database_version(database_path) == REVISION_0019
    assert "revision" not in column_names(
        database_path,
        "prompt_profiles",
    )
    assert "content_hash" not in column_names(
        database_path,
        "account_ai_recipes",
    )


def _insert_prompt(
    connection: sqlite3.Connection,
    *,
    version: int,
    revision: int | None = None,
) -> None:
    columns = [
        "id",
        "profile_key",
        "name",
        "capability_key",
        "version",
        "status",
        "system_prompt",
        "task_template",
        "variables_schema_json",
        "output_schema_json",
        "visual_style_prefix",
        "safety_constraints_json",
        "content_hash",
        "created_from_id",
        "created_at",
        "activated_at",
    ]
    values: list[object] = [
        "prompt-migration",
        "prompt-migration",
        "迁移 Prompt",
        "script_generation",
        version,
        "draft",
        "系统提示",
        "任务模板",
        "{}",
        "{}",
        None,
        "{}",
        "a" * 64,
        None,
        "2026-07-26T00:00:00Z",
        None,
    ]
    if revision is not None:
        columns.append("revision")
        values.append(revision)
    placeholders = ", ".join("?" for _ in values)
    connection.execute(
        f"""
        INSERT INTO prompt_profiles ({", ".join(columns)})
        VALUES ({placeholders})
        """,
        values,
    )


def _insert_recipe(
    connection: sqlite3.Connection,
    *,
    account_id: str,
    route_overrides_json: str = "{}",
    content_hash: str | None = None,
) -> None:
    insert_account(connection, account_id, status="draft")
    columns = [
        "id",
        "account_id",
        "name",
        "version",
        "status",
        "route_overrides_json",
        "visual_style_json",
        "voice_profile_ref",
        "composition_template_ref",
        "cost_policy_json",
        "fallback_policy_json",
        "source_ai_config_revision",
        "validation_status",
        "validation_issues_json",
        "revision",
        "created_from_id",
        "created_at",
        "activated_at",
    ]
    values: list[object] = [
        "recipe-migration",
        account_id,
        "迁移 Recipe",
        1,
        "draft",
        route_overrides_json,
        '{"tone":"clean"}',
        None,
        None,
        '{"dailyLimit":10}',
        '{"retry":1}',
        7,
        "incomplete",
        "[]",
        1,
        None,
        "2026-07-26T00:00:00Z",
        None,
    ]
    if content_hash is not None:
        columns.append("content_hash")
        values.append(content_hash)
    placeholders = ", ".join("?" for _ in values)
    connection.execute(
        f"""
        INSERT INTO account_ai_recipes ({", ".join(columns)})
        VALUES ({placeholders})
        """,
        values,
    )


def _expected_recipe_hash() -> str:
    payload = {
        "name": "迁移 Recipe",
        "routeOverrides": {},
        "visualStyle": {"tone": "clean"},
        "voiceProfileRef": None,
        "compositionTemplateRef": None,
        "costPolicy": {"dailyLimit": 10},
        "fallbackPolicy": {"retry": 1},
        "sourceAiConfigRevision": 7,
    }
    return hashlib.sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()

