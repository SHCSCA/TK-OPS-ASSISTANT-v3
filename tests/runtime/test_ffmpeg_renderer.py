from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from media.ffmpeg import MinimalFfmpegRenderer
from services.media_tool_resolver import MediaToolResolution


def test_minimal_ffmpeg_renderer_reports_unavailable_tool(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("media.ffmpeg.resolve_ffmpeg", lambda: _resolution(path=None))

    result = MinimalFfmpegRenderer().render_minimal_mp4(
        output_path=tmp_path / "out.mp4",
        project_id="project-1",
        project_name="项目",
        preset="1080p",
        format="mp4",
    )

    assert result.output_path is None
    assert result.error_code == "media.ffmpeg_unavailable"


def test_minimal_ffmpeg_renderer_reports_timeout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("media.ffmpeg.resolve_ffmpeg", lambda: _resolution(path="ffmpeg.exe"))

    def raise_timeout(*_args: object, **_kwargs: object) -> None:
        raise subprocess.TimeoutExpired(cmd="ffmpeg", timeout=60)

    monkeypatch.setattr("media.ffmpeg.subprocess.run", raise_timeout)

    result = MinimalFfmpegRenderer().render_minimal_mp4(
        output_path=tmp_path / "out.mp4",
        project_id="project-1",
        project_name="项目",
        preset="1080p",
        format="mp4",
    )

    assert result.output_path is None
    assert result.error_code == "media.ffmpeg_timeout"


def test_minimal_ffmpeg_renderer_reports_nonzero_exit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("media.ffmpeg.resolve_ffmpeg", lambda: _resolution(path="ffmpeg.exe"))
    monkeypatch.setattr(
        "media.ffmpeg.subprocess.run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=1, stderr="编码失败"),
    )

    result = MinimalFfmpegRenderer().render_minimal_mp4(
        output_path=tmp_path / "out.mp4",
        project_id="project-1",
        project_name="项目",
        preset="1080p",
        format="mp4",
    )

    assert result.output_path is None
    assert result.error_code == "media.ffmpeg_failed"


def test_minimal_ffmpeg_renderer_reports_missing_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("media.ffmpeg.resolve_ffmpeg", lambda: _resolution(path="ffmpeg.exe"))
    monkeypatch.setattr(
        "media.ffmpeg.subprocess.run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=0, stderr=""),
    )

    result = MinimalFfmpegRenderer().render_minimal_mp4(
        output_path=tmp_path / "missing.mp4",
        project_id="project-1",
        project_name="项目",
        preset="1080p",
        format="mp4",
    )

    assert result.output_path is None
    assert result.error_code == "render.output_not_found"


def _resolution(path: str | None) -> MediaToolResolution:
    if path is None:
        return MediaToolResolution(
            status="unavailable",
            tool="ffmpeg",
            path=None,
            source="fallback",
            version=None,
            error_code="media.ffmpeg_unavailable",
            error_message="FFmpeg 未安装或未配置到可执行路径。",
        )
    return MediaToolResolution(
        status="ready",
        tool="ffmpeg",
        path=path,
        source="test",
        version="ffmpeg test",
        error_code=None,
        error_message=None,
    )
