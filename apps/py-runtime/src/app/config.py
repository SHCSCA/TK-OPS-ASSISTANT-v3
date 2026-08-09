from __future__ import annotations

import logging
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import NoReturn
from urllib.parse import urlsplit

from app.version import RUNTIME_VERSION
from config.database import resolve_database_path, resolve_runtime_data_dir
from config.migration import MigrationConfig, resolve_migration_config

log = logging.getLogger(__name__)

TAURI_ALLOWED_ORIGINS: tuple[str, ...] = (
    "tauri://localhost",
    "http://tauri.localhost",
)
DEVELOPMENT_ALLOWED_ORIGINS: tuple[str, ...] = (
    "http://127.0.0.1:1420",
    "http://localhost:1420",
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "http://127.0.0.1:5174",
    "http://localhost:5174",
)
DEFAULT_ALLOWED_ORIGINS: tuple[str, ...] = (
    *DEVELOPMENT_ALLOWED_ORIGINS,
    *TAURI_ALLOWED_ORIGINS,
)
PRODUCTION_MODES = frozenset({"prod", "production"})
DEVELOPMENT_MODES = frozenset({"dev", "development", "test"})
SUPPORTED_RUNTIME_MODES = DEVELOPMENT_MODES | PRODUCTION_MODES
_STRONG_SESSION_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]{43,256}$")


class RuntimeConfigurationError(RuntimeError):
    """Runtime 启动配置不完整或不安全。"""


@dataclass(frozen=True, slots=True)
class RuntimeBootstrapConfig:
    repo_root: Path
    data_dir: Path


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    version: str
    mode: str
    repo_root: Path
    data_dir: Path
    database_path: Path
    migration: MigrationConfig
    license_public_key_path: Path
    allowed_origins: tuple[str, ...]
    runtime_session_token: str = field(default="", repr=False)
    expected_host: str = ""
    managed_sidecar: bool = False
    workspace_root_registry_path: Path | None = None


def load_runtime_bootstrap_config() -> RuntimeBootstrapConfig:
    repo_root = _resolve_repo_root()
    data_dir = resolve_runtime_data_dir(repo_root / ".runtime-data")
    return RuntimeBootstrapConfig(repo_root=repo_root, data_dir=data_dir)


def load_runtime_config(
    bootstrap_config: RuntimeBootstrapConfig | None = None,
) -> RuntimeConfig:
    bootstrap = bootstrap_config or load_runtime_bootstrap_config()
    repo_root = bootstrap.repo_root
    data_dir = bootstrap.data_dir
    database_path = resolve_database_path(data_dir)
    migration_config = resolve_migration_config(data_dir, database_path)
    runtime_mode = _load_runtime_mode()
    license_public_key_path = _load_license_public_key_path(
        repo_root,
        data_dir,
    )

    return RuntimeConfig(
        version=_load_runtime_version(),
        mode=runtime_mode,
        repo_root=repo_root,
        data_dir=data_dir,
        database_path=database_path,
        migration=migration_config,
        license_public_key_path=license_public_key_path.resolve(),
        allowed_origins=_load_allowed_origins(runtime_mode),
        runtime_session_token=_load_runtime_session_token(runtime_mode),
        expected_host=_load_expected_host(runtime_mode),
        managed_sidecar=_load_managed_sidecar(),
        workspace_root_registry_path=_load_workspace_root_registry_path(data_dir),
    )


