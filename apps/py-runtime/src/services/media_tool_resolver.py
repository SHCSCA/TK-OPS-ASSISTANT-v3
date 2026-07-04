from __future__ import annotations

import logging
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)

FFPROBE_RELATIVE_PATH = Path("bin") / "ffprobe" / "windows-x64" / "ffprobe.exe"
FFMPEG_RELATIVE_PATH = Path("bin") / "ffmpeg" / "windows-x64" / "ffmpeg.exe"
_configured_ffprobe_path: str | None = None
_configured_ffmpeg_path: str | None = None


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
            return _ready(executable, "ffprobe", "config")
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
            return _ready(executable, "ffprobe", "configured")
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
        return _ready(bundled, "ffprobe", "bundled")

    detected = shutil.which("ffprobe")
    if detected:
        return _ready(Path(detected), "ffprobe", "path")

    return MediaToolResolution(
        status="unavailable",
        tool="ffprobe",
        path=None,
        source="fallback",
        version=None,
        error_code="media.ffprobe_unavailable",
        error_message="FFprobe 未安装或未配置到可执行路径。",
    )


def resolve_ffmpeg(*, repo_root: Path | None = None) -> MediaToolResolution:
    if _configured_ffmpeg_path:
        configured_path = Path(_configured_ffmpeg_path).expanduser()
        executable = _normalize_tool_candidate(configured_path, executable_name="ffmpeg.exe")
        if executable is not None:
            return _ready(executable, "ffmpeg", "config")
        return MediaToolResolution(
            status="unavailable",
            tool="ffmpeg",
            path=str(configured_path),
            source="config",
            version=None,
            error_code="media.ffmpeg_configured_path_missing",
            error_message="配置总线中的 FFmpeg 路径不存在。",
        )

    configured = os.getenv("TK_OPS_FFMPEG_PATH", "").strip()
    if configured:
        configured_path = Path(configured).expanduser()
        executable = _normalize_tool_candidate(configured_path, executable_name="ffmpeg.exe")
        if executable is not None:
            return _ready(executable, "ffmpeg", "configured")
        return MediaToolResolution(
            status="unavailable",
            tool="ffmpeg",
            path=str(configured_path),
            source="configured",
            version=None,
            error_code="media.ffmpeg_configured_path_missing",
            error_message="已配置 FFmpeg 路径，但文件不存在。",
        )

    bundled = _resolve_bundled_tool(
        repo_root=repo_root,
        relative_path=FFMPEG_RELATIVE_PATH,
    )
    if bundled is not None:
        return _ready(bundled, "ffmpeg", "bundled")

    detected = shutil.which("ffmpeg")
    if detected:
        return _ready(Path(detected), "ffmpeg", "path")

    return MediaToolResolution(
        status="unavailable",
        tool="ffmpeg",
        path=None,
        source="fallback",
        version=None,
        error_code="media.ffmpeg_unavailable",
        error_message="FFmpeg 未安装或未配置到可执行路径。",
    )


def configure_ffprobe_path(path: str | None) -> None:
    global _configured_ffprobe_path
    normalized = (path or "").strip()
    _configured_ffprobe_path = normalized or None


def configure_ffmpeg_path(path: str | None) -> None:
    global _configured_ffmpeg_path
    normalized = (path or "").strip()
    _configured_ffmpeg_path = normalized or None


def _resolve_bundled_ffprobe(*, repo_root: Path | None) -> Path | None:
    return _resolve_bundled_tool(repo_root=repo_root, relative_path=FFPROBE_RELATIVE_PATH)


def _resolve_bundled_tool(*, repo_root: Path | None, relative_path: Path) -> Path | None:
    resource_dir = os.getenv("TK_OPS_RESOURCE_DIR", "").strip()
    candidates: list[Path] = []
    if resource_dir:
        candidates.append(Path(resource_dir).expanduser() / relative_path)

    if repo_root is not None:
        candidates.append(repo_root / "apps" / "desktop" / "src-tauri" / "resources" / relative_path)
        candidates.append(repo_root / "src-tauri" / "resources" / relative_path)

    for candidate in candidates:
        try:
            if candidate.exists():
                return candidate.resolve()
        except OSError:
            log.exception("检测内置媒体工具路径失败: %s", candidate)
    return None


def _normalize_ffprobe_candidate(path: Path) -> Path | None:
    return _normalize_tool_candidate(path, executable_name="ffprobe.exe")


def _normalize_tool_candidate(path: Path, *, executable_name: str) -> Path | None:
    try:
        if path.is_file():
            return path.resolve()
        nested = path / executable_name
        if nested.is_file():
            return nested.resolve()
    except OSError:
        log.exception("解析媒体工具配置路径失败: %s", path)
    return None


def _ready(path: Path, tool: str, source: str) -> MediaToolResolution:
    return MediaToolResolution(
        status="ready",
        tool=tool,
        path=str(path),
        source=source,
        version=None,
        error_code=None,
        error_message=None,
    )
