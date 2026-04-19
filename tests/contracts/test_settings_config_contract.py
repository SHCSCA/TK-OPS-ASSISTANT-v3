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


def test_validation_failures_use_error_envelope(runtime_client: TestClient) -> None:
    response = runtime_client.put("/api/settings/config", json={"runtime": {}})

    assert response.status_code == 422
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error"] == "请求参数校验失败"
    assert payload["requestId"]
    assert payload["details"]


def test_runtime_logs_contract_envelope_and_schema(runtime_client: TestClient) -> None:
    response = runtime_client.get("/api/settings/logs", params={"limit": 3})

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert set(payload) == {"ok", "data"}
    assert set(payload["data"]) == {"items", "nextCursor"}
