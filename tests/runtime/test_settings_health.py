from __future__ import annotations

import asyncio
from pathlib import Path

import zipfile
from fastapi.testclient import TestClient

from app.config import load_runtime_config


def test_settings_health_returns_runtime_snapshot(runtime_client: TestClient) -> None:
    client = runtime_client

    response = client.get("/api/settings/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    data = payload["data"]
    assert data["service"] == "online"
    assert set(data["runtime"]) == {"status", "port", "uptimeMs", "version"}
    assert set(data["aiProvider"]) == {"status", "latencyMs", "providerId", "providerName", "lastChecked"}
    assert set(data["renderQueue"]) == {"running", "queued", "avgWaitMs"}
    assert set(data["publishingQueue"]) == {"pendingToday", "failedToday"}
    assert set(data["taskBus"]) == {"running", "queued", "blocked", "failed24h"}
    assert set(data["license"]) == {"status", "expiresAt"}
    assert payload["data"]["version"]
    assert payload["data"]["now"]
    assert payload["data"]["mode"] == "test"


def test_settings_logs_supports_since_filter(runtime_client: TestClient) -> None:
    response = runtime_client.get(
        "/api/settings/logs",
        params={"since": "2020-01-01T00:00:00Z", "limit": 2},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert isinstance(payload["data"]["items"], list)


def test_settings_logs_rejects_bad_since(runtime_client: TestClient) -> None:
    response = runtime_client.get("/api/settings/logs", params={"since": "not-a-time"})

    assert response.status_code == 422
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error"] == "请求参数校验失败"


def test_settings_diagnostics_export_creates_local_zip(runtime_client: TestClient) -> None:
    response = runtime_client.post("/api/settings/diagnostics/export")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    path = Path(payload["data"]["bundlePath"])
    assert path.exists()
    with zipfile.ZipFile(path) as archive:
        assert "settings.json" in archive.namelist()
        assert "health.json" in archive.namelist()
        assert "diagnostics.json" in archive.namelist()


def test_settings_media_diagnostics_reports_ffprobe_state(runtime_app) -> None:
    client = TestClient(runtime_app)

    response = client.get("/api/settings/diagnostics/media")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert set(payload["data"]) == {"ffprobe", "ffmpeg", "checkedAt"}
    assert set(payload["data"]["ffprobe"]) == {
        "status",
        "path",
        "source",
        "version",
        "errorCode",
        "errorMessage",
    }
    assert set(payload["data"]["ffmpeg"]) == {
        "status",
        "path",
        "source",
        "version",
        "errorCode",
        "errorMessage",
    }


def test_settings_diagnostics_reports_invalid_ffmpeg_config_without_500(
    runtime_app,
    runtime_data_dir: Path,
) -> None:
    client = TestClient(runtime_app)
    current = client.get("/api/settings/config").json()["data"]
    current["media"]["ffmpegPath"] = str(runtime_data_dir / "missing" / "ffmpeg.exe")
    update_response = client.put("/api/settings/config", json=current)
    assert update_response.status_code == 200

    response = client.get("/api/settings/diagnostics")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    ffmpeg_item = next(
        item for item in payload["data"]["items"] if item["id"] == "media.ffmpeg"
    )
    assert ffmpeg_item["status"] == "failed"
    assert "FFmpeg" in ffmpeg_item["summary"]


def test_settings_health_allows_desktop_origins(runtime_client: TestClient) -> None:
    allowed_origins = [
        "http://127.0.0.1:1420",
        "http://localhost:1420",
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:5174",
        "http://localhost:5174",
        "tauri://localhost",
        "http://tauri.localhost",
    ]

    for origin in allowed_origins:
        response = runtime_client.get(
            "/api/settings/health",
            headers={"Origin": origin},
        )

        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == origin

    preflight_response = runtime_client.options(
        "/api/settings/config",
        headers={
            "Origin": "http://127.0.0.1:5174",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    blocked_response = runtime_client.get(
        "/api/settings/health",
        headers={"Origin": "http://evil.example"},
    )

    assert preflight_response.status_code == 200
    assert (
        preflight_response.headers.get("access-control-allow-origin")
        == "http://127.0.0.1:5174"
    )
    assert "GET" in preflight_response.headers.get("access-control-allow-methods", "")
    assert blocked_response.status_code == 200
    assert blocked_response.headers.get("access-control-allow-origin") is None


def test_runtime_config_loads_extra_allowed_origins(
    monkeypatch,
    runtime_data_dir: Path,
) -> None:
    monkeypatch.setenv(
        "TK_OPS_RUNTIME_ALLOWED_ORIGINS",
        "http://127.0.0.1:6006, http://127.0.0.1:5174",
    )

    config = load_runtime_config()

    assert "http://127.0.0.1:6006" in config.allowed_origins
    assert config.allowed_origins.count("http://127.0.0.1:5174") == 1


def test_runtime_config_reads_legacy_allowed_origins(
    monkeypatch,
    runtime_data_dir: Path,
) -> None:
    monkeypatch.setenv("TK_OPS_ALLOWED_ORIGINS", "http://127.0.0.1:7007")

    config = load_runtime_config()

    assert "http://127.0.0.1:7007" in config.allowed_origins


def test_runtime_config_rejects_unsafe_allowed_origins(
    monkeypatch,
    runtime_data_dir: Path,
) -> None:
    monkeypatch.setenv(
        "TK_OPS_RUNTIME_ALLOWED_ORIGINS",
        "*, http://127.0.0.1:6006/path, http://127.0.0.1:6007?x=1",
    )
    monkeypatch.setenv("TK_OPS_ALLOWED_ORIGINS", "http://127.0.0.1:6008#debug")

    config = load_runtime_config()

    assert "*" not in config.allowed_origins
    assert "http://127.0.0.1:6006/path" not in config.allowed_origins
    assert "http://127.0.0.1:6007?x=1" not in config.allowed_origins
    assert "http://127.0.0.1:6008#debug" not in config.allowed_origins


def test_settings_health_reads_real_ai_provider_snapshot(runtime_app) -> None:
    runtime_app.state.ai_capability_service.refresh_provider_health()
    client = TestClient(runtime_app)

    response = client.get("/api/settings/health")

    assert response.status_code == 200
    payload = response.json()["data"]["aiProvider"]
    assert payload["providerId"] == "openai"
    assert payload["status"] in {
        "not_configured",
        "missing_secret",
        "ready",
        "offline",
        "refresh_failed",
        "unsupported",
    }


def test_provider_health_refresh_emits_ai_capability_changed_event(runtime_app) -> None:
    captured: list[dict[str, object]] = []

    async def fake_broadcast(message: dict[str, object]) -> None:
        event = dict(message)
        event.setdefault("schema_version", 1)
        captured.append(event)

    from services import ai_capability_service as ai_capability_service_module

    original_broadcast = ai_capability_service_module.ws_manager.broadcast
    ai_capability_service_module.ws_manager.broadcast = fake_broadcast
    try:
        runtime_app.state.ai_capability_service.refresh_provider_health()
    finally:
        ai_capability_service_module.ws_manager.broadcast = original_broadcast

    assert captured
    event = captured[-1]
    assert event["schema_version"] == 1
    assert event["type"] == "ai-capability.changed"
    assert event["reason"] == "provider_health_refreshed"
    assert event["scope"] == "runtime_local"
    assert event["providerIds"]
    assert set(event["capabilityIds"]) == {
        "script_generation",
        "script_rewrite",
        "storyboard_generation",
        "tts_generation",
        "subtitle_alignment",
        "video_transcription",
        "video_generation",
        "asset_analysis",
        "magic_cut",
    }


def test_runtime_lifespan_skips_ai_provider_refresh_in_test_mode(
    runtime_app,
    monkeypatch,
) -> None:
    scheduled: list[object] = []

    def fake_create_task(coro):
        scheduled.append(coro)
        coro.close()
        return object()

    monkeypatch.setattr(asyncio, "create_task", fake_create_task)

    with TestClient(runtime_app):
        pass

    assert scheduled == []


def test_runtime_lifespan_schedules_ai_provider_refresh_outside_test_mode(
    runtime_data_dir,
    monkeypatch,
) -> None:
    monkeypatch.setenv("TK_OPS_RUNTIME_MODE", "dev")

    from app.factory import create_app

    scheduled: list[object] = []

    def fake_create_task(coro):
        scheduled.append(coro)
        coro.close()
        return object()

    monkeypatch.setattr(asyncio, "create_task", fake_create_task)

    with TestClient(create_app()):
        pass

    assert len(scheduled) == 1
