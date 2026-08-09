from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config
import pytest

REVISION_0017 = "0017_p0_enforce_and_cutover"
REVISION_0018 = "0018_p0_runtime_kernel"


def test_0018_backfills_task_identity_and_preserves_event_references(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "runtime-kernel.db"
    config = _config(database_path)
    command.upgrade(config, REVISION_0017)

    snapshot, key_hash, request_hash = _snapshot("idem-runtime")
    with sqlite3.connect(database_path) as connection:
        _insert_account(connection, "account-a")
        _insert_0017_task(
            connection,
            task_id="task-a",
            scope="account",
            account_id="account-a",
            snapshot=snapshot,
        )
        connection.execute(
            """
            INSERT INTO runtime_events (
                event_id, topic, sequence, event_type, account_id, task_id,
                payload_json, occurred_at
            ) VALUES (
                'event-task-a', 'account:account-a:tasks', 1, 'task.queued',
                'account-a', 'task-a', '{}', '2026-01-02'
            )
            """
        )
        connection.execute(
            """
            INSERT INTO runtime_events (
                event_id, topic, sequence, event_type, payload_json, occurred_at
            ) VALUES (
                'migration:0016_p0_backfill', 'system.migrations', 1,
                'migration.legacy_backfill_completed', '{}',
                '2026-01-01T01:00:00Z'
            )
            """
        )
        connection.execute(
            """
            INSERT INTO runtime_events (
                event_id, topic, sequence, event_type, payload_json, occurred_at
            ) VALUES (
                'event-existing-target', 'system:migrations', 1,
                'migration.test', '{}', '2026-01-01T00:00:00Z'
            )
            """
        )
        connection.execute(
            """
            INSERT INTO runtime_events (
                event_id, topic, sequence, event_type, payload_json, occurred_at
            ) VALUES (
                'event-legacy-extra', 'system.migrations', 2,
                'migration.test', '{}', '2026-01-03T00:00:00Z'
            )
            """
        )
        connection.commit()

    command.upgrade(config, REVISION_0018)

    assert _version(database_path) == REVISION_0018
    assert _row(
        database_path,
        """
        SELECT idempotency_key_hash, request_hash, handler_version
        FROM runtime_tasks
        WHERE id = 'task-a'
        """,
    ) == (key_hash, request_hash, 1)
    migrated_snapshot = json.loads(
        str(
            _scalar(
                database_path,
                """
                SELECT config_snapshot_json
                FROM runtime_tasks
                WHERE id = 'task-a'
                """,
            )
        )
    )
    assert migrated_snapshot["schemaVersion"] == 2
    assert migrated_snapshot["command"] == {
        "creationAttempt": 1,
        "retryOfTaskId": None,
        "requestedTimeoutSeconds": None,
    }
    assert _rows(
        database_path,
        """
        SELECT event_id, sequence
        FROM runtime_events
        WHERE topic = 'system:migrations'
        ORDER BY sequence
        """,
    ) == [
        ("event-existing-target", 1),
        ("migration:0016_p0_backfill", 2),
        ("event-legacy-extra", 3),
    ]
    assert _scalar(
        database_path,
        """
        SELECT published_at
        FROM runtime_events
        WHERE event_id = 'migration:0016_p0_backfill'
        """,
    ) not in (None, "")
    assert _scalar(
        database_path,
        "SELECT task_id FROM runtime_events WHERE event_id = 'event-task-a'",
    ) == "task-a"
    assert _foreign_key_violations(database_path) == []
    assert {
        "uq_runtime_tasks_system_idempotency",
        "uq_runtime_tasks_account_idempotency",
    }.issubset(_indexes(database_path, "runtime_tasks"))

    command.downgrade(config, REVISION_0017)

    assert _version(database_path) == REVISION_0017
    downgraded_snapshot = json.loads(
        str(
            _scalar(
                database_path,
                """
                SELECT config_snapshot_json
                FROM runtime_tasks
                WHERE id = 'task-a'
                """,
            )
        )
    )
    assert downgraded_snapshot["schemaVersion"] == 1
    assert "command" not in downgraded_snapshot
    assert {
        "idempotency_key_hash",
        "request_hash",
        "handler_version",
    }.isdisjoint(_columns(database_path, "runtime_tasks"))
    assert _scalar(
        database_path,
        "SELECT task_id FROM runtime_events WHERE event_id = 'event-task-a'",
    ) == "task-a"
    assert _foreign_key_violations(database_path) == []


def test_0018_rejects_invalid_snapshot_before_schema_mutation(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "invalid-snapshot.db"
    config = _config(database_path)
    command.upgrade(config, REVISION_0017)
    snapshot, _, _ = _snapshot("idem-invalid")
    raw = json.loads(snapshot)
    raw["payload"]["resourceRef"] = "asset://changed"

    with sqlite3.connect(database_path) as connection:
        _insert_0017_task(
            connection,
            task_id="task-invalid",
            scope="system",
            account_id=None,
            snapshot=_canonical_json(raw),
        )
        connection.commit()

    with pytest.raises(
        RuntimeError,
        match="P0_RUNTIME_KERNEL_MIGRATION_INVALID",
    ):
        command.upgrade(config, REVISION_0018)

    assert _version(database_path) == REVISION_0017
    assert "idempotency_key_hash" not in _columns(
        database_path,
        "runtime_tasks",
    )


def test_0018_database_constraints_enforce_scope_state_and_idempotency(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "runtime-constraints.db"
    command.upgrade(_config(database_path), REVISION_0018)
    with sqlite3.connect(database_path) as connection:
        _insert_account(connection, "account-a")
        snapshot, key_hash, request_hash = _snapshot(
            "idem-valid",
            schema_version=2,
        )
        _insert_0018_task(
            connection,
            task_id="task-valid",
            scope="system",
            account_id=None,
            snapshot=snapshot,
            key_hash=key_hash,
            request_hash=request_hash,
        )
        connection.commit()

        with pytest.raises(
            sqlite3.IntegrityError,
            match="UNIQUE constraint failed",
        ):
            _insert_0018_task(
                connection,
                task_id="task-duplicate",
                scope="system",
                account_id=None,
                snapshot=snapshot,
                key_hash=key_hash,
                request_hash=request_hash,
            )
        connection.rollback()

        other_snapshot, other_key_hash, other_request_hash = _snapshot(
            "idem-other",
            schema_version=2,
        )
        with pytest.raises(
            sqlite3.IntegrityError,
            match="ck_runtime_tasks_account_scope",
        ):
            _insert_0018_task(
                connection,
                task_id="task-invalid-scope",
                scope="system",
                account_id="account-a",
                snapshot=other_snapshot,
                key_hash=other_key_hash,
                request_hash=other_request_hash,
            )
        connection.rollback()

        with pytest.raises(
            sqlite3.IntegrityError,
            match="ck_runtime_tasks_terminal_kind",
        ):
            _insert_0018_task(
                connection,
                task_id="task-invalid-state",
                scope="account",
                account_id="account-a",
                snapshot=other_snapshot,
                key_hash=other_key_hash,
                request_hash=other_request_hash,
                completed_at="2026-01-02",
            )
        connection.rollback()

        with pytest.raises(
            sqlite3.IntegrityError,
            match="ck_runtime_events_account_topic",
        ):
            connection.execute(
                """
                INSERT INTO runtime_events (
                    event_id, topic, sequence, event_type, account_id,
                    payload_json, occurred_at
                ) VALUES (
                    'event-invalid-system', 'system:tasks', 1, 'test.event',
                    'account-a', '{}', '2026-01-01'
                )
                """
            )


def _insert_account(connection: sqlite3.Connection, account_id: str) -> None:
    connection.execute(
        """
        INSERT INTO accounts (
            id, name, platform, status, created_at, updated_at,
            wizard_completed_at, revision
        ) VALUES (?, ?, 'tiktok', 'active', '2026-01-01', '2026-01-01',
                  '2026-01-01', 1)
        """,
        (account_id, account_id),
    )


def _insert_0017_task(
    connection: sqlite3.Connection,
    *,
    task_id: str,
    scope: str,
    account_id: str | None,
    snapshot: str,
) -> None:
    connection.execute(
        """
        INSERT INTO runtime_tasks (
            id, scope, account_id, task_type, status, progress, cancellable,
            attempt, config_snapshot_json, revision, created_at, updated_at
        ) VALUES (?, ?, ?, 'test.operation', 'queued', 0, 1, 1, ?, 1,
                  '2026-01-01', '2026-01-01')
        """,
        (task_id, scope, account_id, snapshot),
    )


def _insert_0018_task(
    connection: sqlite3.Connection,
    *,
    task_id: str,
    scope: str,
    account_id: str | None,
    snapshot: str,
    key_hash: str,
    request_hash: str,
    completed_at: str | None = None,
) -> None:
    connection.execute(
        """
        INSERT INTO runtime_tasks (
            id, scope, account_id, task_type, status, progress, cancellable,
            attempt, config_snapshot_json, revision, created_at, completed_at,
            updated_at, idempotency_key_hash, request_hash, handler_version
        ) VALUES (?, ?, ?, 'test.operation', 'queued', 0, 1, 1, ?, 1,
                  '2026-01-01', ?, '2026-01-01', ?, ?, 1)
        """,
        (
            task_id,
            scope,
            account_id,
            snapshot,
            completed_at,
            key_hash,
            request_hash,
        ),
    )


def _snapshot(
    idempotency_key: str,
    *,
    schema_version: int = 1,
) -> tuple[str, str, str]:
    payload = {"resourceRef": "asset://owned/input"}
    key_hash = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()
    request_hash = hashlib.sha256(
        _canonical_json(payload).encode("utf-8")
    ).hexdigest()
    envelope = {
        "schemaVersion": schema_version,
        "handlerVersion": 1,
        "requestId": "req-migration",
        "operationId": "op-migration",
        "payload": payload,
        "idempotency": {
            "keyHash": key_hash,
            "requestHash": request_hash,
        },
    }
    if schema_version == 2:
        envelope["command"] = {
            "creationAttempt": 1,
            "retryOfTaskId": None,
            "requestedTimeoutSeconds": None,
        }
    return _canonical_json(envelope), key_hash, request_hash


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _config(database_path: Path) -> Config:
    runtime_root = Path(__file__).resolve().parents[2] / "apps" / "py-runtime"
    config = Config(str(runtime_root / "alembic.ini"))
    config.set_main_option("script_location", str(runtime_root / "alembic"))
    config.attributes["database_url"] = f"sqlite:///{database_path.as_posix()}"
    return config


def _version(database_path: Path) -> str:
    return str(
        _scalar(
            database_path,
            "SELECT version_num FROM alembic_version",
        )
    )


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


def _columns(database_path: Path, table_name: str) -> set[str]:
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(f'PRAGMA table_info("{table_name}")').fetchall()
    return {str(row[1]) for row in rows}


def _indexes(database_path: Path, table_name: str) -> set[str]:
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(f'PRAGMA index_list("{table_name}")').fetchall()
    return {str(row[1]) for row in rows}


def _foreign_key_violations(
    database_path: Path,
) -> list[tuple[object, ...]]:
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute("PRAGMA foreign_key_check").fetchall()
    return [tuple(row) for row in rows]
