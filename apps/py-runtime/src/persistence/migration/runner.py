from __future__ import annotations

import logging
import time
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

from config.database import database_path_to_url
from config.migration import MigrationConfig
from persistence.migration.backup import (
    create_database_backup,
)
from persistence.migration.cutover import DurableCutoverJournal
from persistence.migration.compatibility import (
    P0_MINIMUM_SUPPORTED_SCHEMA_REVISION,
)
from persistence.migration.fingerprint import (
    inspect_database_schema,
    validate_database_integrity,
)
from persistence.migration.failure_evidence import (
    build_migration_failure_evidence,
)
from persistence.migration.lock import MigrationLock
from persistence.migration.recovery import (
    append_cutover_evidence_safely,
    is_automatic_restore_allowed,
    prune_migration_backups_after_success,
    release_failed_migration_resources,
    restore_pre_write_migration_failure,
    validate_restored_database_fingerprint,
)
from persistence.migration.report import MigrationReport
from persistence.migration.target_contract import (
    TargetSchemaContractError,
    validate_target_schema_contract,
)
from persistence.migration.types import (
    BackupManifest,
    DatabaseSchemaKind,
    SchemaInspection,
)

log = logging.getLogger(__name__)

DATABASE_SCHEMA_UNSUPPORTED = "DATABASE_SCHEMA_UNSUPPORTED"
MIGRATION_FAILED = "MIGRATION_FAILED"
LEGACY_BASELINE_REVISION = "0014_magic_cut_suggestion_drafts"


