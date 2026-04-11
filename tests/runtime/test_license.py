from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient


def test_license_status_returns_default_restricted_state(
    runtime_client: TestClient,
) -> None:
    response = runtime_client.get("/api/license/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["active"] is False
    assert payload["data"]["restrictedMode"] is True
    assert payload["data"]["machineId"]
    assert payload["data"]["machineBound"] is False
    assert payload["data"]["activationMode"] == "placeholder"
    assert payload["data"]["maskedCode"] == ""
    assert payload["data"]["activatedAt"] is None


def test_license_status_persists_machine_id_across_app_recreation(
    runtime_app,
) -> None:
    client = TestClient(runtime_app)
    first_response = client.get("/api/license/status")

    assert first_response.status_code == 200
    first_payload = first_response.json()

    from app.factory import create_app

    reloaded_client = TestClient(create_app())
    second_response = reloaded_client.get("/api/license/status")

    assert second_response.status_code == 200
    second_payload = second_response.json()
    assert second_payload["data"]["machineId"] == first_payload["data"]["machineId"]
    assert second_payload["data"]["active"] is False


def test_license_activate_persists_grant_across_app_recreation(
    runtime_app,
) -> None:
    client = TestClient(runtime_app)

    activate_response = client.post(
        "/api/license/activate",
        json={"activationCode": "TK-OPS-2026-ALPHA-0001"},
    )

    assert activate_response.status_code == 200
    activated = activate_response.json()
    assert activated["ok"] is True
    assert activated["data"]["active"] is True
    assert activated["data"]["restrictedMode"] is False
    assert activated["data"]["machineBound"] is True
    assert activated["data"]["activationMode"] == "placeholder"
    assert activated["data"]["maskedCode"] == "TK-O****************0001"
    assert activated["data"]["activatedAt"]

    from app.factory import create_app

    reloaded_client = TestClient(create_app())
    read_response = reloaded_client.get("/api/license/status")

    assert read_response.status_code == 200
    payload = read_response.json()
    assert payload["data"]["active"] is True
    assert payload["data"]["restrictedMode"] is False
    assert payload["data"]["machineBound"] is True
    assert payload["data"]["maskedCode"] == "TK-O****************0001"


def test_license_activation_rejects_blank_code_with_error_envelope(
    runtime_client: TestClient,
) -> None:
    response = runtime_client.post("/api/license/activate", json={"activationCode": ""})

    assert response.status_code == 422
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error"] == "Request validation failed"
    assert payload["requestId"]
    assert payload["details"]


def test_license_events_write_structured_audit_logs(
    runtime_app,
    runtime_data_dir: Path,
) -> None:
    client = TestClient(runtime_app)

    status_response = client.get("/api/license/status")
    activate_response = client.post(
        "/api/license/activate",
        json={"activationCode": "TK-OPS-2026-ALPHA-0001"},
    )

    assert status_response.status_code == 200
    assert activate_response.status_code == 200

    log_path = runtime_data_dir / "logs" / "runtime.jsonl"
    assert log_path.exists()

    entries = [
        json.loads(line)
        for line in log_path.read_text(encoding="utf-8").strip().splitlines()
    ]
    messages = [entry["message"] for entry in entries if entry["category"] == "audit"]
    assert "license.status_loaded" in messages
    assert "license.activated" in messages
