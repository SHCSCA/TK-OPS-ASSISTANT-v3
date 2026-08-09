from __future__ import annotations

from fastapi.testclient import TestClient


def test_settings_diagnostics_returns_system_check_report(
    monkeypatch,
    licensed_runtime_client: TestClient,
) -> None:
    monkeypatch.setattr(
        "services.diagnostics.runtime_diagnostics_service.resolve_ffprobe",
        lambda **_: type(
            "FfprobeAvailabilityStub",
            (),
            {
                "status": "ready",
                "source": "bundled",
                "error_code": None,
            },
        )(),
    )

    response = licensed_runtime_client.get("/api/settings/diagnostics")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    data = payload["data"]
    assert data["overallStatus"] in {"ready", "warning"}
    assert data["checkedAt"]
    assert data["databasePath"] == ""
    assert {item["id"] for item in data["items"]} == {
        "runtime.status",
        "database.schema",
        "directories.status",
        "media-tools.status",
    }
    media_item = next(
        item for item in data["items"] if item["id"] == "media-tools.status"
    )
    assert media_item["status"] in {"ready", "warning"}


def test_settings_diagnostics_marks_ffprobe_warning_when_tool_is_missing(
    monkeypatch,
    licensed_runtime_client: TestClient,
) -> None:
    monkeypatch.setattr(
        "services.diagnostics.runtime_diagnostics_service.resolve_ffprobe",
        lambda **_: type(
            "FfprobeAvailabilityStub",
            (),
            {
                "status": "unavailable",
                "source": "fallback",
                "error_code": "media.ffprobe_unavailable",
            },
        )(),
    )

    response = licensed_runtime_client.get("/api/settings/diagnostics")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["overallStatus"] == "warning"
    media_item = next(
        item for item in data["items"] if item["id"] == "media-tools.status"
    )
    assert media_item["status"] == "warning"
    assert media_item["actionLabel"] == "重新检测"


def test_legacy_ai_capability_write_is_retired_for_unconnected_provider(
    runtime_client: TestClient,
) -> None:
    settings_response = runtime_client.get("/api/settings/ai-capabilities")
    capabilities = settings_response.json()["data"]["capabilities"]
    for item in capabilities:
        if item["capabilityId"] == "video_transcription":
            item.update(
                {
                    "enabled": True,
                    "provider": "volcengine_asr",
                    "model": "volcengine-asr",
                }
            )

    update_response = runtime_client.put(
        "/api/settings/ai-capabilities",
        json={"capabilities": capabilities},
    )
    assert update_response.status_code == 410
    payload = update_response.json()
    assert payload["ok"] is False
    assert payload["error_code"] == "legacy.write.unsupported"


def test_legacy_ai_capability_and_secret_writes_are_retired(
    licensed_runtime_client: TestClient,
) -> None:
    settings_response = licensed_runtime_client.get("/api/settings/ai-capabilities")
    capabilities = settings_response.json()["data"]["capabilities"]
    for item in capabilities:
        if item["capabilityId"] == "asset_analysis":
            item["enabled"] = False
        if item["capabilityId"] == "video_transcription":
            item.update(
                {
                    "enabled": True,
                    "provider": "volcengine",
                    "model": "doubao-seed-2.0-pro",
                }
            )

    update_response = licensed_runtime_client.put(
        "/api/settings/ai-capabilities",
        json={"capabilities": capabilities},
    )
    assert update_response.status_code == 410
    assert update_response.json()["error_code"] == "legacy.write.unsupported"
    secret_response = licensed_runtime_client.put(
        "/api/settings/ai-capabilities/providers/volcengine/secret",
        json={"apiKey": "sk-test", "baseUrl": "https://ark.cn-beijing.volces.com/api/v3"},
    )
    assert secret_response.status_code == 410
    assert secret_response.json()["error_code"] == "legacy.write.unsupported"
