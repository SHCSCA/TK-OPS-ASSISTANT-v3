from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
from contextlib import closing
from pathlib import Path
from urllib.parse import quote

from persistence.migration.legacy_baseline import match_known_legacy_schema
from persistence.migration.types import (
    ColumnSignature,
    DatabaseSchemaClassification,
    DatabaseSchemaKind,
    DatabaseIntegrityResult,
    ForeignKeySignature,
    IndexColumnSignature,
    IndexSignature,
    SchemaObjectSignature,
    SchemaFingerprint,
    TableSignature,
)

log = logging.getLogger(__name__)


class SchemaInspectionError(RuntimeError):
    """数据库结构无法以只读方式检查。"""


class DatabaseIntegrityError(RuntimeError):
    """数据库完整性或外键一致性校验失败。"""


def inspect_database_schema(database_path: Path) -> DatabaseSchemaClassification:
    """只读识别空库、Alembic 库、冻结 legacy 库或未知库。"""

    try:
        resolved_path = database_path.resolve()
        if not resolved_path.exists() or resolved_path.stat().st_size == 0:
            fingerprint = _empty_fingerprint()
            return DatabaseSchemaClassification(
                kind=DatabaseSchemaKind.EMPTY,
                fingerprint=fingerprint.sha256,
                revision=None,
                tables=fingerprint.tables,
                reason="数据库为空，可从 Alembic base 初始化",
            )
        with closing(_connect_read_only(resolved_path)) as connection:
            fingerprint = inspect_schema(connection)
            if not fingerprint.tables:
                return DatabaseSchemaClassification(
                    kind=DatabaseSchemaKind.EMPTY,
                    fingerprint=fingerprint.sha256,
                    revision=None,
                    tables=fingerprint.tables,
                    reason="数据库为空，可从 Alembic base 初始化",
                )

            if "alembic_version" in fingerprint.table_names:
                alembic_version = _read_alembic_version(connection)
                if alembic_version is None:
                    return DatabaseSchemaClassification(
                        kind=DatabaseSchemaKind.UNKNOWN,
                        fingerprint=fingerprint.sha256,
                        revision=None,
                        tables=fingerprint.tables,
                        reason="alembic_version 表缺少唯一有效版本，已拒绝写入",
                    )
                return DatabaseSchemaClassification(
                    kind=DatabaseSchemaKind.VERSIONED,
                    fingerprint=fingerprint.sha256,
                    revision=alembic_version,
                    tables=fingerprint.tables,
                    reason="数据库已由 Alembic 管理",
                )

            schema_meta_version = (
                _read_schema_meta_version(connection)
                if "schema_meta" in fingerprint.table_names
                else None
            )
            legacy_kind = match_known_legacy_schema(
                fingerprint,
                schema_meta_version=schema_meta_version,
            )
            if legacy_kind is not None:
                return DatabaseSchemaClassification(
                    kind=legacy_kind,
                    fingerprint=fingerprint.sha256,
                    revision=schema_meta_version,
                    tables=fingerprint.tables,
                    reason="数据库完整命中冻结 legacy 结构，可进入显式迁移桥",
                )

            return DatabaseSchemaClassification(
                kind=DatabaseSchemaKind.UNKNOWN,
                fingerprint=fingerprint.sha256,
                revision=schema_meta_version,
                tables=fingerprint.tables,
                reason="数据库结构未命中冻结基线，已拒绝写入",
            )
    except (OSError, sqlite3.DatabaseError) as exc:
        log.exception("数据库结构只读检查失败")
        raise SchemaInspectionError("数据库结构检查失败，请保留原库并查看日志") from exc


def classify_database_schema(database_path: Path) -> DatabaseSchemaClassification:
    """兼容旧命名，统一转发到稳定检查入口。"""

    return inspect_database_schema(database_path)


