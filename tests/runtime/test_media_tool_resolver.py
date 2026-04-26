from __future__ import annotations

from pathlib import Path

from services.media_tool_resolver import configure_ffprobe_path, resolve_ffprobe


def test_resolve_ffprobe_prefers_config_bus_path(
    monkeypatch,
    tmp_path: Path,
) -> None:
    configured = tmp_path / "config-bus" / "ffprobe.exe"
    configured.parent.mkdir(parents=True)
    configured.write_bytes(b"fake")
    env_path = tmp_path / "env" / "ffprobe.exe"
    env_path.parent.mkdir(parents=True)
    env_path.write_bytes(b"fake")

    monkeypatch.setenv("TK_OPS_FFPROBE_PATH", str(env_path))
    configure_ffprobe_path(str(configured))

    try:
        result = resolve_ffprobe(repo_root=tmp_path)
    finally:
        configure_ffprobe_path(None)

    assert result.status == "ready"
    assert result.source == "config"
    assert result.path == str(configured)


def test_resolve_ffprobe_accepts_configured_bin_directory(
    tmp_path: Path,
) -> None:
    configured_dir = tmp_path / "ffmpeg" / "bin"
    configured = configured_dir / "ffprobe.exe"
    configured_dir.mkdir(parents=True)
    configured.write_bytes(b"fake")

    configure_ffprobe_path(str(configured_dir))

    try:
        result = resolve_ffprobe(repo_root=tmp_path)
    finally:
        configure_ffprobe_path(None)

    assert result.status == "ready"
    assert result.source == "config"
    assert result.path == str(configured)


def test_resolve_ffprobe_prefers_configured_path(
    monkeypatch,
    tmp_path: Path,
) -> None:
    configured = tmp_path / "configured" / "ffprobe.exe"
    configured.parent.mkdir(parents=True)
    configured.write_bytes(b"fake")
    bundled = tmp_path / "resources" / "bin" / "ffprobe" / "windows-x64" / "ffprobe.exe"
    bundled.parent.mkdir(parents=True)
    bundled.write_bytes(b"fake")

    monkeypatch.setenv("TK_OPS_FFPROBE_PATH", str(configured))
    monkeypatch.setenv("TK_OPS_RESOURCE_DIR", str(tmp_path / "resources"))

    result = resolve_ffprobe(repo_root=tmp_path)

    assert result.status == "ready"
    assert result.source == "configured"
    assert result.path == str(configured)


def test_resolve_ffprobe_uses_bundled_resource_before_path(
    monkeypatch,
    tmp_path: Path,
) -> None:
    bundled = tmp_path / "resources" / "bin" / "ffprobe" / "windows-x64" / "ffprobe.exe"
    bundled.parent.mkdir(parents=True)
    bundled.write_bytes(b"fake")

    monkeypatch.delenv("TK_OPS_FFPROBE_PATH", raising=False)
    monkeypatch.setenv("TK_OPS_RESOURCE_DIR", str(tmp_path / "resources"))
    monkeypatch.setattr("services.media_tool_resolver.shutil.which", lambda _: "C:/tools/ffprobe.exe")

    result = resolve_ffprobe(repo_root=tmp_path)

    assert result.status == "ready"
    assert result.source == "bundled"
    assert result.path == str(bundled)


def test_resolve_ffprobe_reports_unavailable_when_no_candidate_exists(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("TK_OPS_FFPROBE_PATH", raising=False)
    monkeypatch.delenv("TK_OPS_RESOURCE_DIR", raising=False)
    monkeypatch.setattr("services.media_tool_resolver.shutil.which", lambda _: None)

    result = resolve_ffprobe(repo_root=tmp_path)

    assert result.status == "unavailable"
    assert result.source == "fallback"
    assert result.path is None
    assert result.error_code == "media.ffprobe_unavailable"
