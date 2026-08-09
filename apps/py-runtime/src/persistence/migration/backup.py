from __future__ import annotations

import json
import logging
import os
import re
import shutil
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from persistence.migration.backup_common import (
    DatabaseBackupError,
    _ensure_direct_child,
    _FILE_LAYOUT,
    _MANIFEST_NAME,
    _sha256,
)
from persistence.migration.backup_restore import (
    restore_database_backup as _restore_database_backup,
)
from persistence.migration.types import BackupFileRecord, BackupManifest

log = logging.getLogger(__name__)

# 保持异常类型的公开模块路径，避免破坏既有序列化与类型检查。
DatabaseBackupError.__module__ = __name__


def create_database_backup(
    database_path: Path,
    backup_dir: Path,
) -> BackupManifest:
    """完成 WAL checkpoint 后，在受控目录创建完整恢复单元。"""

    source = database_path.resolve()
    root = backup_dir.resolve()
    if not source.is_file():
        log.error("数据库迁移备份创建失败：源数据库不存在")
        raise DatabaseBackupError("数据库文件不存在，无法创建迁移备份")
    if root == source or source.is_relative_to(root):
        log.error("数据库迁移备份创建失败：备份目录越过安全边界")
        raise DatabaseBackupError("备份目录不能覆盖数据库文件或其上级边界")

    destination: Path | None = None
    try:
        root.mkdir(parents=True, exist_ok=True)
        database_id = uuid4().hex[:12]
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        destination = (root / f"{timestamp}-{database_id}").resolve()
        _ensure_direct_child(destination, root)
        destination.mkdir(exist_ok=False)

        checkpoint = _checkpoint_and_copy(source, destination)
        records = _build_file_records(destination)
        manifest = BackupManifest(
            backup_dir=destination,
            database_id=database_id,
            created_at=datetime.now(UTC).isoformat(),
            checkpoint_busy=checkpoint[0],
            checkpoint_log_frames=checkpoint[1],
            checkpointed_frames=checkpoint[2],
            files=records,
        )
        _write_manifest(manifest)
        verify_database_backup(manifest)
        log.info(
            "数据库迁移备份已创建: database_id=%s files=%d",
            database_id,
            sum(1 for item in records if item.present),
        )
        return manifest
    except DatabaseBackupError:
        log.exception("数据库迁移备份创建失败")
        _cleanup_incomplete_backup(destination, root)
        raise
    except (OSError, sqlite3.DatabaseError) as exc:
        log.exception("数据库迁移备份创建失败")
        _cleanup_incomplete_backup(destination, root)
        raise DatabaseBackupError("数据库迁移备份创建失败，请查看日志") from exc


