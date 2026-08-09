from __future__ import annotations

import hashlib
from pathlib import Path

_MANIFEST_NAME = "manifest.json"
_FILE_LAYOUT = (
    ("database", "database.db", ""),
    ("wal", "database.db-wal", "-wal"),
    ("shm", "database.db-shm", "-shm"),
)


class DatabaseBackupError(RuntimeError):
    """数据库备份单元无法安全创建、校验或恢复。"""


def _sha256(file_path: Path) -> str:
    digest = hashlib.sha256()
    with file_path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _ensure_direct_child(path: Path, parent: Path) -> None:
    if path.parent != parent:
        raise DatabaseBackupError("备份路径越过受控目录边界")
