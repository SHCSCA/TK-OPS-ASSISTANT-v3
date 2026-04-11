from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    version: str
    mode: str


def load_runtime_config() -> RuntimeConfig:
    return RuntimeConfig(
        version=_load_runtime_version(),
        mode=os.getenv("TK_OPS_RUNTIME_MODE", "development").strip() or "development",
    )


def _load_runtime_version() -> str:
    pyproject_path = Path(__file__).resolve().parents[2] / "pyproject.toml"
    try:
        with pyproject_path.open("rb") as file:
            pyproject = tomllib.load(file)
    except OSError:
        return "unknown"

    return str(pyproject.get("project", {}).get("version", "unknown"))
