"""收紧 P0-B Runtime 任务与事件持久化契约。

Revision ID: 0018_p0_runtime_kernel
Revises: 0017_p0_enforce_and_cutover
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from typing import NamedTuple, NoReturn

from alembic import context, op
import sqlalchemy as sa
from sqlalchemy import Connection

revision = "0018_p0_runtime_kernel"
down_revision = "0017_p0_enforce_and_cutover"
branch_labels = None
depends_on = None

log = logging.getLogger(__name__)

_MIGRATION_EVENT_ID = "migration:0016_p0_backfill"
_LEGACY_MIGRATION_TOPIC = "system.migrations"
_RUNTIME_MIGRATION_TOPIC = "system:migrations"
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")

_STRICT_TASK_SCOPE_CHECK = (
    "(scope = 'system' AND account_id IS NULL) OR "
    "(scope = 'account' AND account_id IS NOT NULL "
    "AND length(trim(account_id)) > 0)"
)
_LEGACY_TASK_SCOPE_CHECK = "scope <> 'account' OR account_id IS NOT NULL"
_TASK_TYPE_CHECK = (
    "length(trim(task_type)) > 0 AND task_type = trim(task_type)"
)
_STRICT_TASK_TERMINAL_CHECK = (
    "(status = 'completed' AND completion_kind IS NOT NULL "
    "AND failure_kind IS NULL AND completed_at IS NOT NULL) "
    "OR (status = 'failed' AND failure_kind IS NOT NULL "
    "AND completion_kind IS NULL AND completed_at IS NOT NULL) "
    "OR (status IN ('queued','running','cancelling') "
    "AND completion_kind IS NULL AND failure_kind IS NULL "
    "AND completed_at IS NULL)"
)
_LEGACY_TASK_TERMINAL_CHECK = (
    "(status = 'completed' AND completion_kind IS NOT NULL "
    "AND failure_kind IS NULL AND completed_at IS NOT NULL) "
    "OR (status = 'failed' AND failure_kind IS NOT NULL "
    "AND completion_kind IS NULL AND completed_at IS NOT NULL) "
    "OR (status IN ('queued','running','cancelling') "
    "AND completion_kind IS NULL AND failure_kind IS NULL)"
)
_IDEMPOTENCY_HASH_CHECK = (
    "length(idempotency_key_hash) = 64 "
    "AND idempotency_key_hash NOT GLOB '*[^0-9a-f]*'"
)
_REQUEST_HASH_CHECK = (
    "length(request_hash) = 64 "
    "AND request_hash NOT GLOB '*[^0-9a-f]*'"
)
_HANDLER_VERSION_CHECK = "handler_version >= 1"
_STRICT_EVENT_SCOPE_CHECK = (
    "(account_id IS NULL AND topic LIKE 'system:%' "
    "AND length(topic) > length('system:')) OR "
    "(account_id IS NOT NULL AND length(trim(account_id)) > 0 "
    "AND substr(topic, 1, length('account:' || account_id || ':')) = "
    "'account:' || account_id || ':' "
    "AND length(topic) > length('account:' || account_id || ':'))"
)
_LEGACY_EVENT_SCOPE_CHECK = (
    "topic NOT LIKE 'account:%' OR (account_id IS NOT NULL AND "
    "substr(topic, 1, length('account:' || account_id || ':')) = "
    "'account:' || account_id || ':')"
)


class _TaskIdentity(NamedTuple):
    task_id: str
    scope: str
    account_id: str | None
    task_type: str
    idempotency_key_hash: str
    request_hash: str
    handler_version: int
    snapshot_json: str


def upgrade() -> None:
    connection = op.get_bind()
    _validate_required_schema(connection)
    task_identities = _read_task_identities(connection)
    _validate_task_identities(task_identities)
    _add_task_identity_columns()
    _backfill_task_identity_columns(connection, task_identities)
    _move_topic_rows(
        connection,
        source_topic=_LEGACY_MIGRATION_TOPIC,
        target_topic=_RUNTIME_MIGRATION_TOPIC,
    )
    _mark_historical_migration_event_published(connection)
    _validate_event_scopes(connection)
    _upgrade_task_contract()
    _upgrade_event_contract()
    _create_idempotency_indexes()
    _validate_foreign_keys(connection)


def downgrade() -> None:
    _preflight_cross_revision_downgrade()
    connection = op.get_bind()
    _drop_idempotency_indexes()
    _downgrade_event_contract()
    _downgrade_task_snapshots(connection)
    _downgrade_task_contract()
    _move_topic_rows(
        connection,
        source_topic=_RUNTIME_MIGRATION_TOPIC,
        target_topic=_LEGACY_MIGRATION_TOPIC,
    )
    _validate_foreign_keys(connection)


def _preflight_cross_revision_downgrade() -> None:
    destination = context.get_revision_argument()
    if destination in {down_revision, (down_revision,)}:
        return

    predecessor = context.script.get_revision(down_revision)
    guard = (
        getattr(predecessor.module, "_refuse_data_bearing_downgrade", None)
        if predecessor is not None
        else None
    )
    if not callable(guard):
        _fail("无法加载 0017 有数据降级保护")

    # SQLite DDL 不支持完整事务回滚，跨过 0017 前必须先完成其有数据检查。
    guard()


def _validate_required_schema(connection: Connection) -> None:
    inspector = sa.inspect(connection)
    required_tables = {"runtime_tasks", "runtime_events"}
    missing_tables = sorted(required_tables - set(inspector.get_table_names()))
    if missing_tables:
        _fail(f"缺少 Runtime 表：{', '.join(missing_tables)}")

    required_columns = {
        "runtime_tasks": {
            "id",
            "scope",
            "account_id",
            "task_type",
            "status",
            "completion_kind",
            "failure_kind",
            "config_snapshot_json",
            "completed_at",
        },
        "runtime_events": {
            "event_id",
            "topic",
            "sequence",
            "event_type",
            "account_id",
            "occurred_at",
            "published_at",
        },
    }
    for table_name, expected in required_columns.items():
        present = {
            str(column["name"]) for column in inspector.get_columns(table_name)
        }
        missing = sorted(expected - present)
        if missing:
            _fail(f"表 {table_name} 缺少字段：{', '.join(missing)}")


def _read_task_identities(connection: Connection) -> list[_TaskIdentity]:
    rows = connection.execute(
        sa.text(
            """
            SELECT
                id,
                scope,
                account_id,
                task_type,
                status,
                completion_kind,
                failure_kind,
                completed_at,
                attempt,
                retry_of_task_id,
                config_snapshot_json
            FROM runtime_tasks
            ORDER BY created_at, id
            """
        )
    ).mappings()
    identities: list[_TaskIdentity] = []
    for row in rows:
        task_id = str(row["id"])
        scope = str(row["scope"])
        account_id = (
            str(row["account_id"]) if row["account_id"] is not None else None
        )
        task_type = str(row["task_type"])
        _validate_task_state(
            task_id=task_id,
            scope=scope,
            account_id=account_id,
            task_type=task_type,
            status=str(row["status"]),
            completion_kind=(
                str(row["completion_kind"])
                if row["completion_kind"] is not None
                else None
            ),
            failure_kind=(
                str(row["failure_kind"])
                if row["failure_kind"] is not None
                else None
            ),
            completed_at=(
                str(row["completed_at"])
                if row["completed_at"] is not None
                else None
            ),
        )
        key_hash, request_hash, handler_version, snapshot_json = _parse_snapshot(
            task_id,
            str(row["config_snapshot_json"]),
            attempt=int(row["attempt"]),
            retry_of_task_id=(
                str(row["retry_of_task_id"])
                if row["retry_of_task_id"] is not None
                else None
            ),
        )
        identities.append(
            _TaskIdentity(
                task_id=task_id,
                scope=scope,
                account_id=account_id,
                task_type=task_type,
                idempotency_key_hash=key_hash,
                request_hash=request_hash,
                handler_version=handler_version,
                snapshot_json=snapshot_json,
            )
        )
    return identities


def _validate_task_state(
    *,
    task_id: str,
    scope: str,
    account_id: str | None,
    task_type: str,
    status: str,
    completion_kind: str | None,
    failure_kind: str | None,
    completed_at: str | None,
) -> None:
    valid_scope = (
        scope == "system" and account_id is None
    ) or (
        scope == "account"
        and account_id is not None
        and bool(account_id.strip())
    )
    if not valid_scope:
        _fail(f"任务 {task_id} 的作用域与账号不一致")
    if not task_type.strip() or task_type != task_type.strip():
        _fail(f"任务 {task_id} 的任务类型不是规范值")

    if status == "completed":
        valid_terminal = (
            completion_kind in {"succeeded", "cancelled"}
            and failure_kind is None
            and completed_at is not None
        )
    elif status == "failed":
        valid_terminal = (
            failure_kind in {"error", "timed_out", "restart_interrupted"}
            and completion_kind is None
            and completed_at is not None
        )
    else:
        valid_terminal = (
            status in {"queued", "running", "cancelling"}
            and completion_kind is None
            and failure_kind is None
            and completed_at is None
        )
    if not valid_terminal:
        _fail(f"任务 {task_id} 的终态字段不一致")


def _parse_snapshot(
    task_id: str,
    serialized: str,
    *,
    attempt: int,
    retry_of_task_id: str | None,
) -> tuple[str, str, int, str]:
    try:
        raw = json.loads(serialized)
    except (TypeError, ValueError) as exc:
        _fail(f"任务 {task_id} 的配置快照无法解析", cause=exc)
    if (
        not isinstance(raw, dict)
        or isinstance(raw.get("schemaVersion"), bool)
        or not isinstance(raw.get("schemaVersion"), int)
        or raw.get("schemaVersion") not in {1, 2}
    ):
        _fail(f"任务 {task_id} 的配置快照版本不受支持")

    schema_version = int(raw["schemaVersion"])
    handler_version = raw.get("handlerVersion")
    payload = raw.get("payload")
    idempotency = raw.get("idempotency")
    if (
        isinstance(handler_version, bool)
        or not isinstance(handler_version, int)
        or handler_version < 1
        or not isinstance(payload, dict)
        or not isinstance(idempotency, dict)
    ):
        _fail(f"任务 {task_id} 的配置快照缺少必要字段")

    key_hash = idempotency.get("keyHash")
    request_hash = idempotency.get("requestHash")
    if (
        not isinstance(key_hash, str)
        or _SHA256_PATTERN.fullmatch(key_hash) is None
        or not isinstance(request_hash, str)
        or _SHA256_PATTERN.fullmatch(request_hash) is None
    ):
        _fail(f"任务 {task_id} 的幂等摘要无效")
    try:
        calculated_request_hash = _sha256_json(payload)
    except (TypeError, ValueError) as exc:
        _fail(f"任务 {task_id} 的请求正文不是规范 JSON", cause=exc)
    if calculated_request_hash != request_hash:
        _fail(f"任务 {task_id} 的请求摘要与快照正文不一致")

    if schema_version == 2:
        command = raw.get("command")
        if not isinstance(command, dict):
            _fail(f"任务 {task_id} 的配置快照缺少创建命令")
        creation_attempt = command.get("creationAttempt")
        stored_retry_of = command.get("retryOfTaskId")
        requested_timeout = command.get("requestedTimeoutSeconds")
        if (
            isinstance(creation_attempt, bool)
            or not isinstance(creation_attempt, int)
            or creation_attempt < 1
            or creation_attempt > attempt
            or stored_retry_of != retry_of_task_id
            or (
                requested_timeout is not None
                and (
                    isinstance(requested_timeout, bool)
                    or not isinstance(requested_timeout, int)
                    or requested_timeout <= 0
                )
            )
        ):
            _fail(f"任务 {task_id} 的创建命令快照无效")
    else:
        raw["schemaVersion"] = 2
        raw["command"] = {
            "creationAttempt": attempt,
            "retryOfTaskId": retry_of_task_id,
            "requestedTimeoutSeconds": None,
        }
    return (
        key_hash,
        request_hash,
        handler_version,
        _canonical_json(raw),
    )


def _validate_task_identities(identities: list[_TaskIdentity]) -> None:
    seen: set[tuple[str, str | None, str, str]] = set()
    for identity in identities:
        key = (
            identity.scope,
            identity.account_id,
            identity.task_type,
            identity.idempotency_key_hash,
        )
        if key in seen:
            _fail("Runtime 任务存在重复作用域幂等键")
        seen.add(key)


def _add_task_identity_columns() -> None:
    op.add_column(
        "runtime_tasks",
        sa.Column("idempotency_key_hash", sa.String(), nullable=True),
    )
    op.add_column(
        "runtime_tasks",
        sa.Column("request_hash", sa.String(), nullable=True),
    )
    op.add_column(
        "runtime_tasks",
        sa.Column("handler_version", sa.Integer(), nullable=True),
    )


def _backfill_task_identity_columns(
    connection: Connection,
    identities: list[_TaskIdentity],
) -> None:
    statement = sa.text(
        """
        UPDATE runtime_tasks
        SET config_snapshot_json = :config_snapshot_json,
            idempotency_key_hash = :idempotency_key_hash,
            request_hash = :request_hash,
            handler_version = :handler_version
        WHERE id = :task_id
        """
    )
    for identity in identities:
        connection.execute(
            statement,
            {
                "task_id": identity.task_id,
                "config_snapshot_json": identity.snapshot_json,
                "idempotency_key_hash": identity.idempotency_key_hash,
                "request_hash": identity.request_hash,
                "handler_version": identity.handler_version,
            },
        )
    missing_count = int(
        connection.execute(
            sa.text(
                """
                SELECT COUNT(*)
                FROM runtime_tasks
                WHERE idempotency_key_hash IS NULL
                   OR request_hash IS NULL
                   OR handler_version IS NULL
                """
            )
        ).scalar_one()
    )
    if missing_count:
        _fail(f"有 {missing_count} 条 Runtime 任务未完成摘要回填")


def _downgrade_task_snapshots(connection: Connection) -> None:
    identities = _read_task_identities(connection)
    statement = sa.text(
        """
        UPDATE runtime_tasks
        SET config_snapshot_json = :config_snapshot_json
        WHERE id = :task_id
        """
    )
    for identity in identities:
        raw = json.loads(identity.snapshot_json)
        raw["schemaVersion"] = 1
        raw.pop("command", None)
        connection.execute(
            statement,
            {
                "task_id": identity.task_id,
                "config_snapshot_json": _canonical_json(raw),
            },
        )


def _upgrade_task_contract() -> None:
    with op.batch_alter_table("runtime_tasks", recreate="always") as batch:
        batch.alter_column(
            "idempotency_key_hash",
            existing_type=sa.String(),
            nullable=False,
        )
        batch.alter_column(
            "request_hash",
            existing_type=sa.String(),
            nullable=False,
        )
        batch.alter_column(
            "handler_version",
            existing_type=sa.Integer(),
            nullable=False,
        )
        batch.drop_constraint(
            "ck_runtime_tasks_account_scope",
            type_="check",
        )
        batch.drop_constraint(
            "ck_runtime_tasks_terminal_kind",
            type_="check",
        )
        batch.create_check_constraint(
            "ck_runtime_tasks_account_scope",
            _STRICT_TASK_SCOPE_CHECK,
        )
        batch.create_check_constraint(
            "ck_runtime_tasks_task_type",
            _TASK_TYPE_CHECK,
        )
        batch.create_check_constraint(
            "ck_runtime_tasks_terminal_kind",
            _STRICT_TASK_TERMINAL_CHECK,
        )
        batch.create_check_constraint(
            "ck_runtime_tasks_idempotency_hash",
            _IDEMPOTENCY_HASH_CHECK,
        )
        batch.create_check_constraint(
            "ck_runtime_tasks_request_hash",
            _REQUEST_HASH_CHECK,
        )
        batch.create_check_constraint(
            "ck_runtime_tasks_handler_version",
            _HANDLER_VERSION_CHECK,
        )


def _downgrade_task_contract() -> None:
    with op.batch_alter_table("runtime_tasks", recreate="always") as batch:
        for constraint_name in (
            "ck_runtime_tasks_task_type",
            "ck_runtime_tasks_idempotency_hash",
            "ck_runtime_tasks_request_hash",
            "ck_runtime_tasks_handler_version",
            "ck_runtime_tasks_account_scope",
            "ck_runtime_tasks_terminal_kind",
        ):
            batch.drop_constraint(constraint_name, type_="check")
        batch.create_check_constraint(
            "ck_runtime_tasks_account_scope",
            _LEGACY_TASK_SCOPE_CHECK,
        )
        batch.create_check_constraint(
            "ck_runtime_tasks_terminal_kind",
            _LEGACY_TASK_TERMINAL_CHECK,
        )
        batch.drop_column("handler_version")
        batch.drop_column("request_hash")
        batch.drop_column("idempotency_key_hash")


def _upgrade_event_contract() -> None:
    with op.batch_alter_table("runtime_events", recreate="always") as batch:
        batch.drop_constraint(
            "ck_runtime_events_account_topic",
            type_="check",
        )
        batch.create_check_constraint(
            "ck_runtime_events_account_topic",
            _STRICT_EVENT_SCOPE_CHECK,
        )


def _downgrade_event_contract() -> None:
    with op.batch_alter_table("runtime_events", recreate="always") as batch:
        batch.drop_constraint(
            "ck_runtime_events_account_topic",
            type_="check",
        )
        batch.create_check_constraint(
            "ck_runtime_events_account_topic",
            _LEGACY_EVENT_SCOPE_CHECK,
        )


def _create_idempotency_indexes() -> None:
    op.create_index(
        "uq_runtime_tasks_system_idempotency",
        "runtime_tasks",
        ["task_type", "idempotency_key_hash"],
        unique=True,
        sqlite_where=sa.text("scope = 'system' AND account_id IS NULL"),
    )
    op.create_index(
        "uq_runtime_tasks_account_idempotency",
        "runtime_tasks",
        ["account_id", "task_type", "idempotency_key_hash"],
        unique=True,
        sqlite_where=sa.text("scope = 'account' AND account_id IS NOT NULL"),
    )


def _drop_idempotency_indexes() -> None:
    op.drop_index(
        "uq_runtime_tasks_account_idempotency",
        table_name="runtime_tasks",
    )
    op.drop_index(
        "uq_runtime_tasks_system_idempotency",
        table_name="runtime_tasks",
    )


def _move_topic_rows(
    connection: Connection,
    *,
    source_topic: str,
    target_topic: str,
) -> None:
    rows = connection.execute(
        sa.text(
            """
            SELECT event_id
            FROM runtime_events
            WHERE topic = :source_topic
            ORDER BY sequence, event_id
            """
        ),
        {"source_topic": source_topic},
    ).mappings().all()
    if not rows:
        return

    next_sequence = int(
        connection.execute(
            sa.text(
                """
                SELECT COALESCE(MAX(sequence), 0) + 1
                FROM runtime_events
                WHERE topic = :target_topic
                """
            ),
            {"target_topic": target_topic},
        ).scalar_one()
    )
    statement = sa.text(
        """
        UPDATE runtime_events
        SET topic = :target_topic,
            sequence = :sequence
        WHERE event_id = :event_id
          AND topic = :source_topic
        """
    )
    for offset, row in enumerate(rows):
        connection.execute(
            statement,
            {
                "target_topic": target_topic,
                "sequence": next_sequence + offset,
                "event_id": str(row["event_id"]),
                "source_topic": source_topic,
            },
        )


def _mark_historical_migration_event_published(connection: Connection) -> None:
    connection.execute(
        sa.text(
            """
            UPDATE runtime_events
            SET published_at = COALESCE(published_at, occurred_at)
            WHERE event_id = :event_id
              AND event_type = 'migration.legacy_backfill_completed'
            """
        ),
        {"event_id": _MIGRATION_EVENT_ID},
    )


def _validate_event_scopes(connection: Connection) -> None:
    rows = connection.execute(
        sa.text(
            """
            SELECT event_id, topic, account_id
            FROM runtime_events
            ORDER BY occurred_at, event_id
            """
        )
    ).mappings()
    for row in rows:
        event_id = str(row["event_id"])
        topic = str(row["topic"])
        account_id = (
            str(row["account_id"]) if row["account_id"] is not None else None
        )
        if account_id is None:
            valid = topic.startswith("system:") and len(topic) > len("system:")
        else:
            prefix = f"account:{account_id}:"
            valid = bool(account_id.strip()) and topic.startswith(prefix) and (
                len(topic) > len(prefix)
            )
        if not valid:
            _fail(f"事件 {event_id} 的 Topic 与账号作用域不一致")


def _validate_foreign_keys(connection: Connection) -> None:
    violations = connection.execute(sa.text("PRAGMA foreign_key_check")).all()
    if violations:
        _fail(f"Runtime 内核迁移后检测到 {len(violations)} 条孤儿外键")


def _sha256_json(value: object) -> str:
    serialized = _canonical_json(value)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _fail(message: str, *, cause: Exception | None = None) -> NoReturn:
    log.error("P0-B Runtime 内核迁移拒绝继续：%s", message)
    error = RuntimeError(f"P0_RUNTIME_KERNEL_MIGRATION_INVALID: {message}")
    if cause is None:
        raise error
    raise error from cause
