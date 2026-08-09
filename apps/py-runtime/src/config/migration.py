from __future__ import annotations

import hashlib
import hmac
import json
import logging
import math
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

log = logging.getLogger(__name__)

MIGRATION_BACKUP_DIR_ENV = "TK_OPS_MIGRATION_BACKUP_DIR"
MIGRATION_BACKUP_RETENTION_ENV = "TK_OPS_MIGRATION_BACKUP_RETENTION"
MIGRATION_LOCK_PATH_ENV = "TK_OPS_MIGRATION_LOCK_PATH"
MIGRATION_LOCK_TIMEOUT_ENV = "TK_OPS_MIGRATION_LOCK_TIMEOUT_SECONDS"
MIGRATION_BACKUP_RETENTION_KEY = "migration.backupRetention"
MIGRATION_BACKUP_RETENTION_DEFAULT = 5
MIGRATION_BACKUP_RETENTION_MINIMUM = 1
MIGRATION_BACKUP_RETENTION_MAXIMUM = 50
MIGRATION_BOOTSTRAP_PROJECTION_SCHEMA_VERSION = 1
MIGRATION_BOOTSTRAP_PROJECTION_MAX_BYTES = 16_384
MIGRATION_BOOTSTRAP_PROJECTION_RELATIVE_PATH = (
    Path("config") / "runtime-bootstrap.json"
)


class MigrationConfigurationError(RuntimeError):
    """数据库迁移配置无法安全解析。"""


@dataclass(frozen=True, slots=True)
class MigrationConfig:
    backup_dir: Path
    backup_retention_count: int
    lock_path: Path
    lock_timeout_seconds: float
    cutover_journal_path: Path | None = None
    compatibility_evidence_path: Path | None = None
    bootstrap_projection_path: Path | None = None
    bootstrap_projection_revision: int | None = None
    bootstrap_projection_sha256: str | None = None
    backup_retention_source: str = "default"


@dataclass(frozen=True, slots=True)
class MigrationBootstrapProjection:
    config_revision: int
    backup_retention_count: int
    sha256: str


def resolve_migration_config(
    data_dir: Path,
    database_path: Path,
    *,
    environ: Mapping[str, str] | None = None,
) -> MigrationConfig:
    """从统一环境配置入口解析启动迁移边界。"""

    environment = os.environ if environ is None else environ
    try:
        resolved_database_path = database_path.resolve()
        migration_root = resolved_database_path.parent / (
            f".{resolved_database_path.name}.migrations"
        )
        backup_dir = _resolve_path(
            environment.get(MIGRATION_BACKUP_DIR_ENV, ""),
            migration_root / "backups",
            relative_to=migration_root,
        )
        lock_path = _resolve_path(
            environment.get(MIGRATION_LOCK_PATH_ENV, ""),
            migration_root / "database-migration.lock",
            relative_to=migration_root,
        )
        lock_timeout_seconds = _parse_timeout(
            environment.get(MIGRATION_LOCK_TIMEOUT_ENV, "30")
        )
        projection_path = resolve_migration_bootstrap_projection_path(data_dir)
        projection = load_migration_bootstrap_projection(projection_path)
        backup_retention_count = (
            MIGRATION_BACKUP_RETENTION_DEFAULT
            if projection is None
            else projection.backup_retention_count
        )
        backup_retention_source = "default" if projection is None else "projection"
        deployment_override = environment.get(MIGRATION_BACKUP_RETENTION_ENV)
        if deployment_override is not None:
            backup_retention_count = _parse_retention(deployment_override)
            backup_retention_source = "deployment_env"
            log.warning(
                "数据库迁移备份保留数量使用部署环境覆盖",
                extra={"backup_retention_count": backup_retention_count},
            )
        _validate_paths(
            database_path=resolved_database_path,
            backup_dir=backup_dir,
            lock_path=lock_path,
        )
        return MigrationConfig(
            backup_dir=backup_dir,
            backup_retention_count=backup_retention_count,
            lock_path=lock_path,
            lock_timeout_seconds=lock_timeout_seconds,
            cutover_journal_path=(
                migration_root / "cutover-journal.json"
            ).resolve(),
            compatibility_evidence_path=(
                migration_root / "runtime-schema-compatibility.json"
            ).resolve(),
            bootstrap_projection_path=projection_path,
            bootstrap_projection_revision=(
                None if projection is None else projection.config_revision
            ),
            bootstrap_projection_sha256=(
                None if projection is None else projection.sha256
            ),
            backup_retention_source=backup_retention_source,
        )
    except MigrationConfigurationError:
        log.exception("数据库迁移配置解析失败")
        raise
    except (OSError, RuntimeError, ValueError) as exc:
        log.exception("数据库迁移配置解析失败")
        raise MigrationConfigurationError(
            "数据库迁移配置无法解析，请检查路径、超时和备份保留数量"
        ) from exc


def _resolve_path(
    raw_value: str,
    default_path: Path,
    *,
    relative_to: Path,
) -> Path:
    value = raw_value.strip()
    path = Path(value).expanduser() if value else default_path
    if not path.is_absolute():
        path = relative_to / path
    return path.resolve()


def _parse_timeout(raw_value: str) -> float:
    try:
        value = float(raw_value.strip())
    except ValueError as exc:
        raise MigrationConfigurationError("数据库迁移锁超时必须是有效数字") from exc
    if not math.isfinite(value) or not 0 <= value <= 300:
        raise MigrationConfigurationError("数据库迁移锁超时必须在 0 到 300 秒之间")
    return value


def _parse_retention(raw_value: str) -> int:
    try:
        value = int(raw_value.strip())
    except ValueError as exc:
        raise MigrationConfigurationError("数据库迁移备份保留数量必须是整数") from exc
    if not is_valid_migration_backup_retention(value):
        raise MigrationConfigurationError("数据库迁移备份保留数量必须在 1 到 50 之间")
    return value