def validate_database_integrity(database_path: Path) -> DatabaseIntegrityResult:
    """只读执行 SQLite 完整性与外键检查，不返回业务行。"""

    try:
        resolved_path = database_path.resolve()
        if not resolved_path.exists() or resolved_path.stat().st_size == 0:
            return DatabaseIntegrityResult(
                integrity_message="ok",
                foreign_key_violation_count=0,
            )
        with closing(_connect_read_only(resolved_path)) as connection:
            integrity_rows = connection.execute("PRAGMA integrity_check").fetchall()
            messages = tuple(str(row[0]).strip().lower() for row in integrity_rows)
            integrity_message = "ok" if messages == ("ok",) else "failed"
            foreign_key_violation_count = len(
                connection.execute("PRAGMA foreign_key_check").fetchall()
            )
            result = DatabaseIntegrityResult(
                integrity_message=integrity_message,
                foreign_key_violation_count=foreign_key_violation_count,
            )
            if not result.ok:
                raise DatabaseIntegrityError(
                    "数据库完整性校验失败，已停止迁移并保留原库"
                )
            return result
    except DatabaseIntegrityError:
        log.exception("数据库完整性校验未通过")
        raise
    except (OSError, sqlite3.DatabaseError) as exc:
        log.exception("数据库完整性校验执行失败")
        raise DatabaseIntegrityError("数据库完整性校验无法完成，请查看日志") from exc


def fingerprint_database(database_path: Path) -> SchemaFingerprint:
    """生成不包含业务正文和路径的数据库结构 SHA-256。"""

    try:
        resolved_path = database_path.resolve()
        if not resolved_path.exists() or resolved_path.stat().st_size == 0:
            return _empty_fingerprint()
        with closing(_connect_read_only(resolved_path)) as connection:
            return inspect_schema(connection)
    except (OSError, sqlite3.DatabaseError) as exc:
        log.exception("数据库结构指纹生成失败")
        raise SchemaInspectionError("数据库结构指纹生成失败，请查看日志") from exc


def inspect_schema(connection: sqlite3.Connection) -> SchemaFingerprint:
    """从现有只读连接生成确定性结构指纹。"""

    connection.row_factory = sqlite3.Row
    table_rows = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    ).fetchall()
    tables = tuple(_inspect_table(connection, str(row["name"])) for row in table_rows)
    object_rows = connection.execute(
        """
        SELECT type, name, tbl_name, sql
        FROM sqlite_master
        WHERE type IN ('view', 'trigger')
        ORDER BY type, name
        """
    ).fetchall()
    schema_objects = tuple(
        SchemaObjectSignature(
            object_type=str(row["type"]),
            name=str(row["name"]),
            table_name=str(row["tbl_name"]),
            definition_sql=(
                " ".join(str(row["sql"]).strip().split())
                if row["sql"] is not None
                else None
            ),
        )
        for row in object_rows
    )
    canonical_payload = {
        "formatVersion": 2,
        "schemaObjects": [item.to_payload() for item in schema_objects],
        "tables": [table.to_payload() for table in tables],
    }
    canonical_json = json.dumps(
        canonical_payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return SchemaFingerprint(
        sha256=hashlib.sha256(canonical_json).hexdigest(),
        tables=tables,
        schema_objects=schema_objects,
    )


def _inspect_table(connection: sqlite3.Connection, table_name: str) -> TableSignature:
    quoted_table = _quote_identifier(table_name)
    definition_row = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    definition_sql = None
    if definition_row is not None and definition_row["sql"] is not None:
        definition_sql = " ".join(str(definition_row["sql"]).strip().split())
    column_rows = connection.execute(f"PRAGMA table_xinfo({quoted_table})").fetchall()
    columns = tuple(
        ColumnSignature(
            name=str(row["name"]),
            declared_type=_normalize_declared_type(row["type"]),
            not_null=bool(row["notnull"]),
            default_value=_normalize_default(row["dflt_value"]),
            primary_key_position=int(row["pk"]),
            hidden=int(row["hidden"]),
        )
        for row in sorted(column_rows, key=lambda item: int(item["cid"]))
    )

    foreign_key_rows = connection.execute(
        f"PRAGMA foreign_key_list({quoted_table})"
    ).fetchall()
    foreign_keys = tuple(
        ForeignKeySignature(
            identifier=int(row["id"]),
            sequence=int(row["seq"]),
            target_table=str(row["table"]),
            source_column=str(row["from"]),
            target_column=str(row["to"]) if row["to"] is not None else None,
            on_update=str(row["on_update"]).upper(),
            on_delete=str(row["on_delete"]).upper(),
            match=str(row["match"]).upper(),
        )
        for row in sorted(
            foreign_key_rows,
            key=lambda item: (int(item["id"]), int(item["seq"])),
        )
    )

    index_rows = connection.execute(f"PRAGMA index_list({quoted_table})").fetchall()
    indexes = tuple(
        _inspect_index(connection, row)
        for row in sorted(index_rows, key=lambda item: str(item["name"]))
    )
    return TableSignature(
        name=table_name,
        definition_sql=definition_sql,
        columns=columns,
        foreign_keys=foreign_keys,
        indexes=indexes,
    )


def _inspect_index(
    connection: sqlite3.Connection,
    index_row: sqlite3.Row,
) -> IndexSignature:
    index_name = str(index_row["name"])
    quoted_index = _quote_identifier(index_name)
    column_rows = connection.execute(f"PRAGMA index_xinfo({quoted_index})").fetchall()
    columns = tuple(
        IndexColumnSignature(
            sequence=int(row["seqno"]),
            column_id=int(row["cid"]),
            column_name=str(row["name"]) if row["name"] is not None else None,
            descending=bool(row["desc"]),
            collation=str(row["coll"]) if row["coll"] is not None else None,
        )
        for row in sorted(column_rows, key=lambda item: int(item["seqno"]))
        if bool(row["key"])
    )
    definition_row = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'index' AND name = ?",
        (index_name,),
    ).fetchone()
    definition_sql = None
    if definition_row is not None and definition_row["sql"] is not None:
        definition_sql = " ".join(str(definition_row["sql"]).strip().split())
    return IndexSignature(
        name=index_name,
        unique=bool(index_row["unique"]),
        origin=str(index_row["origin"]),
        partial=bool(index_row["partial"]),
        definition_sql=definition_sql,
        columns=columns,
    )


