from __future__ import annotations

import base64
import json
from datetime import UTC, datetime
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient

from services.license_activation import OfflineLicenseActivationAdapter


def _base64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _issue_activation_code(machine_code: str, private_key: Ed25519PrivateKey) -> str:
    payload = {
        "machineCode": machine_code,
        "licenseType": "perpetual",
        "issuedAt": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "version": 1,
    }
    payload_bytes = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    signature = private_key.sign(payload_bytes)
    return f"{_base64url(payload_bytes)}.{_base64url(signature)}"


def _configure_license_keys(
    runtime_data_dir: Path,
    monkeypatch,
    *,
    machine_code: str = "TKOPS-TEST1-TEST2-TEST3-TEST4-TEST5",
) -> None:
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    public_key_path = runtime_data_dir / "license-public.pem"
    public_key_path.write_bytes(
        public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    monkeypatch.setenv("TK_OPS_LICENSE_PUBLIC_KEY_PATH", str(public_key_path))
    monkeypatch.setenv("TK_OPS_MACHINE_CODE_OVERRIDE", machine_code)
    return private_key


def test_license_status_returns_default_restricted_state(
    runtime_client: TestClient,
) -> None:
    response = runtime_client.get("/api/license/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["active"] is False
    assert payload["data"]["restrictedMode"] is True
    assert payload["data"]["machineCode"]
    assert payload["data"]["machineBound"] is False
    assert payload["data"]["licenseType"] == "perpetual"
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
    assert second_payload["data"]["machineCode"] == first_payload["data"]["machineCode"]
    assert second_payload["data"]["active"] is False


def test_license_activate_persists_grant_across_app_recreation(
    runtime_data_dir: Path,
    monkeypatch,
) -> None:
    private_key = _configure_license_keys(runtime_data_dir, monkeypatch)
    from app.factory import create_app

    client = TestClient(create_app())
    machine_code = client.get("/api/license/status").json()["data"]["machineCode"]
    activation_code = _issue_activation_code(machine_code, private_key)

    activate_response = client.post(
        "/api/license/activate",
        json={"activationCode": activation_code},
    )

    assert activate_response.status_code == 200
    activated = activate_response.json()
    assert activated["ok"] is True
    assert activated["data"]["active"] is True
    assert activated["data"]["restrictedMode"] is False
    assert activated["data"]["machineBound"] is True
    assert activated["data"]["licenseType"] == "perpetual"
    assert activated["data"]["maskedCode"].startswith(activation_code[:4])
    assert activated["data"]["activatedAt"]

    from app.factory import create_app

    reloaded_client = TestClient(create_app())
    read_response = reloaded_client.get("/api/license/status")

    assert read_response.status_code == 200
    payload = read_response.json()
    assert payload["data"]["active"] is True
    assert payload["data"]["restrictedMode"] is False
    assert payload["data"]["machineBound"] is True
    assert payload["data"]["licenseType"] == "perpetual"


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


def test_license_activation_rejects_machine_code_mismatch(
    runtime_data_dir: Path,
    monkeypatch,
) -> None:
    private_key = _configure_license_keys(runtime_data_dir, monkeypatch)
    from app.factory import create_app

    client = TestClient(create_app())

    response = client.post(
        "/api/license/activate",
        json={
            "activationCode": _issue_activation_code(
                "TKOPS-OTHER1-OTHER2-OTHER3-OTHER4-OTHER5",
                private_key,
            )
        },
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error"] == "机器码不匹配"
    assert payload["requestId"]


def test_offline_activation_accepts_case_insensitive_machine_code(tmp_path: Path) -> None:
    private_key = Ed25519PrivateKey.generate()
    public_key_path = tmp_path / "license-public.pem"
    public_key_path.write_bytes(
        private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    activation_code = _issue_activation_code(
        "97792E0167B449ACBF1D9BB1FD3E9B41",
        private_key,
    )

    result = OfflineLicenseActivationAdapter(public_key_path).activate(
        activation_code,
        machine_code="97792e0167b449acbf1d9bb1fd3e9b41",
    )

    assert result.license_type == "perpetual"


def test_license_activation_rejects_invalid_signature(
    runtime_data_dir: Path,
    monkeypatch,
) -> None:
    private_key = _configure_license_keys(runtime_data_dir, monkeypatch)
    from app.factory import create_app

    client = TestClient(create_app())
    machine_code = client.get("/api/license/status").json()["data"]["machineCode"]
    invalid_code = _issue_activation_code(machine_code, Ed25519PrivateKey.generate())

    response = client.post("/api/license/activate", json={"activationCode": invalid_code})

    assert response.status_code == 400
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error"] == "签名校验失败"
    assert payload["requestId"]


def test_license_events_write_structured_audit_logs(
    runtime_data_dir: Path,
    monkeypatch,
) -> None:
    private_key = _configure_license_keys(runtime_data_dir, monkeypatch)
    from app.factory import create_app

    client = TestClient(create_app())

    status_response = client.get("/api/license/status")
    machine_code = status_response.json()["data"]["machineCode"]
    activate_response = client.post(
        "/api/license/activate",
        json={"activationCode": _issue_activation_code(machine_code, private_key)},
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
