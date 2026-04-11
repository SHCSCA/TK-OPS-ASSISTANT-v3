from __future__ import annotations

from fastapi.testclient import TestClient

from main import app


def test_health_contract_uses_settings_prefix_and_json_envelope() -> None:
    client = TestClient(app)

    response = client.get("/api/settings/health")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"ok", "data"}
    assert payload["ok"] is True
    assert set(payload["data"]) == {"service", "version", "now", "mode"}