def _read_schema_meta_version(connection: sqlite3.Connection) -> str | None:
    try:
        rows = connection.execute(
            "SELECT key, value FROM schema_meta ORDER BY key"
        ).fetchall()
    except sqlite3.DatabaseError:
        log.exception("schema_meta 版本读取失败，数据库将按未知结构处理")
        return None
    if len(rows) != 1 or str(rows[0]["key"]) != "schema_version":
        return None
    value = str(rows[0]["value"]).strip()
    return value or None


def _read_alembic_version(connection: sqlite3.Connection) -> str | None:
    try:
        columns = connection.execute("PRAGMA table_info(alembic_version)").fetchall()
        if tuple(str(row["name"]) for row in columns) != ("version_num",):
            return None
        rows = connection.execute("SELECT version_num FROM alembic_version").fetchall()
    except sqlite3.DatabaseError:
        log.exception("Alembic 版本读取失败，数据库将按未知结构处理")
        return None
    if len(rows) != 1:
        return None
    version = str(rows[0]["version_num"]).strip()
    return version or None


def _connect_read_only(database_path: Path) -> sqlite3.Connection:
    encoded_path = quote(database_path.as_posix(), safe="/:")
    return sqlite3.connect(f"file:{encoded_path}?mode=ro", uri=True)


def _quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _normalize_declared_type(value: object) -> str:
    return " ".join(str(value or "").strip().upper().split())


def _normalize_default(value: object) -> str | None:
    if value is None:
        return None
    return str(value).strip()


def _empty_fingerprint() -> SchemaFingerprint:
    canonical_json = b'{"formatVersion":2,"schemaObjects":[],"tables":[]}'
    return SchemaFingerprint(
        sha256=hashlib.sha256(canonical_json).hexdigest(),
        tables=(),
        schema_objects=(),
    )
