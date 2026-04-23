from __future__ import annotations

from fastapi.testclient import TestClient


def test_settings_config_update_broadcasts_config_changed_event(
    runtime_client: TestClient,
    monkeypatch,
) -> None:
    captured: list[dict[str, object]] = []

    async def fake_broadcast(message: dict[str, object]) -> None:
        event = dict(message)
        event.setdefault("schema_version", 1)
        captured.append(event)

    monkeypatch.setattr("services.settings_service.ws_manager.broadcast", fake_broadcast)

    current_response = runtime_client.get("/api/settings/config")
    assert current_response.status_code == 200
    current = current_response.json()["data"]
    current["ai"]["model"] = "gpt-5.4-contract"

    response = runtime_client.put("/api/settings/config", json=current)

    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert captured
    event = captured[-1]
    assert event["schema_version"] == 1
    assert event["type"] == "config.changed"
    assert event["scope"] == "runtime_local"
    assert event["revision"] == 2
    assert event["updatedAt"]
    assert event["changedKeys"] == ["ai"]


def test_config_contract_uses_settings_prefix_and_expected_document_shape(
    runtime_client: TestClient,
) -> None:
    response = runtime_client.get("/api/settings/config")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"ok", "data"}
    assert payload["ok"] is True
    assert set(payload["data"]) == {"revision", "scope", "runtime", "paths", "logging", "ai"}
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
        "configScope",
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
