from __future__ import annotations

import logging
import os
import shutil
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from persistence.migration.backup_common import (
    DatabaseBackupError,
    _ensure_direct_child,
    _FILE_LAYOUT,
    _sha256,
)
from persistence.migration.types import BackupFileRecord, BackupManifest

log = logging.getLogger("persistence.migration.backup")


@dataclass(frozen=True, slots=True)
class _RollbackFileRecord:
    role: str
    target_path: Path
    staged_path: Path
    present: bool
    size_bytes: int
    sha256: str | None


def restore_database_backup(
    database_path: Path,
    manifest: BackupManifest,
) -> None:
    """先校验恢复单元与恢复前快照，再替换目标数据库。"""

    # 延迟导入避免备份入口与恢复实现形成模块初始化环。
    from persistence.migration.backup import verify_database_backup

    verify_database_backup(manifest)
    target = database_path.resolve()
    backup_root = manifest.backup_dir.resolve()
    if target == backup_root or target.is_relative_to(backup_root):
        log.error("数据库备份恢复失败：目标路径位于备份恢复单元内")
        raise DatabaseBackupError("恢复目标不能位于备份目录内")

    restore_suffix = f".restore-{uuid4().hex}"
    rollback_suffix = f".rollback-{uuid4().hex}"
    target_paths = {
        role: Path(f"{target}{target_suffix}")
        for role, _, target_suffix in _FILE_LAYOUT
    }
    restore_staged_paths = {
        role: Path(f"{target_path}{restore_suffix}")
        for role, target_path in target_paths.items()
    }
    rollback_staged_paths = {
        role: Path(f"{target_path}{rollback_suffix}")
        for role, target_path in target_paths.items()
    }
    rollback_records: dict[str, _RollbackFileRecord] = {}
    target_mutation_started = False
    preserve_rollback_files = False

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        records = {item.role: item for item in manifest.files}
        rollback_records = _stage_rollback_files(
            target_paths,
            rollback_staged_paths,
        )
        for role, _, _ in _FILE_LAYOUT:
            record = records[role]
            if not record.present:
                continue
            source = (backup_root / record.name).resolve()
            staged = restore_staged_paths[role]
            shutil.copy2(source, staged)
            if (
                staged.stat().st_size != record.size_bytes
                or _sha256(staged) != record.sha256
            ):
                raise DatabaseBackupError("恢复暂存文件校验失败，未修改目标数据库")

        _verify_rollback_staging(rollback_records)
        _verify_target_matches_rollback(rollback_records)
        target_mutation_started = True
        for role, _, _ in _FILE_LAYOUT:
            record = records[role]
            target_file = target_paths[role]
            if record.present:
                os.replace(restore_staged_paths[role], target_file)
            elif target_file.exists():
                target_file.unlink()

        _verify_restored_files(target, records)
        log.info("数据库迁移备份已恢复: database_id=%s", manifest.database_id)
    except (DatabaseBackupError, OSError) as exc:
        log.exception("数据库迁移备份恢复失败")
        if target_mutation_started:
            try:
                _restore_rollback_files(rollback_records)
                log.warning(
                    "数据库迁移备份恢复失败，已恢复恢复前状态: database_id=%s",
                    manifest.database_id,
                )
            except (DatabaseBackupError, OSError) as rollback_exc:
                preserve_rollback_files = True
                retained_paths = tuple(
                    item.staged_path.name
                    for item in rollback_records.values()
                    if item.present and item.staged_path.exists()
                )
                log.exception(
                    "数据库迁移备份恢复失败且回滚失败，回滚文件已保留: files=%s",
                    retained_paths,
                )
                raise DatabaseBackupError(
                    "数据库迁移备份恢复失败，且恢复前状态回滚失败；"
                    f"回滚文件已保留在数据库同目录（后缀 {rollback_suffix}），请查看日志"
                ) from rollback_exc
        if isinstance(exc, DatabaseBackupError):
            raise
        raise DatabaseBackupError("数据库迁移备份恢复失败，请查看日志") from exc
    finally:
        _cleanup_staged_files(
            restore_staged_paths.values(),
            error_message="恢复暂存文件清理失败",
        )
        if not preserve_rollback_files:
            _cleanup_staged_files(
                rollback_staged_paths.values(),
                error_message="回滚暂存文件清理失败",
            )


def _stage_rollback_files(
    target_paths: dict[str, Path],
    staged_paths: dict[str, Path],
) -> dict[str, _RollbackFileRecord]:
    records: dict[str, _RollbackFileRecord] = {}
    for role, _, _ in _FILE_LAYOUT:
        target_path = target_paths[role]
        staged_path = staged_paths[role]
        if not target_path.exists():
            records[role] = _RollbackFileRecord(
                role=role,
                target_path=target_path,
                staged_path=staged_path,
                present=False,
                size_bytes=0,
                sha256=None,
            )
            continue
        if not target_path.is_file():
            raise DatabaseBackupError("恢复目标包含非文件条目，无法创建恢复前快照")
        shutil.copy2(target_path, staged_path)
        size_bytes = staged_path.stat().st_size
        sha256 = _sha256(staged_path)
        record = _RollbackFileRecord(
            role=role,
            target_path=target_path,
            staged_path=staged_path,
            present=True,
            size_bytes=size_bytes,
            sha256=sha256,
        )
        records[role] = record
        _verify_single_rollback_staging(record)
        _verify_single_target_matches_rollback(record)
    return records


