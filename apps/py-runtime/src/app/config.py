from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    version: str
    mode: str
    repo_root: Path
    data_dir: Path
    database_path: Path
    license_public_key_path: Path


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
    )


def _load_runtime_version() -> str:
    pyproject_path = Path(__file__).resolve().parents[2] / "pyproject.toml"
    try:
        with pyproject_path.open("rb") as file:
            pyproject = tomllib.load(file)
    except OSError:
        return "unknown"

    return str(pyproject.get("project", {}).get("version", "unknown"))
