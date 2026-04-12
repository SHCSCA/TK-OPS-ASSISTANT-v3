from __future__ import annotations

from fastapi.testclient import TestClient

def test_settings_health_returns_runtime_snapshot(runtime_client: TestClient) -> None:
    client = runtime_client

    response = client.get("/api/settings/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["service"] == "online"
    assert payload["data"]["version"]
    assert payload["data"]["now"]
    assert payload["data"]["mode"] == "test"


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