def is_valid_migration_backup_retention(value: object) -> bool:
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and MIGRATION_BACKUP_RETENTION_MINIMUM
        <= value
        <= MIGRATION_BACKUP_RETENTION_MAXIMUM
    )


def resolve_migration_bootstrap_projection_path(data_dir: Path) -> Path:
    return (data_dir.resolve() / MIGRATION_BOOTSTRAP_PROJECTION_RELATIVE_PATH).resolve()


def load_migration_bootstrap_projection(
    projection_path: Path,
) -> MigrationBootstrapProjection | None:
    """读取迁移前可用的配置总线投影，损坏时禁止继续启动。"""

    if not projection_path.exists():
        return None
    if projection_path.is_symlink() or not projection_path.is_file():
        raise MigrationConfigurationError("迁移启动配置投影必须是受控普通文件")
    try:
        if projection_path.stat().st_size > MIGRATION_BOOTSTRAP_PROJECTION_MAX_BYTES:
            raise MigrationConfigurationError("迁移启动配置投影超过大小上限")
        document = json.loads(projection_path.read_text(encoding="utf-8"))
    except MigrationConfigurationError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise MigrationConfigurationError("迁移启动配置投影无法读取") from exc
    if not isinstance(document, Mapping):
        raise MigrationConfigurationError("迁移启动配置投影结构无效")

    expected_keys = {
        "schemaVersion",
        "configRevision",
        "values",
        "sha256",
    }
    if set(document) != expected_keys:
        raise MigrationConfigurationError("迁移启动配置投影字段无效")
    schema_version = document.get("schemaVersion")
    config_revision = document.get("configRevision")
    values = document.get("values")
    sha256 = document.get("sha256")
    if schema_version != MIGRATION_BOOTSTRAP_PROJECTION_SCHEMA_VERSION:
        raise MigrationConfigurationError("迁移启动配置投影版本不受支持")
    if (
        not isinstance(config_revision, int)
        or isinstance(config_revision, bool)
        or config_revision < 0
    ):
        raise MigrationConfigurationError("迁移启动配置投影 revision 无效")
    if not isinstance(values, Mapping) or set(values) != {
        MIGRATION_BACKUP_RETENTION_KEY
    }:
        raise MigrationConfigurationError("迁移启动配置投影 values 无效")
    retention = values.get(MIGRATION_BACKUP_RETENTION_KEY)
    if not is_valid_migration_backup_retention(retention):
        raise MigrationConfigurationError("迁移启动配置投影备份保留数量无效")
    if not isinstance(sha256, str) or len(sha256) != 64:
        raise MigrationConfigurationError("迁移启动配置投影摘要无效")

    body = {
        "schemaVersion": schema_version,
        "configRevision": config_revision,
        "values": {MIGRATION_BACKUP_RETENTION_KEY: retention},
    }
    expected_sha256 = _projection_sha256(body)
    if not hmac.compare_digest(sha256, expected_sha256):
        raise MigrationConfigurationError("迁移启动配置投影校验失败")
    return MigrationBootstrapProjection(
        config_revision=config_revision,
        backup_retention_count=retention,
        sha256=sha256,
    )


def write_migration_bootstrap_projection(
    data_dir: Path,
    *,
    config_revision: int,
    backup_retention_count: int,
) -> MigrationBootstrapProjection:
    """将配置总线的迁移键原子投影到数据库打开前可读的位置。"""

    if (
        not isinstance(config_revision, int)
        or isinstance(config_revision, bool)
        or config_revision < 0
    ):
        raise MigrationConfigurationError("迁移启动配置投影 revision 无效")
    if not is_valid_migration_backup_retention(backup_retention_count):
        raise MigrationConfigurationError("迁移启动配置投影备份保留数量无效")

    projection_path = resolve_migration_bootstrap_projection_path(data_dir)
    if projection_path.is_symlink():
        raise MigrationConfigurationError("迁移启动配置投影不能写入符号链接")
    body = {
        "schemaVersion": MIGRATION_BOOTSTRAP_PROJECTION_SCHEMA_VERSION,
        "configRevision": config_revision,
        "values": {
            MIGRATION_BACKUP_RETENTION_KEY: backup_retention_count,
        },
    }
    sha256 = _projection_sha256(body)
    document = {**body, "sha256": sha256}
    payload = (
        json.dumps(
            document,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    )
    projection_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = projection_path.with_name(
        f".{projection_path.name}.{uuid4().hex}.tmp"
    )
    try:
        with temporary_path.open("x", encoding="utf-8", newline="\n") as file:
            file.write(payload)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary_path, projection_path)
    except (OSError, UnicodeError) as exc:
        temporary_path.unlink(missing_ok=True)
        log.exception("迁移启动配置投影原子写入失败")
        raise MigrationConfigurationError("迁移启动配置投影无法保存") from exc
    return MigrationBootstrapProjection(
        config_revision=config_revision,
        backup_retention_count=backup_retention_count,
        sha256=sha256,
    )


def _projection_sha256(body: Mapping[str, object]) -> str:
    canonical = json.dumps(
        body,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _validate_paths(
    *,
    database_path: Path,
    backup_dir: Path,
    lock_path: Path,
) -> None:
    protected_database_paths = {
        database_path,
        Path(f"{database_path}-wal"),
        Path(f"{database_path}-shm"),
    }
    if lock_path in protected_database_paths:
        raise MigrationConfigurationError("数据库迁移锁不能覆盖数据库恢复单元")
    if backup_dir == database_path or database_path.is_relative_to(backup_dir):
        raise MigrationConfigurationError("数据库文件不能位于迁移备份目录内")
