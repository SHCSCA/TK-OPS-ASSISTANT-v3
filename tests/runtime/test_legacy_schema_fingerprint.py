from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

import pytest

from domain.models import Base
from persistence.engine import create_runtime_engine, initialize_domain_schema
from persistence.migration import (
    DatabaseSchemaKind,
    fingerprint_database,
    inspect_database_schema,
    validate_database_integrity,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEVELOPMENT_DATABASE = REPO_ROOT / ".runtime-data" / "runtime.db"


def test_missing_database_is_empty_without_creating_file(tmp_path: Path) -> None:
    database_path = tmp_path / "missing.db"

    inspection = inspect_database_schema(database_path)

    assert inspection.kind is DatabaseSchemaKind.EMPTY
    assert inspection.revision is None
    assert inspection.table_count == 0
    assert not database_path.exists()


def test_valid_alembic_database_is_versioned(tmp_path: Path) -> None:
    database_path = tmp_path / "versioned.db"
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"
        )
        connection.execute(
            "INSERT INTO alembic_version (version_num) VALUES ('0014_magic_cut_suggestion_drafts')"
        )

    inspection = inspect_database_schema(database_path)

    assert inspection.kind is DatabaseSchemaKind.VERSIONED
    assert inspection.revision == "0014_magic_cut_suggestion_drafts"


def test_malformed_alembic_database_is_unknown_and_unchanged(tmp_path: Path) -> None:
    database_path = tmp_path / "malformed-version.db"
    with sqlite3.connect(database_path) as connection:
        connection.execute("CREATE TABLE alembic_version (revision TEXT)")
    before = _sha256(database_path)

    inspection = inspect_database_schema(database_path)

    assert inspection.kind is DatabaseSchemaKind.UNKNOWN
    assert _sha256(database_path) == before


def test_frozen_schema_v3_development_database_is_recognized(tmp_path: Path) -> None:
    source = _require_development_database()
    database_path = tmp_path / "legacy-v3.db"
    _sqlite_backup(source, database_path)

    inspection = inspect_database_schema(database_path)

    assert inspection.kind is DatabaseSchemaKind.LEGACY_SCHEMA_V3
    assert inspection.revision == "3"
    assert inspection.table_count == 39
    assert len(inspection.fingerprint) == 64
    assert validate_database_integrity(database_path).ok


def test_frozen_runtime_current_database_without_schema_meta_is_recognized(
    tmp_path: Path,
) -> None:
    source = _require_development_database()
    database_path = tmp_path / "legacy-runtime-current.db"
    _sqlite_backup(source, database_path)
    with sqlite3.connect(database_path) as connection:
        connection.execute("DROP TABLE schema_meta")

    inspection = inspect_database_schema(database_path)

    assert inspection.kind is DatabaseSchemaKind.LEGACY_RUNTIME_CURRENT
    assert inspection.revision is None
    assert inspection.table_count == 38


def test_wrong_schema_meta_revision_is_unknown_and_inspection_is_read_only(
    tmp_path: Path,
) -> None:
    source = _require_development_database()
    database_path = tmp_path / "unknown-v4.db"
    _sqlite_backup(source, database_path)
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "UPDATE schema_meta SET value = '4' WHERE key = 'schema_version'"
        )
    before = _sha256(database_path)

    inspection = inspect_database_schema(database_path)

    assert inspection.kind is DatabaseSchemaKind.UNKNOWN
    assert inspection.revision == "4"
    assert _sha256(database_path) == before


def test_legacy_factory_fresh_runtime_schema_is_recognized(tmp_path: Path) -> None:
    database_path = tmp_path / "fresh-runtime.db"
    engine = create_runtime_engine(database_path)
    try:
        initialize_domain_schema(engine)
    finally:
        engine.dispose()

    inspection = inspect_database_schema(database_path)

    assert inspection.kind is DatabaseSchemaKind.LEGACY_FRESH_RUNTIME
    assert inspection.revision is None
    assert inspection.table_count == 38
    assert inspection.fingerprint == (
        "f65a60e68cf17e30fde645d37146299b21415946da991882668dec0485c846dd"
    )


