from __future__ import annotations

import sqlite3
from pathlib import Path

from alembic import command
import pytest

from persistence.migration import validate_target_schema_contract
from tests.runtime.p0c_migration_test_support import (
    HASH_B,
    column_names as _columns,
    database_version as _version,
    insert_account as _insert_account,
    insert_binding as _insert_binding,
    insert_connection as _insert_connection,
    insert_head_source as _insert_head_source,
    insert_knowledge_base as _insert_knowledge_base,
    insert_legacy_source as _insert_legacy_source,
    insert_mutation as _insert_mutation,
    insert_real_binding_chain as _insert_real_binding_chain,
    insert_snapshot as _insert_snapshot,
    insert_workspace_and_browser as _insert_workspace_and_browser,
    migration_config as _config,
    rows as _rows,
    table_names as _tables,
    trigger_names as _triggers,
)

REVISION_0018 = "0018_p0_runtime_kernel"
REVISION_0019 = "0019_p0_account_vertical_chain"
REVISION_0020 = "0020_p0e_ai_vertical_chain"
REVISION_0021 = "0021_p0g_execution_environment_closure"
REVISION_0023 = "0023_p0h_real_ai_execution"
INVALID_LEGACY_ACCOUNT_IDS = (
    "legacy:account",
    "legacy/account",
    "_legacy",
    " legacy",
    "账号一",
    "A" * 129,
)
VALID_STABLE_ACCOUNT_IDS = (
    "A",
    "0",
    "A._-z",
    "A" + ("z" * 127),
)


