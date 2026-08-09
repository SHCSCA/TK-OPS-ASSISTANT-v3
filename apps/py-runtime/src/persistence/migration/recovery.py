from __future__ import annotations

import gc
import logging
import traceback
from pathlib import Path

from config.migration import MigrationConfig
from persistence.migration.backup import (
    prune_database_backups,
    restore_database_backup,
)
from persistence.migration.cutover import DurableCutoverJournal
from persistence.migration.fingerprint import (
    inspect_database_schema,
    validate_database_integrity,
)
from persistence.migration.types import BackupManifest

log = logging.getLogger(__name__)


def is_automatic_restore_allowed(
    journal: DurableCutoverJournal,
    *,
    cutover_event_id: str,
    log_id: str,
) -> bool:
    try:
        return journal.automatic_restore_allowed(cutover_event_id)
    except Exception:
        log.exception(
            "无法验证 cutover 自动恢复边界，已禁止自动覆盖数据库: log_id=%s",
            log_id,
        )
        return False


def append_cutover_evidence_safely(
    journal: DurableCutoverJournal,
    *,
    cutover_event_id: str,
    log_id: str,
    stage: str,
    evidence: dict[str, object],
) -> None:
    try:
        journal.append(
            cutover_event_id=cutover_event_id,
            log_id=log_id,
            stage=stage,
            evidence=evidence,
        )
    except Exception:
        log.exception(
            "迁移切换证据追加失败: log_id=%s stage=%s",
            log_id,
            stage,
        )


def release_failed_migration_resources(exc: Exception) -> None:
    """释放失败调用栈残留的 SQLite 连接，避免 Windows 阻止恢复。"""

    if exc.__traceback__ is not None:
        traceback.clear_frames(exc.__traceback__)
    gc.collect()


def restore_pre_write_migration_failure(
    *,
    database_path: Path,
    backup_manifest: BackupManifest | None,
    empty_file_existed: bool,
    log_id: str,
) -> bool:
    try:
        if backup_manifest is not None:
            restore_database_backup(database_path, backup_manifest)
        else:
            _reset_fresh_database(
                database_path,
                recreate_empty=empty_file_existed,
            )
        validate_database_integrity(database_path)
        return True
    except Exception:
        log.exception("迁移失败后的数据库恢复未完成: log_id=%s", log_id)
        return False


def validate_restored_database_fingerprint(
    database_path: Path,
    *,
    expected_fingerprint: str,
    log_id: str,
) -> tuple[bool, str | None]:
    try:
        inspection = inspect_database_schema(database_path)
    except Exception:
        log.exception("恢复后的数据库结构证据读取失败: log_id=%s", log_id)
        return False, None
    return (
        inspection.fingerprint == expected_fingerprint,
        inspection.fingerprint,
    )


def prune_migration_backups_after_success(
    migration_config: MigrationConfig,
    *,
    keep_database_id: str | None,
) -> None:
    try:
        prune_database_backups(
            migration_config.backup_dir,
            migration_config.backup_retention_count,
            keep_database_ids=((keep_database_id,) if keep_database_id else ()),
        )
    except Exception:
        log.exception("数据库迁移已成功，但历史备份保留策略执行失败")


def _reset_fresh_database(
    database_path: Path,
    *,
    recreate_empty: bool,
) -> None:
    for suffix in ("-wal", "-shm", ""):
        Path(f"{database_path}{suffix}").unlink(missing_ok=True)
    if recreate_empty:
        database_path.parent.mkdir(parents=True, exist_ok=True)
        database_path.touch(exist_ok=False)