def test_fresh_runtime_schema_with_single_column_drift_fails_closed(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "fresh-runtime-drift.db"
    engine = create_runtime_engine(database_path)
    try:
        initialize_domain_schema(engine)
    finally:
        engine.dispose()
    with sqlite3.connect(database_path) as connection:
        connection.execute("ALTER TABLE accounts ADD COLUMN unexpected_note TEXT")
    before = _sha256(database_path)

    inspection = inspect_database_schema(database_path)

    assert inspection.kind is DatabaseSchemaKind.UNKNOWN
    assert inspection.table_count == 38
    assert _sha256(database_path) == before


def test_legacy_schema_with_removed_table_check_fails_closed(tmp_path: Path) -> None:
    source = _require_development_database()
    database_path = tmp_path / "legacy-without-singleton-check.db"
    _sqlite_backup(source, database_path)
    with sqlite3.connect(database_path) as connection:
        connection.execute("PRAGMA writable_schema = ON")
        connection.execute(
            """
            UPDATE sqlite_master
            SET sql = REPLACE(sql, ' CHECK (id = 1)', '')
            WHERE type = 'table' AND name = 'system_config'
            """
        )
        connection.execute("PRAGMA writable_schema = RESET")
    before = _sha256(database_path)

    inspection = inspect_database_schema(database_path)

    assert inspection.kind is DatabaseSchemaKind.UNKNOWN
    assert inspection.revision == "3"
    assert _sha256(database_path) == before


def test_legacy_schema_with_unexpected_view_or_trigger_fails_closed(
    tmp_path: Path,
) -> None:
    source = _require_development_database()
    database_path = tmp_path / "legacy-with-extra-schema-objects.db"
    _sqlite_backup(source, database_path)
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "CREATE VIEW unexpected_accounts_view AS SELECT id FROM accounts"
        )
        connection.execute(
            """
            CREATE TRIGGER unexpected_accounts_trigger
            AFTER UPDATE ON accounts
            BEGIN
                SELECT 1;
            END
            """
        )
    before = _sha256(database_path)

    inspection = inspect_database_schema(database_path)

    assert inspection.kind is DatabaseSchemaKind.UNKNOWN
    assert _sha256(database_path) == before


def test_plain_orm_schema_with_schema_meta_v3_is_still_unknown(tmp_path: Path) -> None:
    database_path = tmp_path / "mixed-legacy.db"
    engine = create_runtime_engine(database_path)
    try:
        Base.metadata.create_all(engine)
    finally:
        engine.dispose()
    with sqlite3.connect(database_path) as connection:
        connection.execute("CREATE TABLE schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        connection.execute(
            "INSERT INTO schema_meta (key, value) VALUES ('schema_version', '3')"
        )

    inspection = inspect_database_schema(database_path)

    assert inspection.kind is DatabaseSchemaKind.UNKNOWN
    assert inspection.revision == "3"


def test_partial_frozen_schema_is_unknown(tmp_path: Path) -> None:
    source = _require_development_database()
    database_path = tmp_path / "partial-legacy.db"
    _sqlite_backup(source, database_path)
    with sqlite3.connect(database_path) as connection:
        connection.execute("DROP TABLE voice_profiles")
    before = _sha256(database_path)

    inspection = inspect_database_schema(database_path)

    assert inspection.kind is DatabaseSchemaKind.UNKNOWN
    assert inspection.revision == "3"
    assert _sha256(database_path) == before