def verify_database_backup(manifest: BackupManifest) -> None:
    """校验 manifest 及数据库、WAL、SHM 的存在性、大小与 SHA-256。"""

    try:
        backup_root = manifest.backup_dir.resolve()
        if manifest.format_version != 1:
            raise DatabaseBackupError("数据库备份清单版本不受支持，已拒绝恢复")
        if re.fullmatch(r"[0-9a-f]{12}", manifest.database_id) is None:
            raise DatabaseBackupError("数据库备份标识无效，已拒绝恢复")
        try:
            created_at = datetime.fromisoformat(manifest.created_at)
        except ValueError as exc:
            raise DatabaseBackupError("数据库备份时间无效，已拒绝恢复") from exc
        if created_at.tzinfo is None or manifest.checkpoint_busy != 0:
            raise DatabaseBackupError("数据库备份 checkpoint 状态无效，已拒绝恢复")
        expected_names = {role: name for role, name, _ in _FILE_LAYOUT}
        if (
            len(manifest.files) != len(expected_names)
            or {item.role for item in manifest.files} != set(expected_names)
        ):
            raise DatabaseBackupError("备份清单文件角色不完整，已拒绝恢复")
        database_record = next(
            item for item in manifest.files if item.role == "database"
        )
        if not database_record.present or database_record.size_bytes <= 0:
            raise DatabaseBackupError("数据库备份主文件缺失或为空，已拒绝恢复")
        allowed_entries = {_MANIFEST_NAME}
        for record in manifest.files:
            if record.name != expected_names[record.role]:
                raise DatabaseBackupError("备份清单文件名不受支持，已拒绝恢复")
            if record.present and (
                record.size_bytes < 0
                or record.sha256 is None
                or re.fullmatch(r"[0-9a-f]{64}", record.sha256) is None
            ):
                raise DatabaseBackupError("备份清单校验信息不完整，已拒绝恢复")
            if not record.present and (record.size_bytes != 0 or record.sha256 is not None):
                raise DatabaseBackupError("备份清单缺失文件记录无效，已拒绝恢复")
            file_path = (backup_root / record.name).resolve()
            _ensure_direct_child(file_path, backup_root)
            if record.present:
                allowed_entries.add(record.name)
                if not file_path.is_file():
                    raise DatabaseBackupError("备份文件缺失，已拒绝恢复")
                if file_path.stat().st_size != record.size_bytes:
                    raise DatabaseBackupError("备份文件大小不匹配，已拒绝恢复")
                if _sha256(file_path) != record.sha256:
                    raise DatabaseBackupError("备份文件校验失败，已拒绝恢复")
            elif file_path.exists():
                raise DatabaseBackupError("备份清单与实际文件不一致，已拒绝恢复")
        actual_entries = {entry.name for entry in backup_root.iterdir()}
        if actual_entries != allowed_entries:
            raise DatabaseBackupError("备份目录包含清单外文件，已拒绝恢复或自动清理")
    except DatabaseBackupError:
        log.exception("数据库迁移备份校验未通过")
        raise
    except OSError as exc:
        log.exception("数据库迁移备份校验失败")
        raise DatabaseBackupError("数据库迁移备份校验失败，请查看日志") from exc


def restore_database_backup(
    database_path: Path,
    manifest: BackupManifest,
) -> None:
    """先校验恢复单元与恢复前快照，再替换目标数据库。"""

    _restore_database_backup(database_path, manifest)


def load_backup_manifest(backup_dir: Path) -> BackupManifest:
    """从受控备份目录读取并解析清单。"""

    directory = backup_dir.resolve()
    try:
        payload = json.loads((directory / _MANIFEST_NAME).read_text(encoding="utf-8"))
        checkpoint = payload["checkpoint"]
        files = tuple(
            BackupFileRecord(
                role=str(item["role"]),
                name=str(item["name"]),
                present=bool(item["present"]),
                size_bytes=int(item["sizeBytes"]),
                sha256=str(item["sha256"]) if item["sha256"] is not None else None,
            )
            for item in payload["files"]
        )
        manifest = BackupManifest(
            backup_dir=directory,
            database_id=str(payload["databaseId"]),
            created_at=str(payload["createdAt"]),
            checkpoint_busy=int(checkpoint["busy"]),
            checkpoint_log_frames=int(checkpoint["logFrames"]),
            checkpointed_frames=int(checkpoint["checkpointedFrames"]),
            files=files,
            format_version=int(payload["formatVersion"]),
        )
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        log.exception("数据库备份清单读取失败")
        raise DatabaseBackupError("数据库备份清单无效，已拒绝恢复") from exc
    if manifest.format_version != 1:
        log.error("数据库备份清单版本不受支持: version=%s", manifest.format_version)
        raise DatabaseBackupError("数据库备份清单版本不受支持，已拒绝恢复")
    verify_database_backup(manifest)
    return manifest


