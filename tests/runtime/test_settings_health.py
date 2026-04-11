from __future__ import annotations

from fastapi.testclient import TestClient

from main import app


def test_settings_health_returns_runtime_snapshot() -> None:
    client = TestClient(app)

    response = client.get("/api/settings/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["service"] == "online"
    assert payload["data"]["version"]
    assert payload["data"]["now"]
    assert payload["data"]["mode"] == "development"
