from __future__ import annotations

from fastapi.testclient import TestClient


def test_config_contract_uses_settings_prefix_and_expected_document_shape(
    runtime_client: TestClient,
) -> None:
    response = runtime_client.get("/api/settings/config")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"ok", "data"}
    assert payload["ok"] is True
    assert set(payload["data"]) == {"revision", "runtime", "paths", "logging", "ai"}
    assert set(payload["data"]["runtime"]) == {"mode", "workspaceRoot"}
    assert set(payload["data"]["paths"]) == {"cacheDir", "exportDir", "logDir"}
    assert set(payload["data"]["logging"]) == {"level"}
    assert set(payload["data"]["ai"]) == {
        "provider",
        "model",
        "voice",
        "subtitleMode",
    }


def test_diagnostics_contract_exposes_non_sensitive_fields_only(
    runtime_client: TestClient,
) -> None:
    response = runtime_client.get("/api/settings/diagnostics")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"ok", "data"}
    assert payload["ok"] is True
    assert set(payload["data"]) == {
        "databasePath",
        "logDir",
        "revision",
        "mode",
        "healthStatus",
    }


def test_runtime_logs_contract_returns_log_page_shape(
    runtime_client: TestClient,
) -> None:
    current_config = runtime_client.get("/api/settings/config").json()["data"]
    update_payload = {
        "runtime": current_config["runtime"],
        "paths": current_config["paths"],
        "logging": current_config["logging"],
        "ai": current_config["ai"],
    }
    runtime_client.put("/api/settings/config", json=update_payload)

    response = runtime_client.get("/api/settings/logs", params={"kind": "audit"})

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"ok", "data"}
    assert payload["ok"] is True
    assert set(payload["data"]) == {"items", "nextCursor"}
    assert isinstance(payload["data"]["items"], list)
    assert payload["data"]["items"]
    assert set(payload["data"]["items"][0]) == {
        "timestamp",
        "level",
        "kind",
        "requestId",
        "message",
        "context",
    }


def test_diagnostics_export_contract_returns_bundle_metadata(
    runtime_client: TestClient,
) -> None:
    response = runtime_client.post("/api/settings/diagnostics/export")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"ok", "data"}
    assert payload["ok"] is True
    assert set(payload["data"]) == {"bundlePath", "createdAt", "entries"}
    assert isinstance(payload["data"]["entries"], list)
    assert payload["data"]["entries"]
    assert set(payload["data"]["entries"][0]) == {"name", "path", "sizeBytes"}


def test_validation_failures_use_error_envelope(runtime_client: TestClient) -> None:
    response = runtime_client.put("/api/settings/config", json={"runtime": {}})

    assert response.status_code == 422
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error"] == "Request validation failed"
    assert payload["requestId"]
    assert payload["details"]
