from __future__ import annotations

import json
from pathlib import Path

from fastapi import Request
from fastapi.testclient import TestClient
from schemas.v1.bootstrap import LicenseStatusDto

TEST_RUNTIME_BASE_URL = "http://127.0.0.1:43119"


def _active_license_status() -> LicenseStatusDto:
    return LicenseStatusDto(
        status="active",
        machineCode="TKOPS-ABCDE-FGHIJ-KLMNO-PQRST-TEST5",
        machineCodeMasked="TKOPS-…-TEST5",
        expiresAt=None,
        activatedAt="2026-07-26T00:00:00Z",
        blockingIssue=None,
        revision=1,
    )


def test_settings_config_returns_default_document(
    licensed_runtime_client: TestClient,
) -> None:
    response = licensed_runtime_client.get("/api/settings/config")

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
    assert payload["data"]["media"] == {"ffprobePath": "", "ffmpegPath": ""}


def test_settings_config_update_persists_across_app_recreation(
    licensed_runtime_client: TestClient,
    runtime_data_dir: Path,
    monkeypatch,
) -> None:
    update_payload = licensed_runtime_client.get(
        "/api/settings/config"
    ).json()["data"]
    update_payload["logging"]["level"] = "DEBUG"
    update_payload["media"] = {
        "ffprobePath": str(runtime_data_dir / "tools" / "ffprobe.exe"),
        "ffmpegPath": str(runtime_data_dir / "tools" / "ffmpeg.exe"),
    }

    write_response = licensed_runtime_client.put(
        "/api/settings/config",
        json=update_payload,
    )

    assert write_response.status_code == 200
    written = write_response.json()
    assert written["ok"] is True
    assert written["data"]["revision"] == 2
    assert written["data"]["scope"] == "runtime_local"
    assert written["data"]["runtime"]["mode"] == "test"
    assert written["data"]["logging"]["level"] == "DEBUG"
    assert written["data"]["ai"]["model"] == "gpt-5.4"
    assert written["data"]["media"]["ffprobePath"].endswith("ffprobe.exe")
    assert written["data"]["media"]["ffmpegPath"].endswith("ffmpeg.exe")

    from app.factory import create_app

    reloaded_app = create_app()
    monkeypatch.setattr(
        reloaded_app.state.bootstrap_v1_service,
        "get_license_status",
        lambda **_: _active_license_status(),
    )
    with TestClient(
        reloaded_app,
        base_url=TEST_RUNTIME_BASE_URL,
    ) as reloaded_client:
        read_response = reloaded_client.get("/api/settings/config")

        assert read_response.status_code == 200
        payload = read_response.json()
        assert payload["data"]["revision"] == 2
        assert payload["data"]["logging"]["level"] == "DEBUG"
        assert payload["data"]["ai"]["voice"] == "alloy"
        assert payload["data"]["media"]["ffprobePath"].endswith("ffprobe.exe")
        assert payload["data"]["media"]["ffmpegPath"].endswith("ffmpeg.exe")


def test_settings_config_update_writes_persistent_config_event(
    runtime_app,
    licensed_runtime_client: TestClient,
    runtime_data_dir: Path,
) -> None:
    captured: list[dict[str, object]] = []

    async def fake_broadcast(message: dict[str, object]) -> None:
        event = dict(message)
        event.setdefault("schema_version", 1)
        captured.append(event)

    from services import settings_service as settings_service_module

    original_broadcast = settings_service_module.ws_manager.broadcast
    settings_service_module.ws_manager.broadcast = fake_broadcast
    try:
        update_payload = licensed_runtime_client.get(
            "/api/settings/config"
        ).json()["data"]
        update_payload["logging"]["level"] = "DEBUG"
        update_payload["media"] = {
            "ffprobePath": str(runtime_data_dir / "ffprobe.exe"),
            "ffmpegPath": str(runtime_data_dir / "ffmpeg.exe"),
        }
        response = licensed_runtime_client.put(
            "/api/settings/config",
            json=update_payload,
        )
    finally:
        settings_service_module.ws_manager.broadcast = original_broadcast

    assert response.status_code == 200
    assert captured == []
    snapshot = runtime_app.state.runtime_event_repository.load_replay_snapshot(
        topic="system:config",
        last_event_id=None,
        after_sequence=0,
        limit=20,
    )
    event = next(
        item
        for item in snapshot.events_after_cursor
        if item.event_type == "config.changed"
    )
    assert event.revision == 2
    assert set(event.payload["changedKeys"]) == {
        "browser.executablePath",
        "logging.level",
        "media.ffmpegPath",
        "media.ffprobePath",
    }


def test_settings_diagnostics_returns_non_sensitive_runtime_details(
    licensed_runtime_client: TestClient,
) -> None:
    response = licensed_runtime_client.get("/api/settings/diagnostics")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    data = payload["data"]
    assert data["databasePath"] == ""
    assert data["cacheDir"] == ""
    assert data["logDir"] == ""
    assert data["revision"] == 1
    assert data["mode"] == "test"
    assert data["healthStatus"] == "ready"
    assert data["configScope"] == "runtime_local"
    assert data["overallStatus"] in {"ready", "warning"}
    assert data["checkedAt"]
    assert {item["id"] for item in data["items"]} == {
        "runtime.status",
        "database.schema",
        "directories.status",
        "media-tools.status",
    }


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
    licensed_runtime_client: TestClient,
    runtime_data_dir: Path,
) -> None:
    update_payload = licensed_runtime_client.get(
        "/api/settings/config"
    ).json()["data"]
    update_payload["logging"]["level"] = "DEBUG"
    response = licensed_runtime_client.put(
        "/api/settings/config",
        json=update_payload,
    )

    assert response.status_code == 200

    log_path = runtime_data_dir / "logs" / "runtime.jsonl"
    assert log_path.exists()

    entries = [
        json.loads(line)
        for line in log_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    audit_entry = next(
        entry
        for entry in reversed(entries)
        if entry["category"] == "audit" and entry["message"] == "config.updated"
    )
    assert audit_entry["category"] == "audit"
    assert audit_entry["level"] == "INFO"
    assert audit_entry["requestId"]
    assert audit_entry["message"] == "config.updated"
    assert audit_entry["context"]["revision"] == 2