def prune_database_backups(
    root: Path,
    retain_count: int,
    keep_database_ids: tuple[str, ...] = (),
) -> tuple[str, ...]:
    """仅清理受控根目录中通过完整校验的旧备份恢复单元。"""

    if retain_count < 1:
        log.error("数据库备份保留份数无效: retain_count=%s", retain_count)
        raise DatabaseBackupError("数据库备份保留份数必须至少为 1")

    resolved_root = root.resolve()
    if not resolved_root.exists():
        return ()
    if not resolved_root.is_dir():
        log.warning("数据库备份清理已跳过：备份根路径不是目录")
        return ()

    protected_ids = set(keep_database_ids)
    candidates: list[BackupManifest] = []
    try:
        children = tuple(resolved_root.iterdir())
    except OSError:
        log.exception("数据库备份根目录读取失败，已跳过自动清理")
        return ()

    for child in children:
        try:
            if child.is_symlink() or not child.is_dir():
                log.warning("数据库备份清理已跳过未知条目: entry=%s", child.name)
                continue
            resolved_child = child.resolve()
            _ensure_direct_child(resolved_child, resolved_root)
            candidates.append(load_backup_manifest(resolved_child))
        except (OSError, DatabaseBackupError):
            log.warning(
                "数据库备份清理已跳过无效目录: entry=%s",
                child.name,
                exc_info=True,
            )

    candidates.sort(key=lambda item: item.created_at, reverse=True)
    retained_ids = {item.database_id for item in candidates[:retain_count]}
    retained_ids.update(protected_ids)
    removed_ids: list[str] = []
    for manifest in candidates:
        if manifest.database_id in retained_ids:
            continue
        try:
            directory = manifest.backup_dir.resolve()
            _ensure_direct_child(directory, resolved_root)
            if directory.is_symlink():
                log.warning("数据库备份清理已跳过符号链接: entry=%s", directory.name)
                continue
            shutil.rmtree(directory)
            removed_ids.append(manifest.database_id)
            log.info("旧数据库备份已清理: database_id=%s", manifest.database_id)
        except (OSError, DatabaseBackupError):
            log.warning(
                "旧数据库备份清理失败，已保留恢复单元: database_id=%s",
                manifest.database_id,
                exc_info=True,
            )
    return tuple(removed_ids)


def _checkpoint_and_copy(source: Path, destination: Path) -> tuple[int, int, int]:
    connection = sqlite3.connect(source, timeout=30)
    try:
        connection.execute("PRAGMA busy_timeout = 30000")
        checkpoint_row = connection.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
        checkpoint = tuple(int(value) for value in (checkpoint_row or (0, 0, 0)))
        if checkpoint[0] != 0:
            raise DatabaseBackupError("数据库仍有活动写入，WAL checkpoint 未完成")
    finally:
        connection.close()

    # Windows 会锁定打开连接对应的 SHM 文件；写门和迁移锁由调用方保证此处无新写入。
    for _, backup_name, source_suffix in _FILE_LAYOUT:
        source_file = Path(f"{source}{source_suffix}")
        if source_file.exists():
            shutil.copy2(source_file, destination / backup_name)
    return checkpoint


def _build_file_records(destination: Path) -> tuple[BackupFileRecord, ...]:
    records: list[BackupFileRecord] = []
    for role, backup_name, _ in _FILE_LAYOUT:
        file_path = destination / backup_name
        present = file_path.is_file()
        records.append(
            BackupFileRecord(
                role=role,
                name=backup_name,
                present=present,
                size_bytes=file_path.stat().st_size if present else 0,
                sha256=_sha256(file_path) if present else None,
            )
        )
    return tuple(records)


def _write_manifest(manifest: BackupManifest) -> None:
    manifest_path = manifest.backup_dir / _MANIFEST_NAME
    temporary_path = manifest.backup_dir / f"{_MANIFEST_NAME}.tmp"
    temporary_path.write_text(
        json.dumps(manifest.to_payload(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary_path, manifest_path)


def _cleanup_incomplete_backup(destination: Path | None, root: Path) -> None:
    if destination is None or not destination.exists():
        return
    try:
        _ensure_direct_child(destination.resolve(), root)
        shutil.rmtree(destination)
    except (OSError, DatabaseBackupError):
        log.exception("未完成的数据库备份目录清理失败")
