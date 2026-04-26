from __future__ import annotations

import json
import logging
import subprocess
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO

from services.media_tool_resolver import resolve_ffprobe

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class FfprobeResult:
    duration_seconds: float | None
    width: int | None
    height: int | None
    frame_rate: float | None
    codec: str | None
    file_size_bytes: int | None


@dataclass(frozen=True, slots=True)
class FfprobeAvailability:
    status: str
    path: str | None
    source: str
    version: str | None
    error_code: str | None
    error_message: str | None


@dataclass(slots=True)
class _Mp4FallbackMetadata:
    has_signature: bool = False
    duration_seconds: float | None = None
    width: int | None = None
    height: int | None = None
    codec: str | None = None


_MP4_FALLBACK_EXTENSIONS = {".mp4", ".m4v", ".mov"}
_MP4_CONTAINER_BOXES = {"moov", "trak", "mdia", "minf", "stbl"}


def get_ffprobe_availability() -> FfprobeAvailability:
    resolution = resolve_ffprobe()
    if resolution.path is None:
        return FfprobeAvailability(
            status=resolution.status,
            path=resolution.path,
            source=resolution.source,
            version=None,
            error_code=resolution.error_code,
            error_message=resolution.error_message,
        )

    try:
        result = subprocess.run(
            [resolution.path, "-version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except Exception:
        log.exception("FFprobe version probe failed.")
        return FfprobeAvailability(
            status="incompatible",
            path=resolution.path,
            source=resolution.source,
            version=None,
            error_code="media.ffprobe_incompatible",
            error_message="FFprobe 无法正常执行，请检查路径配置或二进制兼容性。",
        )

    if result.returncode != 0:
        return FfprobeAvailability(
            status="incompatible",
            path=resolution.path,
            source=resolution.source,
            version=None,
            error_code="media.ffprobe_incompatible",
            error_message="FFprobe 返回异常状态码，请检查本地安装是否完整。",
        )

    first_line = next((line.strip() for line in result.stdout.splitlines() if line.strip()), "")
    return FfprobeAvailability(
        status="ready",
        path=resolution.path,
        source=resolution.source,
        version=first_line or None,
        error_code=None,
        error_message=None,
    )


def probe_video(file_path: Path) -> FfprobeResult | None:
    resolution = resolve_ffprobe()
    if resolution.path is None:
        log.warning("FFprobe is not available on PATH.")
        return _probe_video_with_builtin_fallback(file_path)

    try:
        result = subprocess.run(
            [
                resolution.path,
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
        return _probe_video_with_builtin_fallback(file_path)
    except Exception:
        log.exception("FFprobe invocation failed.")
        return _probe_video_with_builtin_fallback(file_path)

    if result.returncode != 0:
        log.warning("FFprobe returned non-zero exit code: %s", result.returncode)
        return _probe_video_with_builtin_fallback(file_path)

    try:
        return parse_ffprobe_output(json.loads(result.stdout))
    except json.JSONDecodeError:
        log.warning("FFprobe returned invalid JSON.")
        return _probe_video_with_builtin_fallback(file_path)


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


def _probe_video_with_builtin_fallback(file_path: Path) -> FfprobeResult | None:
    if file_path.suffix.lower() not in _MP4_FALLBACK_EXTENSIONS:
        return None

    try:
        file_size = file_path.stat().st_size
        metadata = _read_mp4_fallback_metadata(file_path, file_size)
        if not metadata.has_signature:
            return None
        return FfprobeResult(
            duration_seconds=metadata.duration_seconds,
            width=metadata.width,
            height=metadata.height,
            frame_rate=None,
            codec=metadata.codec,
            file_size_bytes=file_size,
        )
    except Exception:
        log.exception("MP4 fallback metadata probe failed.")
        return None


def _read_mp4_fallback_metadata(file_path: Path, file_size: int) -> _Mp4FallbackMetadata:
    metadata = _Mp4FallbackMetadata()
    with file_path.open("rb") as handle:
        _scan_mp4_boxes(handle, file_size, metadata)
    return metadata


def _scan_mp4_boxes(handle: BinaryIO, end_offset: int, metadata: _Mp4FallbackMetadata) -> None:
    position = handle.tell()
    while position + 8 <= end_offset:
        handle.seek(position)
        header = handle.read(8)
        if len(header) < 8:
            return

        size, raw_box_type = struct.unpack(">I4s", header)
        box_type = raw_box_type.decode("ascii", errors="ignore")
        header_size = 8
        if size == 1:
            extended_size = handle.read(8)
            if len(extended_size) < 8:
                return
            size = struct.unpack(">Q", extended_size)[0]
            header_size = 16
        elif size == 0:
            size = end_offset - position

        box_end = position + size
        payload_start = position + header_size
        if size < header_size or box_end > end_offset or box_end <= payload_start:
            return

        if box_type == "mvhd":
            _parse_mvhd_box(handle, payload_start, box_end, metadata)
        elif box_type == "ftyp":
            metadata.has_signature = True
        elif box_type == "tkhd":
            _parse_tkhd_box(handle, payload_start, box_end, metadata)
        elif box_type == "stsd":
            _parse_stsd_box(handle, payload_start, box_end, metadata)
        elif box_type in _MP4_CONTAINER_BOXES:
            handle.seek(payload_start)
            _scan_mp4_boxes(handle, box_end, metadata)

        position = box_end


def _parse_mvhd_box(
    handle: BinaryIO,
    payload_start: int,
    box_end: int,
    metadata: _Mp4FallbackMetadata,
) -> None:
    payload = _read_payload(handle, payload_start, box_end, 40)
    if len(payload) < 24:
        return

    version = payload[0]
    if version == 1:
        if len(payload) < 32:
            return
        timescale = struct.unpack(">I", payload[20:24])[0]
        duration = struct.unpack(">Q", payload[24:32])[0]
    else:
        timescale = struct.unpack(">I", payload[12:16])[0]
        duration = struct.unpack(">I", payload[16:20])[0]

    if timescale > 0:
        metadata.duration_seconds = round(duration / timescale, 3)


def _parse_tkhd_box(
    handle: BinaryIO,
    payload_start: int,
    box_end: int,
    metadata: _Mp4FallbackMetadata,
) -> None:
    payload = _read_payload(handle, payload_start, box_end, 160)
    if len(payload) < 8:
        return

    width_fixed, height_fixed = struct.unpack(">II", payload[-8:])
    width = width_fixed >> 16
    height = height_fixed >> 16
    if width > 0 and height > 0:
        metadata.width = width
        metadata.height = height


def _parse_stsd_box(
    handle: BinaryIO,
    payload_start: int,
    box_end: int,
    metadata: _Mp4FallbackMetadata,
) -> None:
    payload = _read_payload(handle, payload_start, box_end, 32)
    if len(payload) < 16:
        return

    entry_count = struct.unpack(">I", payload[4:8])[0]
    if entry_count < 1:
        return

    codec = payload[12:16].decode("ascii", errors="ignore").strip("\x00")
    if codec:
        metadata.codec = codec


def _read_payload(handle: BinaryIO, start: int, end: int, limit: int) -> bytes:
    handle.seek(start)
    return handle.read(min(end - start, limit))


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
