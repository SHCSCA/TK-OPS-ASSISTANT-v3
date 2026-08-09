from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import replace
from pathlib import Path

import pytest

import persistence.migration.backup as backup_module
from persistence.migration import (
    BackupManifest,
    DatabaseBackupError,
    create_database_backup,
    load_backup_manifest,
    prune_database_backups,
    restore_database_backup,
    verify_database_backup,
)


_DATABASE_UNIT_SUFFIXES = ("", "-wal", "-shm")


def _snapshot_database_unit(database_path: Path) -> dict[str, bytes | None]:
    snapshot: dict[str, bytes | None] = {}
    for suffix in _DATABASE_UNIT_SUFFIXES:
        target = Path(f"{database_path}{suffix}")
        snapshot[suffix] = target.read_bytes() if target.exists() else None
    return snapshot


def _set_backup_sidecars_presence(
    manifest: BackupManifest,
    *,
    present: bool,
) -> BackupManifest:
    updated_files = []
    for record in manifest.files:
        if record.role == "database":
            updated_files.append(record)
            continue
        backup_file = manifest.backup_dir / record.name
        if present and not record.present:
            payload = f"rollback-test-{record.role}".encode()
            backup_file.write_bytes(payload)
            updated_files.append(
                replace(
                    record,
                    present=True,
                    size_bytes=len(payload),
                    sha256=hashlib.sha256(payload).hexdigest(),
                )
            )
        elif not present:
            backup_file.unlink(missing_ok=True)
            updated_files.append(
                replace(record, present=False, size_bytes=0, sha256=None)
            )
        else:
            updated_files.append(record)
    updated_manifest = replace(manifest, files=tuple(updated_files))
    (manifest.backup_dir / "manifest.json").write_text(
        json.dumps(updated_manifest.to_payload(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return updated_manifest


def test_backup_records_checkpointed_database_wal_and_shm(tmp_path: Path) -> None:
    database_path = tmp_path / "runtime.db"
    connection = sqlite3.connect(database_path)
    try:
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("CREATE TABLE records (id INTEGER PRIMARY KEY, value TEXT NOT NULL)")
        connection.execute("INSERT INTO records (value) VALUES ('迁移前内容')")
        connection.commit()
    finally:
        connection.close()

    manifest = create_database_backup(database_path, tmp_path / "backups")

    verify_database_backup(manifest)
    assert manifest.checkpoint_busy == 0
    assert {item.role for item in manifest.files} == {"database", "wal", "shm"}
    assert all(item.sha256 is not None for item in manifest.files if item.present)
    payload = json.loads((manifest.backup_dir / "manifest.json").read_text(encoding="utf-8"))
    serialized = json.dumps(payload, ensure_ascii=False)
    assert str(database_path.resolve()) not in serialized
    assert "迁移前内容" not in serialized


def test_restore_replaces_database_and_removes_unlisted_sidecars(tmp_path: Path) -> None:
    database_path = tmp_path / "runtime.db"
    connection = sqlite3.connect(database_path)
    try:
        connection.execute("CREATE TABLE records (value TEXT NOT NULL)")
        connection.execute("INSERT INTO records (value) VALUES ('迁移前')")
        connection.commit()
    finally:
        connection.close()
    manifest = create_database_backup(database_path, tmp_path / "backups")

    connection = sqlite3.connect(database_path)
    try:
        connection.execute("DELETE FROM records")
        connection.execute("INSERT INTO records (value) VALUES ('迁移后损坏')")
        connection.commit()
    finally:
        connection.close()
    for suffix in ("-wal", "-shm"):
        record = next(item for item in manifest.files if item.role == suffix[1:])
        if not record.present:
            Path(f"{database_path}{suffix}").write_bytes(b"stale-sidecar")

    restore_database_backup(database_path, manifest)

    connection = sqlite3.connect(database_path)
    try:
        values = connection.execute("SELECT value FROM records").fetchall()
    finally:
        connection.close()
    assert values == [("迁移前",)]
    for suffix in ("-wal", "-shm"):
        record = next(item for item in manifest.files if item.role == suffix[1:])
        if not record.present:
            assert not Path(f"{database_path}{suffix}").exists()


def test_tampered_backup_is_rejected_before_target_is_changed(tmp_path: Path) -> None:
    database_path = tmp_path / "runtime.db"
    connection = sqlite3.connect(database_path)
    try:
        connection.execute("CREATE TABLE records (value TEXT NOT NULL)")
        connection.execute("INSERT INTO records (value) VALUES ('原始内容')")
        connection.commit()
    finally:
        connection.close()
    manifest = create_database_backup(database_path, tmp_path / "backups")

    connection = sqlite3.connect(database_path)
    try:
        connection.execute("UPDATE records SET value = '当前目标内容'")
        connection.commit()
    finally:
        connection.close()
    database_record = next(item for item in manifest.files if item.role == "database")
    backup_database = manifest.backup_dir / database_record.name
    backup_database.write_bytes(backup_database.read_bytes() + b"tampered")

    with pytest.raises(DatabaseBackupError, match="大小不匹配|校验失败"):
        restore_database_backup(database_path, manifest)

    connection = sqlite3.connect(database_path)
    try:
        value = connection.execute("SELECT value FROM records").fetchone()[0]
    finally:
        connection.close()
    assert value == "当前目标内容"


def test_manifest_without_database_file_is_rejected_before_target_is_changed(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "runtime.db"
    connection = sqlite3.connect(database_path)
    try:
        connection.execute("CREATE TABLE records (value TEXT NOT NULL)")
        connection.execute("INSERT INTO records (value) VALUES ('备份内容')")
        connection.commit()
    finally:
        connection.close()
    manifest = create_database_backup(database_path, tmp_path / "backups")

    connection = sqlite3.connect(database_path)
    try:
        connection.execute("UPDATE records SET value = '当前目标内容'")
        connection.commit()
    finally:
        connection.close()
    forged_files = tuple(
        replace(record, present=False, size_bytes=0, sha256=None)
        for record in manifest.files
    )
    forged_manifest = replace(manifest, files=forged_files)
    for record in manifest.files:
        (manifest.backup_dir / record.name).unlink(missing_ok=True)
    (manifest.backup_dir / "manifest.json").write_text(
        json.dumps(forged_manifest.to_payload(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(DatabaseBackupError, match="主文件缺失或为空"):
        load_backup_manifest(manifest.backup_dir)
    with pytest.raises(DatabaseBackupError, match="主文件缺失或为空"):
        restore_database_backup(database_path, forged_manifest)

    connection = sqlite3.connect(database_path)
    try:
        value = connection.execute("SELECT value FROM records").fetchone()[0]
    finally:
        connection.close()
    assert value == "当前目标内容"


def test_restore_rolls_back_complete_unit_when_second_replace_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "runtime.db"
    connection = sqlite3.connect(database_path)
    try:
        connection.execute("CREATE TABLE records (value TEXT NOT NULL)")
        connection.execute("INSERT INTO records (value) VALUES ('备份内容')")
        connection.commit()
    finally:
        connection.close()
    manifest = create_database_backup(database_path, tmp_path / "backups")
    manifest = _set_backup_sidecars_presence(manifest, present=True)

    for suffix, payload in zip(
        _DATABASE_UNIT_SUFFIXES,
        (b"current-database", b"current-wal", b"current-shm"),
        strict=True,
    ):
        Path(f"{database_path}{suffix}").write_bytes(payload)
    before_restore = _snapshot_database_unit(database_path)
    real_replace = backup_module.os.replace
    replace_call_count = 0

    def fail_second_replace(source: str | Path, destination: str | Path) -> None:
        nonlocal replace_call_count
        replace_call_count += 1
        if replace_call_count == 2:
            raise OSError("故障注入：第二次替换失败")
        real_replace(source, destination)

    monkeypatch.setattr(backup_module.os, "replace", fail_second_replace)

    with pytest.raises(DatabaseBackupError, match="恢复失败"):
        restore_database_backup(database_path, manifest)

    assert replace_call_count == 3
    assert _snapshot_database_unit(database_path) == before_restore


def test_restore_rolls_back_complete_unit_when_sidecar_delete_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "runtime.db"
    connection = sqlite3.connect(database_path)
    try:
        connection.execute("CREATE TABLE records (value TEXT NOT NULL)")
        connection.execute("INSERT INTO records (value) VALUES ('备份内容')")
        connection.commit()
    finally:
        connection.close()
    manifest = create_database_backup(database_path, tmp_path / "backups")
    manifest = _set_backup_sidecars_presence(manifest, present=False)

    for suffix, payload in zip(
        _DATABASE_UNIT_SUFFIXES,
        (b"current-database", b"current-wal", b"current-shm"),
        strict=True,
    ):
        Path(f"{database_path}{suffix}").write_bytes(payload)
    before_restore = _snapshot_database_unit(database_path)
    failed_sidecar = Path(f"{database_path.resolve()}-wal")
    real_unlink = Path.unlink
    sidecar_failure_injected = False

    def fail_sidecar_unlink(path: Path, missing_ok: bool = False) -> None:
        nonlocal sidecar_failure_injected
        if path == failed_sidecar and not sidecar_failure_injected:
            sidecar_failure_injected = True
            raise OSError("故障注入：边车文件删除失败")
        real_unlink(path, missing_ok=missing_ok)

    monkeypatch.setattr(Path, "unlink", fail_sidecar_unlink)

    with pytest.raises(DatabaseBackupError, match="恢复失败"):
        restore_database_backup(database_path, manifest)

    assert sidecar_failure_injected is True
    assert _snapshot_database_unit(database_path) == before_restore


def test_restore_preserves_rollback_staging_when_rollback_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "runtime.db"
    connection = sqlite3.connect(database_path)
    try:
        connection.execute("CREATE TABLE records (value TEXT NOT NULL)")
        connection.execute("INSERT INTO records (value) VALUES ('备份内容')")
        connection.commit()
    finally:
        connection.close()
    manifest = create_database_backup(database_path, tmp_path / "backups")
    manifest = _set_backup_sidecars_presence(manifest, present=True)

    original_payloads = (b"current-database", b"current-wal", b"current-shm")
    for suffix, payload in zip(
        _DATABASE_UNIT_SUFFIXES,
        original_payloads,
        strict=True,
    ):
        Path(f"{database_path}{suffix}").write_bytes(payload)
    target_database = database_path.resolve()
    target_wal = Path(f"{target_database}-wal")
    real_replace = backup_module.os.replace

    def fail_restore_and_rollback_replace(
        source: str | Path,
        destination: str | Path,
    ) -> None:
        resolved_destination = Path(destination)
        if resolved_destination == target_wal:
            raise OSError("故障注入：恢复替换失败")
        if ".rollback-apply-" in str(source) and resolved_destination == target_database:
            raise OSError("故障注入：回滚替换失败")
        real_replace(source, destination)

    monkeypatch.setattr(
        backup_module.os,
        "replace",
        fail_restore_and_rollback_replace,
    )

    with pytest.raises(DatabaseBackupError, match="回滚失败.*回滚文件已保留"):
        restore_database_backup(database_path, manifest)

    rollback_files = tuple(tmp_path.glob("runtime.db*.rollback-*"))
    assert len(rollback_files) == 3
    assert {item.read_bytes() for item in rollback_files} == set(original_payloads)


def test_backup_directory_cannot_enclose_source_database(tmp_path: Path) -> None:
    backup_root = tmp_path / "backups"
    backup_root.mkdir()
    database_path = backup_root / "runtime.db"
    connection = sqlite3.connect(database_path)
    try:
        connection.execute("CREATE TABLE records (id INTEGER PRIMARY KEY)")
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(DatabaseBackupError, match="备份目录"):
        create_database_backup(database_path, backup_root)


def test_prune_removes_only_valid_old_direct_children(tmp_path: Path) -> None:
    database_path = tmp_path / "runtime.db"
    connection = sqlite3.connect(database_path)
    try:
        connection.execute("CREATE TABLE records (id INTEGER PRIMARY KEY)")
        connection.commit()
    finally:
        connection.close()
    backup_root = tmp_path / "backups"
    first = create_database_backup(database_path, backup_root)
    second = create_database_backup(database_path, backup_root)
    third = create_database_backup(database_path, backup_root)
    unknown_dir = backup_root / "manual-notes"
    unknown_dir.mkdir()
    (unknown_dir / "readme.txt").write_text("不可删除", encoding="utf-8")

    removed_ids = prune_database_backups(
        backup_root,
        retain_count=1,
        keep_database_ids=(first.database_id,),
    )

    assert removed_ids == (second.database_id,)
    assert first.backup_dir.is_dir()
    assert not second.backup_dir.exists()
    assert third.backup_dir.is_dir()
    assert unknown_dir.is_dir()


def test_prune_rejects_zero_retention(tmp_path: Path) -> None:
    with pytest.raises(DatabaseBackupError, match="至少为 1"):
        prune_database_backups(tmp_path / "backups", retain_count=0)


def test_prune_keeps_backup_directory_with_unlisted_file(tmp_path: Path) -> None:
    database_path = tmp_path / "runtime.db"
    connection = sqlite3.connect(database_path)
    try:
        connection.execute("CREATE TABLE records (id INTEGER PRIMARY KEY)")
        connection.commit()
    finally:
        connection.close()
    backup_root = tmp_path / "backups"
    suspicious = create_database_backup(database_path, backup_root)
    newest = create_database_backup(database_path, backup_root)
    (suspicious.backup_dir / "manual.txt").write_text("保留", encoding="utf-8")

    removed_ids = prune_database_backups(backup_root, retain_count=1)

    assert removed_ids == ()
    assert suspicious.backup_dir.is_dir()
    assert newest.backup_dir.is_dir()