def _verify_rollback_staging(
    records: dict[str, _RollbackFileRecord],
) -> None:
    if set(records) != {role for role, _, _ in _FILE_LAYOUT}:
        raise DatabaseBackupError("恢复前快照不完整，未修改目标数据库")
    for role, _, _ in _FILE_LAYOUT:
        _verify_single_rollback_staging(records[role])


def _verify_single_rollback_staging(record: _RollbackFileRecord) -> None:
    if not record.present:
        if record.staged_path.exists():
            raise DatabaseBackupError("恢复前快照与文件存在状态不一致")
        return
    if not record.staged_path.is_file():
        raise DatabaseBackupError("恢复前快照文件缺失，未修改目标数据库")
    if record.staged_path.stat().st_size != record.size_bytes:
        raise DatabaseBackupError("恢复前快照文件大小不匹配，未修改目标数据库")
    if _sha256(record.staged_path) != record.sha256:
        raise DatabaseBackupError("恢复前快照文件校验失败，未修改目标数据库")


def _verify_target_matches_rollback(
    records: dict[str, _RollbackFileRecord],
) -> None:
    for role, _, _ in _FILE_LAYOUT:
        _verify_single_target_matches_rollback(records[role])


def _verify_single_target_matches_rollback(record: _RollbackFileRecord) -> None:
    if not record.present:
        if record.target_path.exists():
            raise DatabaseBackupError("恢复目标在快照期间发生变化，未修改目标数据库")
        return
    if not record.target_path.is_file():
        raise DatabaseBackupError("恢复目标在快照期间缺失，未修改目标数据库")
    if record.target_path.stat().st_size != record.size_bytes:
        raise DatabaseBackupError("恢复目标在快照期间大小发生变化，未修改目标数据库")
    if _sha256(record.target_path) != record.sha256:
        raise DatabaseBackupError("恢复目标在快照期间内容发生变化，未修改目标数据库")


def _restore_rollback_files(
    records: dict[str, _RollbackFileRecord],
) -> None:
    _verify_rollback_staging(records)
    apply_suffix = f".rollback-apply-{uuid4().hex}"
    apply_paths = {
        role: Path(f"{record.target_path}{apply_suffix}")
        for role, record in records.items()
    }
    failed_roles: list[str] = []
    try:
        for role, _, _ in _FILE_LAYOUT:
            record = records[role]
            try:
                if _target_matches_rollback(record):
                    continue
                if record.present:
                    apply_path = apply_paths[role]
                    shutil.copy2(record.staged_path, apply_path)
                    if (
                        apply_path.stat().st_size != record.size_bytes
                        or _sha256(apply_path) != record.sha256
                    ):
                        raise DatabaseBackupError("回滚副本校验失败")
                    os.replace(apply_path, record.target_path)
                elif record.target_path.exists():
                    record.target_path.unlink()
            except (DatabaseBackupError, OSError):
                failed_roles.append(role)
                log.exception("数据库恢复前状态回滚失败: role=%s", role)

        try:
            _verify_target_matches_rollback(records)
        except (DatabaseBackupError, OSError):
            log.exception("数据库恢复前状态回滚校验失败")
            if "校验" not in failed_roles:
                failed_roles.append("校验")
        if failed_roles:
            raise DatabaseBackupError(
                f"数据库恢复前状态回滚失败，失败角色：{', '.join(failed_roles)}"
            )
    finally:
        _cleanup_staged_files(
            apply_paths.values(),
            error_message="回滚应用暂存文件清理失败",
        )


def _cleanup_staged_files(
    paths: Iterable[Path],
    *,
    error_message: str,
) -> None:
    for staged_path in paths:
        try:
            staged_path.unlink(missing_ok=True)
        except OSError:
            log.exception("%s: file=%s", error_message, staged_path.name)


def _target_matches_rollback(record: _RollbackFileRecord) -> bool:
    if not record.present:
        return not record.target_path.exists()
    return (
        record.target_path.is_file()
        and record.target_path.stat().st_size == record.size_bytes
        and _sha256(record.target_path) == record.sha256
    )


def _verify_restored_files(
    target: Path,
    records: dict[str, BackupFileRecord],
) -> None:
    for role, _, target_suffix in _FILE_LAYOUT:
        record = records[role]
        target_file = Path(f"{target}{target_suffix}")
        if record.present:
            if target_file.stat().st_size != record.size_bytes:
                raise DatabaseBackupError("恢复后的数据库文件大小不匹配")
            if _sha256(target_file) != record.sha256:
                raise DatabaseBackupError("恢复后的数据库文件校验失败")
        elif target_file.exists():
            raise DatabaseBackupError("恢复后仍存在清单外的 SQLite 边车文件")
