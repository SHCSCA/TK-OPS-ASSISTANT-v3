from __future__ import annotations

import zipfile
from fastapi.testclient import TestClient
from pathlib import Path

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


def test_settings_health_allows_desktop_origins(runtime_client: TestClient) -> None:
    browser_response = runtime_client.get(
        "/api/settings/health",
        headers={"Origin": "http://127.0.0.1:1420"},
    )
    tauri_response = runtime_client.get(
        "/api/settings/health",
        headers={"Origin": "tauri://localhost"},
    )

    assert browser_response.status_code == 200
    assert (
        browser_response.headers.get("access-control-allow-origin")
        == "http://127.0.0.1:1420"
    )
    assert tauri_response.status_code == 200
    assert tauri_response.headers.get("access-control-allow-origin") == "tauri://localhost"
