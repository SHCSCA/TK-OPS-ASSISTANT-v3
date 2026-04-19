from __future__ import annotations

from fastapi.testclient import TestClient
from pathlib import Path
import zipfile

def test_health_contract_uses_settings_prefix_and_json_envelope(
    runtime_client: TestClient,
) -> None:
    client = runtime_client

    response = client.get("/api/settings/health")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"ok", "data"}
    assert payload["ok"] is True
    assert set(payload["data"]) == {
        "runtime",
        "aiProvider",
        "renderQueue",
        "publishingQueue",
        "taskBus",
        "license",
        "lastSyncAt",
        "service",
        "version",
        "now",
        "mode",
    }


def test_logs_endpoint_supports_query_filter_and_pagination(
    runtime_client: TestClient,
) -> None:
    response = runtime_client.get(
        "/api/settings/logs",
        params={"limit": 5, "kind": "system", "level": "INFO"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert set(payload["data"]) == {"items", "nextCursor"}
    assert isinstance(payload["data"]["items"], list)


def test_diagnostics_export_contract_returns_zip_bundle(
    runtime_client: TestClient,
) -> None:
    response = runtime_client.post("/api/settings/diagnostics/export")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    data = payload["data"]
    assert set(data) == {"bundlePath", "createdAt", "entries"}
    assert Path(data["bundlePath"]).exists()
    with zipfile.ZipFile(data["bundlePath"]) as bundle:
        names = set(bundle.namelist())
        assert "settings.json" in names
        assert "health.json" in names
        assert "diagnostics.json" in names
