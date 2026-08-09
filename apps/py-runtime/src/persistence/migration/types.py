from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any


class DatabaseSchemaKind(str, Enum):
    """启动迁移前可识别的数据库结构类别。"""

    EMPTY = "empty"
    VERSIONED = "versioned"
    LEGACY_FRESH_RUNTIME = "legacy_fresh_runtime"
    LEGACY_RUNTIME_CURRENT = "legacy_runtime_current"
    LEGACY_SCHEMA_V3 = "legacy_schema_v3"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ColumnSignature:
    name: str
    declared_type: str
    not_null: bool
    default_value: str | None
    primary_key_position: int
    hidden: int

    def to_payload(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "declaredType": self.declared_type,
            "notNull": self.not_null,
            "defaultValue": self.default_value,
            "primaryKeyPosition": self.primary_key_position,
            "hidden": self.hidden,
        }


@dataclass(frozen=True, slots=True)
class ForeignKeySignature:
    identifier: int
    sequence: int
    target_table: str
    source_column: str
    target_column: str | None
    on_update: str
    on_delete: str
    match: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "identifier": self.identifier,
            "sequence": self.sequence,
            "targetTable": self.target_table,
            "sourceColumn": self.source_column,
            "targetColumn": self.target_column,
            "onUpdate": self.on_update,
            "onDelete": self.on_delete,
            "match": self.match,
        }


@dataclass(frozen=True, slots=True)
class IndexColumnSignature:
    sequence: int
    column_id: int
    column_name: str | None
    descending: bool
    collation: str | None

    def to_payload(self) -> dict[str, Any]:
        return {
            "sequence": self.sequence,
            "columnId": self.column_id,
            "columnName": self.column_name,
            "descending": self.descending,
            "collation": self.collation,
        }


@dataclass(frozen=True, slots=True)
class IndexSignature:
    name: str
    unique: bool
    origin: str
    partial: bool
    definition_sql: str | None
    columns: tuple[IndexColumnSignature, ...]

    def to_payload(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "unique": self.unique,
            "origin": self.origin,
            "partial": self.partial,
            "definitionSql": self.definition_sql,
            "columns": [column.to_payload() for column in self.columns],
        }


@dataclass(frozen=True, slots=True)
class TableSignature:
    name: str
    definition_sql: str | None
    columns: tuple[ColumnSignature, ...]
    foreign_keys: tuple[ForeignKeySignature, ...]
    indexes: tuple[IndexSignature, ...]

    def to_payload(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "definitionSql": self.definition_sql,
            "columns": [column.to_payload() for column in self.columns],
            "foreignKeys": [foreign_key.to_payload() for foreign_key in self.foreign_keys],
            "indexes": [index.to_payload() for index in self.indexes],
        }


@dataclass(frozen=True, slots=True)
class SchemaObjectSignature:
    object_type: str
    name: str
    table_name: str
    definition_sql: str | None

    def to_payload(self) -> dict[str, Any]:
        return {
            "objectType": self.object_type,
            "name": self.name,
            "tableName": self.table_name,
            "definitionSql": self.definition_sql,
        }


@dataclass(frozen=True, slots=True)
class SchemaFingerprint:
    sha256: str
    tables: tuple[TableSignature, ...]
    schema_objects: tuple[SchemaObjectSignature, ...]

    @property
    def table_names(self) -> tuple[str, ...]:
        return tuple(table.name for table in self.tables)

    @property
    def table_count(self) -> int:
        return len(self.tables)


@dataclass(frozen=True, slots=True)
class SchemaInspection:
    kind: DatabaseSchemaKind
    fingerprint: str
    revision: str | None
    tables: tuple[TableSignature, ...]
    reason: str

    @property
    def table_count(self) -> int:
        return len(self.tables)

    @property
    def is_supported(self) -> bool:
        return self.kind is not DatabaseSchemaKind.UNKNOWN


DatabaseSchemaClassification = SchemaInspection


@dataclass(frozen=True, slots=True)
class DatabaseIntegrityResult:
    integrity_message: str
    foreign_key_violation_count: int

    @property
    def ok(self) -> bool:
        return self.integrity_message == "ok" and self.foreign_key_violation_count == 0


@dataclass(frozen=True, slots=True)
class BackupFileRecord:
    role: str
    name: str
    present: bool
    size_bytes: int
    sha256: str | None

    def to_payload(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "name": self.name,
            "present": self.present,
            "sizeBytes": self.size_bytes,
            "sha256": self.sha256,
        }


@dataclass(frozen=True, slots=True)
class BackupManifest:
    backup_dir: Path
    database_id: str
    created_at: str
    checkpoint_busy: int
    checkpoint_log_frames: int
    checkpointed_frames: int
    files: tuple[BackupFileRecord, ...]
    format_version: int = 1

    def to_payload(self) -> dict[str, Any]:
        return {
            "formatVersion": self.format_version,
            "databaseId": self.database_id,
            "createdAt": self.created_at,
            "checkpoint": {
                "busy": self.checkpoint_busy,
                "logFrames": self.checkpoint_log_frames,
                "checkpointedFrames": self.checkpointed_frames,
            },
            "files": [item.to_payload() for item in self.files],
        }