def test_0019_maps_active_accounts_and_backfills_source_modes(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "p0c-backfill.db"
    config = _config(database_path)
    command.upgrade(config, REVISION_0018)

    with sqlite3.connect(database_path) as connection:
        _insert_account(connection, "account-draft", status="active")
        _insert_account(
            connection,
            "account-unbound",
            status="active",
            wizard_completed_at="2026-01-01T00:00:00Z",
        )
        _insert_account(
            connection,
            "account-attention",
            status="active",
            wizard_completed_at="2026-01-01T00:00:00Z",
        )
        _insert_real_binding_chain(connection, "account-attention")
        _insert_knowledge_base(connection, "account-attention")
        _insert_legacy_source(
            connection,
            source_id="source-url",
            account_id="account-attention",
            kind="reference",
            source_ref=" https://example.com/video ",
        )
        _insert_legacy_source(
            connection,
            source_id="source-text",
            account_id="account-attention",
            kind="text",
            source_ref="inline:legacy-text",
        )
        _insert_legacy_source(
            connection,
            source_id="source-file",
            account_id="account-attention",
            kind="document",
            source_ref="asset:legacy-document",
        )
        connection.commit()

    command.upgrade(config, REVISION_0019)

    assert _rows(
        database_path,
        """
        SELECT id, status, status_reason_code, revision
        FROM accounts
        ORDER BY id
        """,
    ) == [
        (
            "account-attention",
            "attention",
            "P0C_LEGACY_ACTIVE_HEALTH_RECHECK_REQUIRED",
            2,
        ),
        (
            "account-draft",
            "draft",
            "P0C_LEGACY_ACTIVE_DRAFT_REVIEW",
            2,
        ),
        (
            "account-unbound",
            "unbound",
            "P0C_LEGACY_ACTIVE_BINDING_REQUIRED",
            2,
        ),
    ]
    assert _rows(
        database_path,
        """
        SELECT id, source_mode, source_url
        FROM knowledge_sources
        ORDER BY id
        """,
    ) == [
        ("source-file", "file", None),
        ("source-text", "text", None),
        ("source-url", "url", "https://example.com/video"),
    ]
    assert "label" in _columns(database_path, "knowledge_snapshots")
    assert {
        "source_mode",
        "source_url",
    } <= _columns(database_path, "knowledge_sources")
    assert "runtime_mutation_idempotency" in _tables(database_path)
    command.upgrade(config, REVISION_0023)
    validate_target_schema_contract(
        database_path,
        target_revision=REVISION_0023,
    )


def test_0019_rejects_invalid_legacy_account_ids_before_backfill(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "p0c-invalid-account-id.db"
    config = _config(database_path)
    command.upgrade(config, REVISION_0018)
    with sqlite3.connect(database_path) as connection:
        for account_id in INVALID_LEGACY_ACCOUNT_IDS:
            _insert_account(connection, account_id, status="draft")
        connection.commit()

    with pytest.raises(
        RuntimeError,
        match=(
            r"P0C_MIGRATION_VALIDATION_FAILED: accounts\.id "
            r"存在不符合稳定资源 ID 语法的记录，共 6 条"
        ),
    ):
        command.upgrade(config, REVISION_0019)

    assert _version(database_path) == REVISION_0018
    assert "runtime_mutation_idempotency" not in _tables(database_path)
    assert "label" not in _columns(database_path, "knowledge_snapshots")
    assert "source_mode" not in _columns(database_path, "knowledge_sources")
    assert _rows(
        database_path,
        "SELECT COUNT(*) FROM account_knowledge_bases",
    ) == [(0,)]


def test_0019_accepts_stable_legacy_account_id_boundaries(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "p0c-valid-account-id.db"
    config = _config(database_path)
    command.upgrade(config, REVISION_0018)
    with sqlite3.connect(database_path) as connection:
        for account_id in VALID_STABLE_ACCOUNT_IDS:
            _insert_account(connection, account_id, status="draft")
        connection.commit()

    command.upgrade(config, REVISION_0019)

    assert [
        row[0]
        for row in _rows(
            database_path,
            "SELECT id FROM accounts ORDER BY length(id), id",
        )
    ] == sorted(VALID_STABLE_ACCOUNT_IDS, key=lambda value: (len(value), value))


def test_0019_constraints_reject_cross_account_and_invalid_idempotency(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "p0c-constraints.db"
    command.upgrade(_config(database_path), REVISION_0019)

    with sqlite3.connect(database_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        _insert_account(connection, "account-a", status="draft")
        _insert_account(connection, "account-b", status="draft")
        for account_id in INVALID_LEGACY_ACCOUNT_IDS:
            with pytest.raises(
                sqlite3.IntegrityError,
                match="ck_accounts_stable_id",
            ):
                _insert_account(connection, account_id, status="draft")
        with pytest.raises(
            sqlite3.IntegrityError,
            match="ck_accounts_stable_id",
        ):
            connection.execute(
                "UPDATE accounts SET id = ? WHERE id = 'account-a'",
                ("legacy:account",),
            )
        _insert_workspace_and_browser(connection, "account-a")
        _insert_workspace_and_browser(connection, "account-b")
        _insert_knowledge_base(connection, "account-a")
        _insert_knowledge_base(connection, "account-b")
        connection.execute(
            """
            INSERT INTO device_workspaces (
                id, name, root_path, status, error_count,
                created_at, updated_at
            ) VALUES ('workspace-unassigned', '未分配工作区', 'C:/unassigned',
                      'offline', 0, '2026-01-01', '2026-01-01')
            """
        )
        connection.execute(
            """
            INSERT INTO browser_instances (
                id, workspace_id, name, profile_path, status,
                created_at, updated_at
            ) VALUES ('browser-unassigned', 'workspace-unassigned', '未分配浏览器',
                      'C:/profile-unassigned', 'stopped',
                      '2026-01-01', '2026-01-01')
            """
        )
        connection.commit()

        with pytest.raises(
            sqlite3.IntegrityError,
            match="ck_accounts_status",
        ):
            _insert_account(connection, "account-active", status="active")

        with pytest.raises(
            sqlite3.IntegrityError,
            match="EXECUTION_BINDING_ACCOUNT_MISMATCH",
        ):
            _insert_binding(
                connection,
                binding_id="binding-cross",
                account_id="account-a",
                workspace_id="workspace-account-b",
                browser_id="browser-account-b",
            )

        _insert_binding(
            connection,
            binding_id="binding-a",
            account_id="account-a",
            workspace_id="workspace-account-a",
            browser_id="browser-account-a",
        )
        connection.commit()
        with pytest.raises(
            sqlite3.IntegrityError,
            match="ACCOUNT_CONNECTION_BINDING_MISMATCH",
        ):
            _insert_connection(
                connection,
                account_id="account-b",
                binding_id="binding-a",
            )
        with pytest.raises(
            sqlite3.IntegrityError,
            match="KNOWLEDGE_SNAPSHOT_ACCOUNT_MISMATCH",
        ):
            _insert_snapshot(
                connection,
                snapshot_id="snapshot-cross",
                account_id="account-b",
                knowledge_base_id="base-account-a",
            )

        _insert_mutation(
            connection,
            record_id="mutation-system",
            scope="system",
            account_id=None,
        )
        _insert_mutation(
            connection,
            record_id="mutation-account-a",
            scope="account",
            account_id="account-a",
        )
        _insert_mutation(
            connection,
            record_id="mutation-account-b",
            scope="account",
            account_id="account-b",
        )
        connection.commit()

        with pytest.raises(sqlite3.IntegrityError):
            _insert_mutation(
                connection,
                record_id="mutation-system-duplicate",
                scope="system",
                account_id=None,
            )
        with pytest.raises(
            sqlite3.IntegrityError,
            match="ck_runtime_mutation_account_scope",
        ):
            _insert_mutation(
                connection,
                record_id="mutation-bad-scope",
                scope="account",
                account_id=None,
                key_hash=HASH_B,
            )
        with pytest.raises(
            sqlite3.IntegrityError,
            match="ck_runtime_mutation_request_hash",
        ):
            _insert_mutation(
                connection,
                record_id="mutation-bad-hash",
                scope="system",
                account_id=None,
                key_hash=HASH_B,
                request_hash="NOT-A-HASH",
            )
        with pytest.raises(
            sqlite3.IntegrityError,
            match="FOREIGN KEY constraint failed",
        ):
            _insert_mutation(
                connection,
                record_id="mutation-orphan-account",
                scope="account",
                account_id="account-missing",
                key_hash=HASH_B,
            )
        with pytest.raises(
            sqlite3.IntegrityError,
            match="ck_knowledge_sources_source_url",
        ):
            _insert_head_source(
                connection,
                source_id="source-bad-url",
                account_id="account-a",
                source_mode="url",
                source_url="file:///private/video.mp4",
            )


def test_0019_reverse_scope_triggers_reject_reassignment(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "p0c-reverse-scope.db"
    command.upgrade(_config(database_path), REVISION_0019)

    with sqlite3.connect(database_path) as connection:
        _insert_account(connection, "account-a", status="draft")
        _insert_account(connection, "account-b", status="draft")
        _insert_real_binding_chain(connection, "account-a")
        _insert_knowledge_base(connection, "account-a")
        _insert_head_source(
            connection,
            source_id="source-a",
            account_id="account-a",
            source_mode="text",
            source_url=None,
        )
        connection.execute(
            """
            INSERT INTO positioning_profiles (
                id, account_id, version, status, audience_json,
                content_pillars_json, voice_style_json, prohibited_terms_json,
                publishing_constraints_json, summary, revision, created_at
            ) VALUES ('profile-a', 'account-a', 1, 'draft', '{}', '[]',
                      '{}', '[]', '{}', '', 1, '2026-01-01')
            """
        )
        _insert_snapshot(
            connection,
            snapshot_id="snapshot-a",
            account_id="account-a",
            knowledge_base_id="base-account-a",
            positioning_profile_id="profile-a",
        )
        connection.commit()

        statements = (
            (
                "UPDATE execution_bindings SET account_id = 'account-b' "
                "WHERE id = 'binding-account-a'",
                "EXECUTION_BINDING_ACCOUNT_MISMATCH",
            ),
            (
                "UPDATE execution_bindings SET browser_instance_id = NULL "
                "WHERE id = 'binding-account-a'",
                "EXECUTION_BINDING_ACCOUNT_MISMATCH",
            ),
            (
                "UPDATE device_workspaces SET account_id = 'account-b' "
                "WHERE id = 'workspace-account-a'",
                "DEVICE_WORKSPACE_ACCOUNT_MISMATCH",
            ),
            (
                "UPDATE browser_instances SET account_id = 'account-b' "
                "WHERE id = 'browser-account-a'",
                "BROWSER_INSTANCE_ACCOUNT_MISMATCH",
            ),
            (
                "UPDATE account_connections SET account_id = 'account-b' "
                "WHERE id = 'connection-account-a'",
                "ACCOUNT_CONNECTION_BINDING_MISMATCH",
            ),
            (
                "UPDATE knowledge_snapshots SET account_id = 'account-b' "
                "WHERE id = 'snapshot-a'",
                "KNOWLEDGE_SNAPSHOT_ACCOUNT_MISMATCH",
            ),
            (
                "UPDATE account_knowledge_bases SET account_id = 'account-b' "
                "WHERE id = 'base-account-a'",
                "KNOWLEDGE_BASE_ACCOUNT_MISMATCH",
            ),
            (
                "UPDATE positioning_profiles SET account_id = 'account-b' "
                "WHERE id = 'profile-a'",
                "POSITIONING_PROFILE_ACCOUNT_MISMATCH",
            ),
        )
        for statement, error_code in statements:
            with pytest.raises(sqlite3.IntegrityError, match=error_code):
                connection.execute(statement)

        with pytest.raises(
            sqlite3.IntegrityError,
            match="BROWSER_INSTANCE_ACCOUNT_MISMATCH",
        ):
            connection.execute(
                """
                INSERT INTO browser_instances (
                    id, workspace_id, name, profile_path, status,
                    created_at, updated_at, account_id
                ) VALUES ('browser-cross', 'workspace-account-a', '跨账号浏览器',
                          'C:/profile-cross', 'stopped',
                          '2026-01-01', '2026-01-01', 'account-b')
                """
            )


def test_0019_rejects_invalid_existing_scope_before_schema_changes(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "p0c-invalid-scope.db"
    config = _config(database_path)
    command.upgrade(config, REVISION_0018)
    with sqlite3.connect(database_path) as connection:
        _insert_account(connection, "account-a", status="unbound")
        _insert_account(connection, "account-b", status="unbound")
        _insert_workspace_and_browser(connection, "account-a")
        _insert_binding(
            connection,
            binding_id="binding-cross",
            account_id="account-b",
            workspace_id="workspace-account-a",
            browser_id="browser-account-a",
        )
        connection.commit()

    with pytest.raises(RuntimeError, match="执行绑定与设备或浏览器账号不一致"):
        command.upgrade(config, REVISION_0019)

    assert _version(database_path) == REVISION_0018
    assert "runtime_mutation_idempotency" not in _tables(database_path)
    assert "label" not in _columns(database_path, "knowledge_snapshots")
    assert "source_mode" not in _columns(database_path, "knowledge_sources")


@pytest.mark.parametrize(
    "blocker",
    ["mutation", "label", "account", "source"],
)
def test_0019_downgrade_fails_closed_for_new_semantics(
    blocker: str,
    tmp_path: Path,
) -> None:
    database_path = tmp_path / f"p0c-downgrade-{blocker}.db"
    config = _config(database_path)
    command.upgrade(config, REVISION_0019)
    with sqlite3.connect(database_path) as connection:
        if blocker == "mutation":
            _insert_mutation(
                connection,
                record_id="mutation-1",
                scope="system",
                account_id=None,
            )
        else:
            _insert_account(connection, "account-a", status="draft")
            if blocker in {"label", "source"}:
                _insert_knowledge_base(connection, "account-a")
            if blocker == "label":
                _insert_snapshot(
                    connection,
                    snapshot_id="snapshot-1",
                    account_id="account-a",
                    knowledge_base_id="base-account-a",
                    label="基线快照",
                )
            if blocker == "source":
                _insert_head_source(
                    connection,
                    source_id="source-1",
                    account_id="account-a",
                    source_mode="text",
                    source_url=None,
                )
        connection.commit()

    expected = {
        "mutation": "runtime_mutation_idempotency",
        "label": "knowledge_snapshots.label",
        "account": "accounts.status",
        "source": "knowledge_sources.source_mode",
    }[blocker]
    with pytest.raises(RuntimeError, match=expected):
        command.downgrade(config, REVISION_0018)

    assert _version(database_path) == REVISION_0019
    assert "runtime_mutation_idempotency" in _tables(database_path)


def test_empty_0019_schema_downgrades_to_complete_0018_contract(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "p0c-empty-round-trip.db"
    config = _config(database_path)
    command.upgrade(config, REVISION_0019)
    account_table_sql = _rows(
        database_path,
        """
        SELECT sql FROM sqlite_master
        WHERE type = 'table' AND name = 'accounts'
        """,
    )[0][0]
    assert "ck_accounts_stable_id" in str(account_table_sql)

    command.downgrade(config, REVISION_0018)

    assert _version(database_path) == REVISION_0018
    assert "runtime_mutation_idempotency" not in _tables(database_path)
    assert "label" not in _columns(database_path, "knowledge_snapshots")
    assert "source_mode" not in _columns(database_path, "knowledge_sources")
    account_table_sql = _rows(
        database_path,
        """
        SELECT sql FROM sqlite_master
        WHERE type = 'table' AND name = 'accounts'
        """,
    )[0][0]
    assert "ck_accounts_stable_id" not in str(account_table_sql)
    assert {
        "trg_knowledge_sources_account_base_insert",
        "trg_knowledge_sources_account_base_update",
        "trg_account_knowledge_bases_account_update",
    } == _triggers(database_path)
