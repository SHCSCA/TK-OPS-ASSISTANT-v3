from __future__ import annotations

import logging
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)

FFPROBE_RELATIVE_PATH = Path("bin") / "ffprobe" / "windows-x64" / "ffprobe.exe"
_configured_ffprobe_path: str | None = None


@dataclass(frozen=True, slots=True)
class MediaToolResolution:
    status: str
    tool: str
    path: str | None
    source: str
    version: str | None
    error_code: str | None
    error_message: str | None


def resolve_ffprobe(*, repo_root: Path | None = None) -> MediaToolResolution:
    if _configured_ffprobe_path:
        configured_path = Path(_configured_ffprobe_path).expanduser()
        executable = _normalize_ffprobe_candidate(configured_path)
        if executable is not None:
            return _ready(executable, "config")
        return MediaToolResolution(
            status="unavailable",
            tool="ffprobe",
            path=str(configured_path),
            source="config",
            version=None,
            error_code="media.ffprobe_configured_path_missing",
            error_message="配置总线中的 FFprobe 路径不存在。",
        )

    configured = os.getenv("TK_OPS_FFPROBE_PATH", "").strip()
    if configured:
        configured_path = Path(configured).expanduser()
        executable = _normalize_ffprobe_candidate(configured_path)
        if executable is not None:
            return _ready(executable, "configured")
        return MediaToolResolution(
            status="unavailable",
            tool="ffprobe",
            path=str(configured_path),
            source="configured",
            version=None,
            error_code="media.ffprobe_configured_path_missing",
            error_message="已配置 FFprobe 路径，但文件不存在。",
        )

    bundled = _resolve_bundled_ffprobe(repo_root=repo_root)
    if bundled is not None:
        return _ready(bundled, "bundled")

    detected = shutil.which("ffprobe")
    if detected:
        return _ready(Path(detected), "path")

    return MediaToolResolution(
        status="unavailable",
        tool="ffprobe",
        path=None,
        source="fallback",
        version=None,
        error_code="media.ffprobe_unavailable",
        error_message="FFprobe 未安装或未配置到可执行路径。",
    )


def configure_ffprobe_path(path: str | None) -> None:
    global _configured_ffprobe_path
    normalized = (path or "").strip()
    _configured_ffprobe_path = normalized or None


def _resolve_bundled_ffprobe(*, repo_root: Path | None) -> Path | None:
    resource_dir = os.getenv("TK_OPS_RESOURCE_DIR", "").strip()
    candidates: list[Path] = []
    if resource_dir:
        candidates.append(Path(resource_dir).expanduser() / FFPROBE_RELATIVE_PATH)

    if repo_root is not None:
        candidates.append(repo_root / "apps" / "desktop" / "src-tauri" / "resources" / FFPROBE_RELATIVE_PATH)
        candidates.append(repo_root / "src-tauri" / "resources" / FFPROBE_RELATIVE_PATH)

    for candidate in candidates:
        try:
            if candidate.exists():
                return candidate.resolve()
        except OSError:
            log.exception("检测内置 FFprobe 路径失败: %s", candidate)
    return None


def _normalize_ffprobe_candidate(path: Path) -> Path | None:
    try:
        if path.is_file():
            return path.resolve()
        nested = path / "ffprobe.exe"
        if nested.is_file():
            return nested.resolve()
    except OSError:
        log.exception("解析 FFprobe 配置路径失败: %s", path)
    return None


def _ready(path: Path, source: str) -> MediaToolResolution:
    return MediaToolResolution(
        status="ready",
        tool="ffprobe",
        path=str(path),
        source=source,
        version=None,
        error_code=None,
        error_message=None,
    )
