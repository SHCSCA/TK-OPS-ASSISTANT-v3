from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class FfprobeResult:
    duration_seconds: float | None
    width: int | None
    height: int | None
    frame_rate: float | None
    codec: str | None
    file_size_bytes: int | None


def probe_video(file_path: Path) -> FfprobeResult | None:
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_streams",
                "-show_format",
                str(file_path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except FileNotFoundError:
        log.warning("FFprobe is not available on PATH.")
        return None
    except Exception:
        log.exception("FFprobe invocation failed.")
        return None

    if result.returncode != 0:
        log.warning("FFprobe returned non-zero exit code: %s", result.returncode)
        return None

    try:
        return parse_ffprobe_output(json.loads(result.stdout))
    except json.JSONDecodeError:
        log.warning("FFprobe returned invalid JSON.")
        return None


def parse_ffprobe_output(raw: dict[str, Any]) -> FfprobeResult:
    video_stream = next(
        (stream for stream in raw.get("streams", []) if stream.get("codec_type") == "video"),
        None,
    )
    fmt = raw.get("format", {})
    duration_raw = (video_stream or {}).get("duration") or fmt.get("duration")
    size_raw = fmt.get("size")

    return FfprobeResult(
        duration_seconds=_to_float(duration_raw),
        width=_to_int((video_stream or {}).get("width")),
        height=_to_int((video_stream or {}).get("height")),
        frame_rate=_parse_frame_rate((video_stream or {}).get("r_frame_rate")),
        codec=(video_stream or {}).get("codec_name"),
        file_size_bytes=_to_int(size_raw),
    )


def _parse_frame_rate(value: object) -> float | None:
    if not value:
        return None

    try:
        raw = str(value)
        if "/" in raw:
            numerator, denominator = raw.split("/", 1)
            denominator_value = float(denominator)
            if denominator_value == 0:
                return None
            return round(float(numerator) / denominator_value, 2)
        return round(float(raw), 2)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def _to_float(value: object) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: object) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