def _load_workspace_root_registry_path(data_dir: Path) -> Path:
    configured = os.getenv("TK_OPS_WORKSPACE_ROOT_REGISTRY_PATH", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return (data_dir.parent / "workspace-roots.v1.json").resolve()


def _resolve_repo_root() -> Path:
    if getattr(sys, "frozen", False):
        bundle_root = getattr(sys, "_MEIPASS", "")
        if isinstance(bundle_root, str) and bundle_root:
            return Path(bundle_root).resolve()
        raise RuntimeConfigurationError("打包 Runtime 缺少资源根目录")
    return Path(__file__).resolve().parents[4]


def _load_license_public_key_path(
    repo_root: Path,
    data_dir: Path,
) -> Path:
    configured = os.getenv("TK_OPS_LICENSE_PUBLIC_KEY_PATH", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    bundled = (
        repo_root
        / "apps"
        / "py-runtime"
        / "resources"
        / "license-public.pem"
    )
    if bundled.is_file():
        return bundled.resolve()
    return (data_dir / "licenses" / "license-public.pem").resolve()


def _load_runtime_version() -> str:
    configured = os.getenv("TK_OPS_RUNTIME_VERSION", "").strip()
    if configured:
        return configured
    return RUNTIME_VERSION


def _load_managed_sidecar() -> bool:
    raw_value = os.getenv("TK_OPS_RUNTIME_MANAGED_SIDECAR", "").strip()
    if raw_value in {"", "0"}:
        return False
    if raw_value == "1":
        return True
    _raise_invalid_security_config("Runtime sidecar 管理标识无效")


def _load_runtime_mode() -> str:
    runtime_mode = (
        os.getenv("TK_OPS_RUNTIME_MODE", "development").strip().lower()
        or "development"
    )
    if runtime_mode not in SUPPORTED_RUNTIME_MODES:
        _raise_invalid_security_config("Runtime 运行模式无效")
    return runtime_mode


def _load_allowed_origins(runtime_mode: str) -> tuple[str, ...]:
    raw_origins = ",".join(
        value
        for value in (
            os.getenv("TK_OPS_RUNTIME_ALLOWED_ORIGINS", ""),
            os.getenv("TK_OPS_ALLOWED_ORIGINS", ""),
        )
        if value
    )
    custom_origins = tuple(
        origin
        for origin in (
            origin.strip()
            for origin in raw_origins.split(",")
            if origin.strip()
        )
        if _is_precise_origin(origin)
    )
    if is_production_mode(runtime_mode):
        if custom_origins:
            log.warning("生产模式已忽略 Runtime 开发 Origin 白名单")
        return TAURI_ALLOWED_ORIGINS

    return tuple(dict.fromkeys((*DEFAULT_ALLOWED_ORIGINS, *custom_origins)))


def _is_precise_origin(origin: str) -> bool:
    if origin == "*":
        log.warning("已忽略不安全的 Runtime CORS 通配符配置")
        return False

    try:
        parsed = urlsplit(origin)
        _ = parsed.port
    except ValueError:
        log.warning("已忽略非法 Runtime CORS origin 配置：%s", origin)
        return False
    if (
        parsed.scheme not in {"http", "https", "tauri"}
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path
        or parsed.query
        or parsed.fragment
    ):
        log.warning("已忽略非法 Runtime CORS origin 配置：%s", origin)
        return False

    return True


def _load_runtime_session_token(runtime_mode: str) -> str:
    token = os.getenv("TK_OPS_RUNTIME_SESSION_TOKEN", "")
    if token and (
        token != token.strip()
        or any(character.isspace() for character in token)
    ):
        _raise_invalid_security_config("Runtime 会话令牌格式非法")

    if is_production_mode(runtime_mode):
        if not token:
            _raise_invalid_security_config("生产模式缺少 Runtime 会话令牌")
        if not _STRONG_SESSION_TOKEN_PATTERN.fullmatch(token):
            _raise_invalid_security_config(
                "生产模式 Runtime 会话令牌必须为至少 256 bit 的随机值"
            )

    return token


def _load_expected_host(runtime_mode: str) -> str:
    expected_host = os.getenv("TK_OPS_RUNTIME_EXPECTED_HOST", "").strip()
    if expected_host and not _is_precise_expected_host(expected_host):
        _raise_invalid_security_config("Runtime Host 配置必须为 127.0.0.1 加受控端口")

    if not expected_host and is_production_mode(runtime_mode):
        _raise_invalid_security_config("生产模式缺少 Runtime Host 配置")

    return expected_host


def _is_precise_expected_host(expected_host: str) -> bool:
    try:
        parsed = urlsplit(f"//{expected_host}")
        port = parsed.port
    except ValueError:
        return False

    return (
        parsed.hostname == "127.0.0.1"
        and port is not None
        and 1 <= port <= 65535
        and parsed.netloc == expected_host
        and parsed.path == ""
        and parsed.query == ""
        and parsed.fragment == ""
        and parsed.username is None
        and parsed.password is None
    )


def is_development_mode(runtime_mode: str) -> bool:
    return runtime_mode.strip().lower() in DEVELOPMENT_MODES


def is_production_mode(runtime_mode: str) -> bool:
    return not is_development_mode(runtime_mode)


def _raise_invalid_security_config(message: str) -> NoReturn:
    log.error(message)
    raise RuntimeConfigurationError(message)
