from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.config import load_runtime_config


def test_settings_health_returns_runtime_snapshot(
    licensed_runtime_client: TestClient,
) -> None:
    client = licensed_runtime_client

    response = client.get("/api/settings/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    data = payload["data"]
    assert data["service"] == "ready"
    assert set(data["runtime"]) == {"status", "port", "uptimeMs", "version"}
    assert set(data["taskBus"]) == {"running", "queued", "blocked", "failed24h"}
    assert set(data["license"]) == {"status", "expiresAt"}
    assert data["unavailableSections"] == [
        "aiProvider",
        "renderQueue",
        "publishingQueue",
    ]
    assert payload["data"]["version"]
    assert payload["data"]["now"]
    assert payload["data"]["mode"] == "test"


def test_settings_logs_collection_is_retired(
    licensed_runtime_client: TestClient,
) -> None:
    response = licensed_runtime_client.get(
        "/api/settings/logs",
        params={"since": "2020-01-01T00:00:00Z", "limit": 2},
    )

    assert response.status_code == 410
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error_code"] == "legacy.write.unsupported"


def test_settings_logs_does_not_reintroduce_legacy_query_validation(
    licensed_runtime_client: TestClient,
) -> None:
    response = licensed_runtime_client.get(
        "/api/settings/logs",
        params={"since": "not-a-time"},
    )

    assert response.status_code == 410
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error_code"] == "legacy.write.unsupported"


def test_settings_diagnostics_export_is_restricted_to_tauri(
    licensed_runtime_client: TestClient,
) -> None:
    response = licensed_runtime_client.post("/api/settings/diagnostics/export")

    assert response.status_code == 410
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error_code"] == "legacy.write.unsupported"


def test_settings_media_diagnostics_reports_ffprobe_state(
    licensed_runtime_client: TestClient,
) -> None:
    response = licensed_runtime_client.get("/api/settings/diagnostics/media")

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
    licensed_runtime_client: TestClient,
    runtime_data_dir: Path,
) -> None:
    current = licensed_runtime_client.get("/api/settings/config").json()["data"]
    current["media"]["ffmpegPath"] = str(runtime_data_dir / "missing" / "ffmpeg.exe")
    update_response = licensed_runtime_client.put(
        "/api/settings/config",
        json=current,
    )
    assert update_response.status_code == 200

    response = licensed_runtime_client.get("/api/settings/diagnostics/media")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["ffmpeg"]["status"] != "ready"
    assert payload["data"]["ffmpeg"]["path"] is None


def test_settings_health_allows_desktop_origins(
    licensed_runtime_client: TestClient,
) -> None:
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
        response = licensed_runtime_client.get(
            "/api/settings/health",
            headers={"Origin": origin},
        )

        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == origin

    preflight_response = licensed_runtime_client.options(
        "/api/settings/config",
        headers={
            "Origin": "http://127.0.0.1:5174",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    blocked_response = licensed_runtime_client.get(
        "/api/settings/health",
        headers={"Origin": "http://evil.example"},
    )

    assert preflight_response.status_code == 200
    assert (
        preflight_response.headers.get("access-control-allow-origin")
        == "http://127.0.0.1:5174"
    )
    assert "GET" in preflight_response.headers.get("access-control-allow-methods", "")
    assert blocked_response.status_code == 403
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


def test_settings_health_does_not_expose_unmigrated_ai_provider_snapshot(
    runtime_app,
    licensed_runtime_client: TestClient,
) -> None:
    runtime_app.state.ai_capability_service.refresh_provider_health()

    response = licensed_runtime_client.get("/api/settings/health")

    assert response.status_code == 200
    payload = response.json()["data"]
    assert "aiProvider" not in payload
    assert "aiProvider" in payload["unavailableSections"]


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
    refreshed: list[object] = []

    async def fake_refresh_provider_health(
        container,
        *,
        blocking_cancel_grace_seconds: float,
    ) -> None:
        assert blocking_cancel_grace_seconds > 0
        refreshed.append(container)

    monkeypatch.setattr(
        "app.factory._refresh_provider_health",
        fake_refresh_provider_health,
    )

    with TestClient(runtime_app):
        pass

    assert refreshed == []


def test_runtime_lifespan_schedules_ai_provider_refresh_outside_test_mode(
    runtime_data_dir,
    monkeypatch,
) -> None:
    monkeypatch.setenv("TK_OPS_RUNTIME_MODE", "dev")

    from app.factory import create_app

    refreshed: list[object] = []

    async def fake_refresh_provider_health(
        container,
        *,
        blocking_cancel_grace_seconds: float,
    ) -> None:
        assert blocking_cancel_grace_seconds > 0
        refreshed.append(container)

    monkeypatch.setattr(
        "app.factory._refresh_provider_health",
        fake_refresh_provider_health,
    )

    with TestClient(create_app()):
        pass

    assert len(refreshed) == 1
