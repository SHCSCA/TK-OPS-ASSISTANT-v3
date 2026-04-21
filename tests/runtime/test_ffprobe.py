from __future__ import annotations

from pathlib import Path

from services.ffprobe import (
    FfprobeAvailability,
    FfprobeResult,
    get_ffprobe_availability,
    parse_ffprobe_output,
)


def test_parse_valid_ffprobe_json() -> None:
    raw = {
        "streams": [
            {
                "codec_type": "video",
                "codec_name": "h264",
                "width": 1920,
                "height": 1080,
                "r_frame_rate": "30/1",
                "duration": "120.5",
            }
        ],
        "format": {"duration": "120.5", "size": "5000000"},
    }

    result = parse_ffprobe_output(raw)

    assert isinstance(result, FfprobeResult)
    assert result.duration_seconds == 120.5
    assert result.width == 1920
    assert result.height == 1080
    assert result.frame_rate == 30.0
    assert result.codec == "h264"
    assert result.file_size_bytes == 5000000


def test_parse_audio_only_stream() -> None:
    result = parse_ffprobe_output(
        {
            "streams": [{"codec_type": "audio", "codec_name": "aac"}],
            "format": {"duration": "60.0", "size": "1000000"},
        }
    )

    assert result.width is None
    assert result.height is None
    assert result.frame_rate is None
    assert result.duration_seconds == 60.0
    assert result.file_size_bytes == 1000000


def test_parse_missing_format_duration() -> None:
    result = parse_ffprobe_output({"streams": [], "format": {}})

    assert result.duration_seconds is None
    assert result.file_size_bytes is None


def test_ffprobe_availability_reports_missing_binary(monkeypatch) -> None:
    monkeypatch.setattr('services.ffprobe.shutil.which', lambda _name: None)

    result = get_ffprobe_availability()

    assert isinstance(result, FfprobeAvailability)
    assert result.status == 'unavailable'
    assert result.path is None
    assert result.version is None
    assert result.error_code == 'media.ffprobe_unavailable'


def test_ffprobe_availability_reports_incompatible_binary(monkeypatch, tmp_path: Path) -> None:
    fake_binary = tmp_path / 'ffprobe.exe'
    fake_binary.write_text('not-used', encoding='utf-8')

    monkeypatch.setattr('services.ffprobe.shutil.which', lambda _name: str(fake_binary))

    def _raise(*_args, **_kwargs):
        raise RuntimeError('boom')

    monkeypatch.setattr('services.ffprobe.subprocess.run', _raise)

    result = get_ffprobe_availability()

    assert result.status == 'incompatible'
    assert result.path == str(fake_binary)
    assert result.version is None
    assert result.error_code == 'media.ffprobe_incompatible'
