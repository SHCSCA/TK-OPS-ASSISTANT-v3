from __future__ import annotations

import logging
import os
from collections.abc import Mapping
from pathlib import Path

log = logging.getLogger(__name__)

RUNTIME_DATA_DIR_ENV = "TK_OPS_RUNTIME_DATA_DIR"
RUNTIME_DATABASE_PATH_ENV = "TK_OPS_RUNTIME_DB_PATH"
LEGACY_DATABASE_PATH_ENV = "TK_OPS_DATABASE_PATH"


class DatabasePathConfigurationError(RuntimeError):
    """数据库路径配置无法安全解析。"""


def resolve_runtime_data_dir(
    default_data_dir: Path,
    *,
    environ: Mapping[str, str] | None = None,
) -> Path:
    environment = os.environ if environ is None else environ
    configured_path = environment.get(RUNTIME_DATA_DIR_ENV, "").strip()
    try:
        default_path = default_data_dir.expanduser().resolve()
        if not configured_path:
            return default_path
        return _normalize_path(configured_path, relative_to=default_path.parent)
    except (OSError, RuntimeError) as exc:
        log.exception("Runtime 数据目录配置解析失败")
        raise DatabasePathConfigurationError(
            "Runtime 数据目录配置无法解析，请检查路径格式和访问权限"
        ) from exc


def resolve_database_path(
    data_dir: Path,
    *,
    environ: Mapping[str, str] | None = None,
) -> Path:
    environment = os.environ if environ is None else environ
    configured_paths = {
        variable: value.strip()
        for variable in (RUNTIME_DATABASE_PATH_ENV, LEGACY_DATABASE_PATH_ENV)
        if (value := environment.get(variable, "")).strip()
    }

    try:
        resolved_data_dir = data_dir.expanduser().resolve()
        resolved_paths = {
            variable: _normalize_path(value, relative_to=resolved_data_dir)
            for variable, value in configured_paths.items()
        }
        if len({_comparison_key(path) for path in resolved_paths.values()}) > 1:
            raise DatabasePathConfigurationError(
                "数据库路径配置冲突：TK_OPS_RUNTIME_DB_PATH 与 "
                "TK_OPS_DATABASE_PATH 必须指向同一个数据库文件"
            )
        if resolved_paths:
            return next(iter(resolved_paths.values()))
        return (resolved_data_dir / "runtime.db").resolve()
    except DatabasePathConfigurationError:
        log.exception("数据库路径配置解析失败")
        raise
    except (OSError, RuntimeError) as exc:
        log.exception("数据库路径配置解析失败")
        raise DatabasePathConfigurationError(
            "数据库路径配置无法解析，请检查路径格式和访问权限"
        ) from exc


def database_path_to_url(database_path: Path) -> str:
    return f"sqlite:///{database_path.as_posix()}"


def _normalize_path(raw_path: str, *, relative_to: Path) -> Path:
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = relative_to / path
    return path.resolve()


def _comparison_key(path: Path) -> str:
    return os.path.normcase(str(path))
