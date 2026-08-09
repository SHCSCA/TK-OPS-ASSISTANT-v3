from __future__ import annotations

import logging
import re
import sqlite3
from pathlib import Path

log = logging.getLogger(__name__)

_REVISION_PATTERN = re.compile(r"^[0-9]{4}_[a-z0-9_]{1,96}$")
_SQLITE_ERROR_NAME_PATTERN = re.compile(r"^SQLITE_[A-Z0-9_]{1,64}$")


def build_migration_failure_evidence(
    exc: BaseException,
    *,
    database_path: Path,
    mutation_started: bool,
    automatic_restore_allowed: bool,
) -> dict[str, object]:
    """构造不包含 SQL、路径和数据内容的迁移失败证据。"""

    evidence: dict[str, object] = {
        "errorType": type(exc).__name__,
        "mutationStarted": mutation_started,
        "automaticRestoreAllowed": automatic_restore_allowed,
    }
    current_revision = _read_current_revision(database_path)
    if current_revision is not None:
        evidence["currentRevision"] = current_revision

    original_error = getattr(exc, "orig", None)
    sqlite_error_code = getattr(original_error, "sqlite_errorcode", None)
    if isinstance(sqlite_error_code, int) and not isinstance(
        sqlite_error_code,
        bool,
    ):
        evidence["sqliteErrorCode"] = sqlite_error_code
    sqlite_error_name = getattr(original_error, "sqlite_errorname", None)
    if (
        isinstance(sqlite_error_name, str)
        and _SQLITE_ERROR_NAME_PATTERN.fullmatch(sqlite_error_name)
    ):
        evidence["sqliteErrorName"] = sqlite_error_name
    return evidence


def _read_current_revision(database_path: Path) -> str | None:
    if not database_path.is_file():
        return None
    connection: sqlite3.Connection | None = None
    try:
        connection = sqlite3.connect(
            f"{database_path.resolve().as_uri()}?mode=ro",
            uri=True,
            timeout=1,
        )
        row = connection.execute(
            "SELECT version_num FROM alembic_version LIMIT 1"
        ).fetchone()
    except sqlite3.Error:
        log.warning("迁移失败时无法读取当前 revision", exc_info=True)
        return None
    finally:
        if connection is not None:
            connection.close()

    if (
        row
        and isinstance(row[0], str)
        and _REVISION_PATTERN.fullmatch(row[0])
    ):
        return row[0]
    return None
