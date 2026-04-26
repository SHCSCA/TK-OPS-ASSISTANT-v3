from __future__ import annotations

import json
from pathlib import Path

from fastapi import Request
from fastapi.testclient import TestClient


def test_settings_config_returns_default_document(
    runtime_client: TestClient,
) -> None:
    response = runtime_client.get("/api/settings/config")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["revision"] == 1
    assert payload["data"]["scope"] == "runtime_local"
    assert payload["data"]["runtime"]["mode"] == "test"
    assert payload["data"]["runtime"]["workspaceRoot"]
    assert payload["data"]["paths"]["cacheDir"]
    assert payload["data"]["paths"]["exportDir"]
    assert payload["data"]["paths"]["logDir"]
    assert payload["data"]["logging"]["level"] == "INFO"
    assert payload["data"]["ai"] == {
        "provider": "openai",
        "model": "gpt-5.4",
        "voice": "alloy",
        "subtitleMode": "balanced",
    }
    assert payload["data"]["media"] == {"ffprobePath": ""}


def test_settings_config_update_persists_across_app_recreation(
    runtime_app,
    runtime_data_dir: Path,
) -> None:
    client = TestClient(runtime_app)
    update_payload = {
        "runtime": {
            "mode": "production",
            "workspaceRoot": str(runtime_data_dir / "workspace"),
        },
        "paths": {
            "cacheDir": str(runtime_data_dir / "cache-next"),
            "exportDir": str(runtime_data_dir / "exports-next"),
            "logDir": str(runtime_data_dir / "logs-next"),
        },
        "logging": {"level": "DEBUG"},
        "ai": {
            "provider": "openai",
            "model": "gpt-5.4-mini",
            "voice": "nova",
            "subtitleMode": "precise",
        },
        "media": {
            "ffprobePath": str(runtime_data_dir / "tools" / "ffprobe.exe"),
        },
    }

    write_response = client.put("/api/settings/config", json=update_payload)

    assert write_response.status_code == 200
    written = write_response.json()
    assert written["ok"] is True
    assert written["data"]["revision"] == 2
    assert written["data"]["scope"] == "runtime_local"
    assert written["data"]["runtime"]["mode"] == "production"
    assert written["data"]["logging"]["level"] == "DEBUG"
    assert written["data"]["ai"]["model"] == "gpt-5.4-mini"
    assert written["data"]["media"]["ffprobePath"].endswith("ffprobe.exe")

    from app.factory import create_app

    reloaded_client = TestClient(create_app())
    read_response = reloaded_client.get("/api/settings/config")

    assert read_response.status_code == 200
    payload = read_response.json()
    assert payload["data"]["revision"] == 2
    assert payload["data"]["runtime"]["workspaceRoot"] == str(
        runtime_data_dir / "workspace"
    )
    assert payload["data"]["paths"]["logDir"] == str(runtime_data_dir / "logs-next")
    assert payload["data"]["ai"]["voice"] == "nova"
    assert payload["data"]["media"]["ffprobePath"].endswith("ffprobe.exe")


def test_settings_config_update_broadcasts_config_changed_event(
    runtime_app,
    runtime_data_dir: Path,
) -> None:
    client = TestClient(runtime_app)
    captured: list[dict[str, object]] = []

    async def fake_broadcast(message: dict[str, object]) -> None:
        event = dict(message)
        event.setdefault("schema_version", 1)
        captured.append(event)

    from services import settings_service as settings_service_module

    original_broadcast = settings_service_module.ws_manager.broadcast
    settings_service_module.ws_manager.broadcast = fake_broadcast
    try:
        response = client.put(
            "/api/settings/config",
            json={
                "runtime": {
                    "mode": "test",
                    "workspaceRoot": str(runtime_data_dir / "workspace-broadcast"),
                },
                "paths": {
                    "cacheDir": str(runtime_data_dir / "cache-broadcast"),
                    "exportDir": str(runtime_data_dir / "exports-broadcast"),
                    "logDir": str(runtime_data_dir / "logs-broadcast"),
                },
                "logging": {"level": "INFO"},
                "ai": {
                    "provider": "openai",
                    "model": "gpt-5.4",
                    "voice": "alloy",
                    "subtitleMode": "balanced",
                },
                "media": {"ffprobePath": str(runtime_data_dir / "ffprobe.exe")},
            },
        )
    finally:
        settings_service_module.ws_manager.broadcast = original_broadcast

    assert response.status_code == 200
    assert captured
    event = captured[-1]
    assert event["schema_version"] == 1
    assert event["type"] == "config.changed"
    assert event["scope"] == "runtime_local"
    assert event["revision"] == 2
    assert event["updatedAt"]
    assert event["changedKeys"] == ["runtime", "paths", "media"]


def test_settings_diagnostics_returns_non_sensitive_runtime_details(
    runtime_client: TestClient,
    runtime_data_dir: Path,
) -> None:
    response = runtime_client.get("/api/settings/diagnostics")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    data = payload["data"]
    assert data["databasePath"] == str(runtime_data_dir / "runtime.db")
    assert data["cacheDir"] == str(runtime_data_dir / "cache")
    assert data["logDir"] == str(runtime_data_dir / "logs")
    assert data["revision"] == 1
    assert data["mode"] == "test"
    assert data["healthStatus"] == "online"
    assert data["configScope"] == "runtime_local"
    assert data["overallStatus"] in {"ready", "warning"}
    assert data["checkedAt"]
    assert data["items"]


def test_unhandled_runtime_errors_are_wrapped_with_request_id(
    runtime_app,
) -> None:
    @runtime_app.get("/api/testing/boom")
    def boom(_: Request) -> dict[str, str]:
        raise RuntimeError("boom")

    client = TestClient(runtime_app, raise_server_exceptions=False)
    response = client.get("/api/testing/boom")

    assert response.status_code == 500
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error"] == "系统内部错误，请稍后重试"
    assert payload["requestId"]
    assert "details" not in payload


def test_settings_update_writes_structured_audit_log(
    runtime_app,
    runtime_data_dir: Path,
) -> None:
    client = TestClient(runtime_app)

    response = client.put(
        "/api/settings/config",
        json={
            "runtime": {
                "mode": "test",
                "workspaceRoot": str(runtime_data_dir / "workspace"),
            },
            "paths": {
                "cacheDir": str(runtime_data_dir / "cache"),
                "exportDir": str(runtime_data_dir / "exports"),
                "logDir": str(runtime_data_dir / "logs"),
            },
            "logging": {"level": "INFO"},
            "ai": {
                "provider": "openai",
                "model": "gpt-5.4",
                "voice": "alloy",
                "subtitleMode": "balanced",
            },
            "media": {"ffprobePath": ""},
        },
    )

    assert response.status_code == 200

    log_path = runtime_data_dir / "logs" / "runtime.jsonl"
    assert log_path.exists()

    audit_entry = json.loads(log_path.read_text(encoding="utf-8").strip().splitlines()[-1])
    assert audit_entry["category"] == "audit"
    assert audit_entry["level"] == "INFO"
    assert audit_entry["requestId"]
    assert audit_entry["message"] == "settings.updated"
    assert audit_entry["context"]["revision"] == 2
