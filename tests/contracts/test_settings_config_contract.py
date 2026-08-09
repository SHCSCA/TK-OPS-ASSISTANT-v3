from __future__ import annotations

from fastapi.testclient import TestClient


def test_legacy_settings_rejects_ai_configuration_writes(
    licensed_runtime_client: TestClient,
) -> None:
    current_response = licensed_runtime_client.get("/api/settings/config")
    assert current_response.status_code == 200
    current = current_response.json()["data"]
    current["ai"]["model"] = "gpt-5.4-contract"

    response = licensed_runtime_client.put("/api/settings/config", json=current)

    assert response.status_code == 410
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error_code"] == "legacy.write.unsupported"


def test_config_contract_uses_settings_prefix_and_expected_document_shape(
    licensed_runtime_client: TestClient,
) -> None:
    response = licensed_runtime_client.get("/api/settings/config")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"ok", "data"}
    assert payload["ok"] is True
    assert set(payload["data"]) == {
        "revision",
        "scope",
        "runtime",
        "paths",
        "logging",
        "ai",
        "media",
        "browser",
    }
    assert set(payload["data"]["runtime"]) == {"mode", "workspaceRoot"}
    assert set(payload["data"]["paths"]) == {"cacheDir", "exportDir", "logDir"}
    assert set(payload["data"]["logging"]) == {"level"}
    assert set(payload["data"]["ai"]) == {
        "provider",
        "model",
        "voice",
        "subtitleMode",
    }
    assert set(payload["data"]["media"]) == {"ffprobePath", "ffmpegPath"}
    assert set(payload["data"]["browser"]) == {"executablePath"}
    assert payload["data"]["browser"]["executablePath"] == ""


def test_diagnostics_contract_exposes_non_sensitive_fields_only(
    licensed_runtime_client: TestClient,
) -> None:
    response = licensed_runtime_client.get("/api/settings/diagnostics")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"ok", "data"}
    assert payload["ok"] is True
    assert {
        "databasePath",
        "cacheDir",
        "logDir",
        "revision",
        "mode",
        "healthStatus",
        "configScope",
        "checkedAt",
        "overallStatus",
        "items",
    } <= set(payload["data"])


def test_validation_failures_use_error_envelope(
    licensed_runtime_client: TestClient,
) -> None:
    response = licensed_runtime_client.put(
        "/api/settings/config",
        json={"runtime": {}},
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error"] == "请求参数校验失败"
    assert payload["requestId"]
    assert payload["details"]


def test_runtime_logs_contract_envelope_and_schema(
    licensed_runtime_client: TestClient,
) -> None:
    response = licensed_runtime_client.get(
        "/api/settings/logs",
        params={"limit": 3},
    )

    assert response.status_code == 410
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error_code"] == "legacy.write.unsupported"
