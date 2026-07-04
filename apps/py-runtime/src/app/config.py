from __future__ import annotations

import logging
import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

log = logging.getLogger(__name__)

DEFAULT_ALLOWED_ORIGINS: tuple[str, ...] = (
    "http://127.0.0.1:1420",
    "http://localhost:1420",
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "http://127.0.0.1:5174",
    "http://localhost:5174",
    "tauri://localhost",
    "http://tauri.localhost",
)


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    version: str
    mode: str
    repo_root: Path
    data_dir: Path
    database_path: Path
    license_public_key_path: Path
    allowed_origins: tuple[str, ...]


def load_runtime_config() -> RuntimeConfig:
    repo_root = Path(__file__).resolve().parents[4]
    data_dir = Path(
        os.getenv("TK_OPS_RUNTIME_DATA_DIR", str(repo_root / ".runtime-data"))
    ).expanduser()
    database_path = Path(
        os.getenv("TK_OPS_RUNTIME_DB_PATH", str(data_dir / "runtime.db"))
    ).expanduser()
    license_public_key_path = Path(
        os.getenv(
            "TK_OPS_LICENSE_PUBLIC_KEY_PATH",
            str(data_dir / "licenses" / "license-public.pem"),
        )
    ).expanduser()

    return RuntimeConfig(
        version=_load_runtime_version(),
        mode=os.getenv("TK_OPS_RUNTIME_MODE", "development").strip() or "development",
        repo_root=repo_root,
        data_dir=data_dir.resolve(),
        database_path=database_path.resolve(),
        license_public_key_path=license_public_key_path.resolve(),
        allowed_origins=_load_allowed_origins(),
    )


def _load_runtime_version() -> str:
    pyproject_path = Path(__file__).resolve().parents[2] / "pyproject.toml"
    try:
        with pyproject_path.open("rb") as file:
            pyproject = tomllib.load(file)
    except OSError:
        return "unknown"

    return str(pyproject.get("project", {}).get("version", "unknown"))


def _load_allowed_origins() -> tuple[str, ...]:
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
    return tuple(dict.fromkeys((*DEFAULT_ALLOWED_ORIGINS, *custom_origins)))


def _is_precise_origin(origin: str) -> bool:
    if origin == "*":
        log.warning("已忽略不安全的 Runtime CORS 通配符配置")
        return False

    parsed = urlsplit(origin)
    if (
        not parsed.scheme
        or not parsed.netloc
        or parsed.path
        or parsed.query
        or parsed.fragment
    ):
        log.warning("已忽略非法 Runtime CORS origin 配置：%s", origin)
        return False

    return True
