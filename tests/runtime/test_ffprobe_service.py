from __future__ import annotations

import struct
from pathlib import Path
from unittest.mock import patch

from services.ffprobe import probe_video


def _box(name: str, payload: bytes) -> bytes:
    return struct.pack(">I4s", len(payload) + 8, name.encode("ascii")) + payload


def _full_box(name: str, payload: bytes) -> bytes:
    return _box(name, b"\x00\x00\x00\x00" + payload)


def _make_minimal_mp4(path: Path) -> None:
    mvhd_payload = b"\x00" * 8 + struct.pack(">II", 1000, 30_000) + b"\x00" * 80
    tkhd_payload = (
        b"\x00" * 8
        + struct.pack(">II", 1, 0)
        + struct.pack(">I", 30_000)
        + b"\x00" * 16
        + b"\x00" * 36
        + struct.pack(">II", 1080 << 16, 1920 << 16)
    )
    sample_entry = struct.pack(">I4s", 16, b"avc1") + b"\x00" * 8
    stsd = _full_box("stsd", struct.pack(">I", 1) + sample_entry)
    stbl = _box("stbl", stsd)
    minf = _box("minf", stbl)
    mdia = _box("mdia", minf)
    trak = _box("trak", _full_box("tkhd", tkhd_payload) + mdia)
    moov = _box("moov", _full_box("mvhd", mvhd_payload) + trak)
    ftyp = _box("ftyp", b"isom\x00\x00\x02\x00isomiso2avc1mp41")
    path.write_bytes(ftyp + moov + _box("mdat", b"\x00" * 32))


def test_probe_video_uses_mp4_fallback_when_ffprobe_is_unavailable(tmp_path: Path) -> None:
    video_path = tmp_path / "fallback.mp4"
    _make_minimal_mp4(video_path)

    with patch("services.ffprobe.resolve_ffprobe") as resolver:
        resolver.return_value = type(
            "Resolution",
            (),
            {"path": None},
        )()
        result = probe_video(video_path)

    assert result is not None
    assert result.duration_seconds == 30
    assert result.width == 1080
    assert result.height == 1920
    assert result.codec == "avc1"
    assert result.file_size_bytes == video_path.stat().st_size


def test_probe_video_fallback_rejects_unrecognized_mp4_payload(tmp_path: Path) -> None:
    video_path = tmp_path / "broken.mp4"
    video_path.write_bytes(b"\x00" * 128)

    with patch("services.ffprobe.resolve_ffprobe") as resolver:
        resolver.return_value = type(
            "Resolution",
            (),
            {"path": None},
        )()
        result = probe_video(video_path)

    assert result is None
