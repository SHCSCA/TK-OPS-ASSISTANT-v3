from __future__ import annotations

from services.ffprobe import FfprobeResult, parse_ffprobe_output


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
