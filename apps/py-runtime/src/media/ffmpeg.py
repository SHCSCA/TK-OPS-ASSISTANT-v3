from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path

from services.media_tool_resolver import resolve_ffmpeg

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class MinimalRenderResult:
    output_path: Path | None
    error_code: str | None = None
    error_message: str | None = None


@dataclass(frozen=True, slots=True)
class FfmpegAvailability:
    status: str
    path: str | None
    source: str
    version: str | None
    error_code: str | None
    error_message: str | None


def get_ffmpeg_availability() -> FfmpegAvailability:
    resolution = resolve_ffmpeg()
    if resolution.path is None:
        return FfmpegAvailability(
            status=resolution.status,
            path=resolution.path,
            source=resolution.source,
            version=None,
            error_code=resolution.error_code,
            error_message=resolution.error_message,
        )
    return FfmpegAvailability(
        status=resolution.status,
        path=resolution.path,
        source=resolution.source,
        version=resolution.version,
        error_code=resolution.error_code,
        error_message=resolution.error_message,
    )


class MinimalFfmpegRenderer:
    def render_minimal_mp4(
        self,
        *,
        output_path: Path,
        project_id: str | None,
        project_name: str | None,
        preset: str,
        format: str,
    ) -> MinimalRenderResult:
        resolution = resolve_ffmpeg()
        if resolution.path is None:
            return MinimalRenderResult(
                output_path=None,
                error_code=resolution.error_code or "media.ffmpeg_unavailable",
                error_message=resolution.error_message or "FFmpeg 未安装或未配置到可执行路径。",
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        command = [
            resolution.path,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=720x1280:d=1",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=channel_layout=stereo:sample_rate=44100",
            "-shortest",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            str(output_path),
        ]
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
        except FileNotFoundError:
            log.exception("FFmpeg 可执行文件不存在: %s", resolution.path)
            return MinimalRenderResult(
                output_path=None,
                error_code="media.ffmpeg_unavailable",
                error_message="FFmpeg 未安装或未配置到可执行路径。",
            )
        except subprocess.TimeoutExpired:
            log.exception("FFmpeg 最小渲染超时: output_path=%s", output_path)
            return MinimalRenderResult(
                output_path=None,
                error_code="media.ffmpeg_timeout",
                error_message="FFmpeg 渲染超时，请重试或检查本地媒体工具。",
            )
        except Exception:
            log.exception("FFmpeg 最小渲染执行失败")
            return MinimalRenderResult(
                output_path=None,
                error_code="media.ffmpeg_failed",
                error_message="FFmpeg 渲染执行失败，请检查日志。",
            )

        if result.returncode != 0:
            stderr_summary = (result.stderr or "").strip().splitlines()[-1:] or [""]
            log.warning(
                "FFmpeg 返回异常状态码: code=%s path=%s stderr=%s",
                result.returncode,
                resolution.path,
                stderr_summary[0][:500],
            )
            return MinimalRenderResult(
                output_path=None,
                error_code="media.ffmpeg_failed",
                error_message="FFmpeg 渲染失败，请检查媒体工具配置。",
            )

        try:
            if not output_path.exists() or output_path.stat().st_size <= 0:
                return MinimalRenderResult(
                    output_path=None,
                    error_code="render.output_not_found",
                    error_message="渲染任务执行完成，但输出文件不存在或为空。",
                )
        except OSError:
            log.exception("校验 FFmpeg 输出文件失败: %s", output_path)
            return MinimalRenderResult(
                output_path=None,
                error_code="render.output_not_found",
                error_message="渲染任务执行完成，但输出文件无法访问。",
            )

        return MinimalRenderResult(output_path=output_path)
