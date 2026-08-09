from __future__ import annotations

from fastapi.testclient import TestClient

def test_health_contract_uses_settings_prefix_and_json_envelope(
    licensed_runtime_client: TestClient,
) -> None:
    client = licensed_runtime_client

    response = client.get("/api/settings/health")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"ok", "data"}
    assert payload["ok"] is True
    assert set(payload["data"]) == {
        "runtime",
        "taskBus",
        "license",
        "lastSyncAt",
        "service",
        "version",
        "now",
        "mode",
        "unavailableSections",
    }
    assert payload["data"]["unavailableSections"] == [
        "aiProvider",
        "renderQueue",
        "publishingQueue",
    ]


def test_legacy_logs_collection_requires_v1_log_lookup(
    licensed_runtime_client: TestClient,
) -> None:
    response = licensed_runtime_client.get(
        "/api/settings/logs",
        params={"limit": 5, "kind": "system", "level": "INFO"},
    )

    assert response.status_code == 410
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error_code"] == "legacy.write.unsupported"


def test_legacy_diagnostics_export_requires_controlled_tauri_export(
    licensed_runtime_client: TestClient,
) -> None:
    response = licensed_runtime_client.post("/api/settings/diagnostics/export")

    assert response.status_code == 410
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error_code"] == "legacy.write.unsupported"


def test_media_diagnostics_contract_uses_settings_prefix_and_expected_shape(
    licensed_runtime_client: TestClient,
) -> None:
    response = licensed_runtime_client.get("/api/settings/diagnostics/media")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"ok", "data"}
    assert payload["ok"] is True
    assert set(payload["data"]) == {"ffprobe", "ffmpeg", "checkedAt"}
    expected_tool_fields = {
        "status",
        "path",
        "source",
        "version",
        "errorCode",
        "errorMessage",
    }
    assert set(payload["data"]["ffprobe"]) == expected_tool_fields
    assert set(payload["data"]["ffmpeg"]) == expected_tool_fields