@pytest.mark.parametrize(
    "variant_sql",
    [
        "CREATE TABLE child (id TEXT PRIMARY KEY, parent_id TEXT NOT NULL)",
        "CREATE TABLE child (id TEXT PRIMARY KEY, parent_id INTEGER)",
        (
            "CREATE TABLE child (id TEXT PRIMARY KEY, parent_id TEXT, "
            "FOREIGN KEY(parent_id) REFERENCES parent(id) ON DELETE SET NULL)"
        ),
    ],
)
def test_column_and_foreign_key_changes_change_anonymous_fingerprint(
    tmp_path: Path,
    variant_sql: str,
) -> None:
    baseline = tmp_path / "baseline.db"
    variant = tmp_path / "variant.db"
    baseline_sql = (
        "CREATE TABLE child (id TEXT PRIMARY KEY, parent_id TEXT NOT NULL, "
        "FOREIGN KEY(parent_id) REFERENCES parent(id) ON DELETE CASCADE)"
    )
    for database_path, child_sql in ((baseline, baseline_sql), (variant, variant_sql)):
        with sqlite3.connect(database_path) as connection:
            connection.execute("CREATE TABLE parent (id TEXT PRIMARY KEY)")
            connection.execute(child_sql)
            connection.execute("CREATE UNIQUE INDEX ix_child_parent ON child(parent_id)")

    baseline_fingerprint = fingerprint_database(baseline)
    variant_fingerprint = fingerprint_database(variant)

    assert baseline_fingerprint.sha256 != variant_fingerprint.sha256
    assert len(baseline_fingerprint.sha256) == 64
    assert str(tmp_path) not in baseline_fingerprint.sha256


def test_index_change_changes_anonymous_fingerprint(tmp_path: Path) -> None:
    baseline = tmp_path / "indexed.db"
    variant = tmp_path / "non-unique-index.db"
    for database_path, unique in ((baseline, "UNIQUE "), (variant, "")):
        with sqlite3.connect(database_path) as connection:
            connection.execute("CREATE TABLE items (id TEXT PRIMARY KEY, label TEXT)")
            connection.execute(f"CREATE {unique}INDEX ix_items_label ON items(label)")

    assert fingerprint_database(baseline).sha256 != fingerprint_database(variant).sha256


def test_table_check_change_changes_anonymous_fingerprint(tmp_path: Path) -> None:
    baseline = tmp_path / "checked.db"
    variant = tmp_path / "unchecked.db"
    with sqlite3.connect(baseline) as connection:
        connection.execute(
            "CREATE TABLE singleton (id INTEGER PRIMARY KEY CHECK (id = 1))"
        )
    with sqlite3.connect(variant) as connection:
        connection.execute("CREATE TABLE singleton (id INTEGER PRIMARY KEY)")

    assert fingerprint_database(baseline).sha256 != fingerprint_database(variant).sha256


def test_view_and_trigger_change_anonymous_fingerprint(tmp_path: Path) -> None:
    baseline = tmp_path / "plain-schema.db"
    variant = tmp_path / "schema-with-extra-objects.db"
    for database_path in (baseline, variant):
        with sqlite3.connect(database_path) as connection:
            connection.execute("CREATE TABLE items (id TEXT PRIMARY KEY, label TEXT)")
    with sqlite3.connect(variant) as connection:
        connection.execute("CREATE VIEW item_labels AS SELECT label FROM items")
        connection.execute(
            """
            CREATE TRIGGER item_label_guard
            BEFORE UPDATE OF label ON items
            BEGIN
                SELECT 1;
            END
            """
        )

    baseline_fingerprint = fingerprint_database(baseline)
    variant_fingerprint = fingerprint_database(variant)

    assert baseline_fingerprint.sha256 != variant_fingerprint.sha256
    assert baseline_fingerprint.schema_objects == ()
    assert {item.object_type for item in variant_fingerprint.schema_objects} == {
        "trigger",
        "view",
    }


def _require_development_database() -> Path:
    if not DEVELOPMENT_DATABASE.is_file():
        pytest.skip("当前检出未包含冻结开发库，仅跳过本地 cohort 实物核对")
    return DEVELOPMENT_DATABASE


def _sqlite_backup(source: Path, destination: Path) -> None:
    with sqlite3.connect(source) as source_connection:
        with sqlite3.connect(destination) as destination_connection:
            source_connection.backup(destination_connection)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