class RuntimeMigrationError(RuntimeError):
    """启动迁移失败，错误可安全映射到生命周期反馈。"""

    def __init__(
        self,
        message: str,
        *,
        error_code: str,
        log_id: str,
        restored: bool = False,
        cutover_event_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.log_id = log_id
        self.restored = restored
        self.cutover_event_id = cutover_event_id


class DatabaseSchemaUnsupportedError(RuntimeMigrationError):
    """数据库结构没有命中受支持版本或冻结 legacy 指纹。"""


def run_startup_migrations(
    database_path: Path,
    migration_config: MigrationConfig,
    *,
    runtime_root: Path | None = None,
) -> MigrationReport:
    """在 Runtime 容器创建前完成识别、备份、升级和恢复。"""

    log_id = f"log_{uuid4().hex}"
    started_at = time.monotonic()
    resolved_database_path = database_path.resolve()
    resolved_runtime_root = (
        runtime_root.resolve()
        if runtime_root is not None
        else Path(__file__).resolve().parents[3]
    )

    try:
        with MigrationLock(
            migration_config.lock_path,
            migration_config.lock_timeout_seconds,
        ):
            return _run_locked_migration(
                database_path=resolved_database_path,
                migration_config=migration_config,
                runtime_root=resolved_runtime_root,
                log_id=log_id,
                started_at=started_at,
            )
    except RuntimeMigrationError:
        raise
    except Exception as exc:
        log.exception("数据库迁移启动边界失败: log_id=%s", log_id)
        raise RuntimeMigrationError(
            "数据库迁移失败，Runtime 已停止启动，请查看日志后重试",
            error_code=MIGRATION_FAILED,
            log_id=log_id,
        ) from exc


def _run_locked_migration(
    *,
    database_path: Path,
    migration_config: MigrationConfig,
    runtime_root: Path,
    log_id: str,
    started_at: float,
) -> MigrationReport:
    backup_manifest: BackupManifest | None = None
    inspection: SchemaInspection | None = None
    target_revision: str | None = None
    mutation_started = False
    empty_file_existed = False
    journal = DurableCutoverJournal(
        migration_config.cutover_journal_path
        or (migration_config.lock_path.parent / "cutover-journal.json")
    )
    cutover = journal.begin(
        log_id=log_id,
        evidence={
            "databasePathRedacted": database_path.name,
            "backupRetention": migration_config.backup_retention_count,
            "backupRetentionSource": migration_config.backup_retention_source,
            "bootstrapProjectionRevision": (
                migration_config.bootstrap_projection_revision
            ),
            "bootstrapProjectionSha256": (
                migration_config.bootstrap_projection_sha256
            ),
            "automaticRestoreAllowed": True,
        },
    )
    cutover_event_id = cutover.cutover_event_id

    try:
        inspection = inspect_database_schema(database_path)
        _require_supported_schema(inspection, log_id=log_id)
        validate_database_integrity(database_path)
        journal.append(
            cutover_event_id=cutover_event_id,
            log_id=log_id,
            stage="pre_migration_validated",
            evidence={
                "schemaKind": inspection.kind.value,
                "revision": inspection.revision,
                "fingerprint": inspection.fingerprint,
                "tableCount": inspection.table_count,
                "integrity": "ok",
            },
        )

        alembic_config = _build_alembic_config(runtime_root, database_path)
        script_directory = ScriptDirectory.from_config(alembic_config)
        target_revision = script_directory.get_current_head()
        if target_revision is None:
            raise RuntimeError("Alembic 没有可用的目标版本")
        _require_known_versioned_revision(
            inspection,
            script_directory=script_directory,
            target_revision=target_revision,
            log_id=log_id,
        )

        needs_upgrade = not (
            inspection.kind is DatabaseSchemaKind.VERSIONED
            and inspection.revision == target_revision
        )
        empty_file_existed = (
            inspection.kind is DatabaseSchemaKind.EMPTY
            and database_path.exists()
            and database_path.stat().st_size == 0
        )
        if needs_upgrade and database_path.is_file() and database_path.stat().st_size > 0:
            backup_manifest = create_database_backup(
                database_path,
                migration_config.backup_dir,
            )
            journal.append(
                cutover_event_id=cutover_event_id,
                log_id=log_id,
                stage="backup_created",
                evidence={
                    "databaseId": backup_manifest.database_id,
                    "formatVersion": backup_manifest.format_version,
                    "fileCount": len(backup_manifest.files),
                },
            )

        if needs_upgrade:
            mutation_started = True
            if inspection.kind in {
                DatabaseSchemaKind.LEGACY_FRESH_RUNTIME,
                DatabaseSchemaKind.LEGACY_RUNTIME_CURRENT,
                DatabaseSchemaKind.LEGACY_SCHEMA_V3,
            }:
                command.stamp(alembic_config, LEGACY_BASELINE_REVISION)
            command.upgrade(alembic_config, target_revision)
            journal.append(
                cutover_event_id=cutover_event_id,
                log_id=log_id,
                stage="migration_applied",
                evidence={
                    "targetRevision": target_revision,
                    "backupDatabaseId": (
                        backup_manifest.database_id
                        if backup_manifest is not None
                        else None
                    ),
                },
            )

        try:
            post_inspection = validate_target_schema_contract(
                database_path,
                target_revision=target_revision,
            )
        except TargetSchemaContractError as exc:
            if mutation_started:
                raise
            log.error(
                "当前数据库未满足目标契约: log_id=%s",
                log_id,
            )
            raise DatabaseSchemaUnsupportedError(
                "数据库结构与当前版本契约不一致，已保留原库并停止启动",
                error_code=DATABASE_SCHEMA_UNSUPPORTED,
                log_id=log_id,
                cutover_event_id=cutover_event_id,
            ) from exc
        journal.append(
            cutover_event_id=cutover_event_id,
            log_id=log_id,
            stage="post_migration_validated",
            evidence={
                "revision": post_inspection.revision,
                "fingerprint": post_inspection.fingerprint,
                "tableCount": post_inspection.table_count,
                "integrity": "ok",
            },
        )
        report = MigrationReport(
            log_id=log_id,
            schema_kind=inspection.kind.value,
            previous_revision=inspection.revision,
            target_revision=target_revision,
            backup_database_id=(
                backup_manifest.database_id if backup_manifest is not None else None
            ),
            duration_ms=round((time.monotonic() - started_at) * 1000),
            table_count=post_inspection.table_count,
            changed=needs_upgrade,
            cutover_event_id=cutover_event_id,
            cutover_journal_path=str(journal.path),
            compatibility_evidence_path=(
                str(migration_config.compatibility_evidence_path)
                if migration_config.compatibility_evidence_path is not None
                else None
            ),
            pre_migration_fingerprint=inspection.fingerprint,
            post_migration_fingerprint=post_inspection.fingerprint,
            schema_read_min_revision=P0_MINIMUM_SUPPORTED_SCHEMA_REVISION,
            schema_read_max_revision=target_revision,
            backup_manifest=backup_manifest,
            pre_migration_empty_file_existed=empty_file_existed,
        )
        journal.append(
            cutover_event_id=cutover_event_id,
            log_id=log_id,
            stage="migration_completed",
            evidence={
                "targetRevision": target_revision,
                "changed": needs_upgrade,
                "postMigrationFingerprint": post_inspection.fingerprint,
                "automaticRestoreAllowed": True,
                "recoveryPolicy": report.recovery_policy,
            },
        )
        log.info(
            "数据库启动迁移已完成",
            extra={
                "category": "migration",
                "request_id": log_id,
                "context": report.to_log_context(),
            },
        )
        prune_migration_backups_after_success(
            migration_config,
            keep_database_id=(
                backup_manifest.database_id if backup_manifest is not None else None
            ),
        )
        return report
    except DatabaseSchemaUnsupportedError as exc:
        exc.cutover_event_id = cutover_event_id
        append_cutover_evidence_safely(
            journal,
            cutover_event_id=cutover_event_id,
            log_id=log_id,
            stage="migration_failed",
            evidence={
                "errorCode": exc.error_code,
                "mutationStarted": mutation_started,
                "automaticRestoreAllowed": not mutation_started,
            },
        )
        raise
    except Exception as exc:
        restored = False
        automatic_restore_allowed = is_automatic_restore_allowed(
            journal,
            cutover_event_id=cutover_event_id,
            log_id=log_id,
        )
        append_cutover_evidence_safely(
            journal,
            cutover_event_id=cutover_event_id,
            log_id=log_id,
            stage="migration_failed",
            evidence=build_migration_failure_evidence(
                exc,
                database_path=database_path,
                mutation_started=mutation_started,
                automatic_restore_allowed=automatic_restore_allowed,
            ),
        )
        if mutation_started:
            release_failed_migration_resources(exc)
            if automatic_restore_allowed:
                append_cutover_evidence_safely(
                    journal,
                    cutover_event_id=cutover_event_id,
                    log_id=log_id,
                    stage="restore_started",
                    evidence={
                        "backupDatabaseId": (
                            backup_manifest.database_id
                            if backup_manifest is not None
                            else None
                        ),
                        "expectedFingerprint": (
                            inspection.fingerprint if inspection else None
                        ),
                    },
                )
                restored = restore_pre_write_migration_failure(
                    database_path=database_path,
                    backup_manifest=backup_manifest,
                    empty_file_existed=empty_file_existed,
                    log_id=log_id,
                )
                actual_fingerprint: str | None = None
                if restored and inspection is not None:
                    restored, actual_fingerprint = (
                        validate_restored_database_fingerprint(
                            database_path,
                            expected_fingerprint=inspection.fingerprint,
                            log_id=log_id,
                        )
                    )
                append_cutover_evidence_safely(
                    journal,
                    cutover_event_id=cutover_event_id,
                    log_id=log_id,
                    stage=("restore_validated" if restored else "restore_failed"),
                    evidence={
                        "expectedFingerprint": (
                            inspection.fingerprint if inspection else None
                        ),
                        "actualFingerprint": (
                            actual_fingerprint
                        ),
                        "integrity": "ok" if restored else "failed",
                    },
                )
            else:
                log.error(
                    "写门已开放，禁止自动覆盖当前数据库: log_id=%s",
                    log_id,
                )
        log.exception(
            "数据库启动迁移失败: log_id=%s restored=%s",
            log_id,
            restored,
            extra={
                "category": "migration",
                "request_id": log_id,
                "context": {
                    "schemaKind": inspection.kind.value if inspection else None,
                    "previousRevision": inspection.revision if inspection else None,
                    "targetRevision": target_revision,
                    "backupDatabaseId": (
                        backup_manifest.database_id if backup_manifest else None
                    ),
                    "durationMs": round((time.monotonic() - started_at) * 1000),
                    "tableCount": inspection.table_count if inspection else None,
                    "restored": restored,
                },
            },
        )
        if restored and backup_manifest is not None:
            message = "数据库迁移失败，已恢复迁移前备份并停止启动"
        elif restored:
            message = "数据库迁移失败，已清理未完成的新库并停止启动"
        else:
            message = "数据库迁移失败，Runtime 已停止启动，请查看日志后重试"
        raise RuntimeMigrationError(
            message,
            error_code=MIGRATION_FAILED,
            log_id=log_id,
            restored=restored,
            cutover_event_id=cutover_event_id,
        ) from exc


def _build_alembic_config(runtime_root: Path, database_path: Path) -> Config:
    config = Config(str(runtime_root / "alembic.ini"))
    config.set_main_option("script_location", str(runtime_root / "alembic"))
    config.attributes["database_url"] = database_path_to_url(database_path)
    return config


def _require_supported_schema(inspection: SchemaInspection, *, log_id: str) -> None:
    if inspection.kind is not DatabaseSchemaKind.UNKNOWN:
        return
    log.error(
        "数据库结构未命中安全基线: log_id=%s fingerprint=%s",
        log_id,
        inspection.fingerprint,
        extra={
            "category": "migration",
            "request_id": log_id,
            "context": {
                "fingerprint": inspection.fingerprint,
                "tableCount": inspection.table_count,
            },
        },
    )
    raise DatabaseSchemaUnsupportedError(
        "数据库结构无法安全识别，已保留原库并停止启动",
        error_code=DATABASE_SCHEMA_UNSUPPORTED,
        log_id=log_id,
    )


def _require_known_versioned_revision(
    inspection: SchemaInspection,
    *,
    script_directory: ScriptDirectory,
    target_revision: str,
    log_id: str,
) -> None:
    if inspection.kind is not DatabaseSchemaKind.VERSIONED:
        return
    revision = inspection.revision
    known_revisions = {
        item.revision
        for item in script_directory.walk_revisions("base", target_revision)
    }
    if revision in known_revisions:
        return
    log.error(
        "数据库 Alembic 版本不受当前 Runtime 支持: log_id=%s revision=%s",
        log_id,
        revision,
    )
    raise DatabaseSchemaUnsupportedError(
        "数据库版本不受当前 Runtime 支持，已保留原库并停止启动",
        error_code=DATABASE_SCHEMA_UNSUPPORTED,
        log_id=log_id,
    )
