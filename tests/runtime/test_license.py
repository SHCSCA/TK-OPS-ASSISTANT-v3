from __future__ import annotations

import base64
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

LEGACY_RUNTIME_BASE_URL = "http://127.0.0.1:43119"
TEST_MACHINE_CODE = "TKOPS-TEST1-TEST2-TEST3-TEST4-TEST5"

try:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from services.license_activation import OfflineLicenseActivationAdapter

    HAS_CRYPTOGRAPHY = True
except ModuleNotFoundError:
    serialization = None  # type: ignore[assignment]
    Ed25519PrivateKey = Any  # type: ignore[assignment]
    OfflineLicenseActivationAdapter = None  # type: ignore[assignment]
    HAS_CRYPTOGRAPHY = False


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
    machine_code: str = TEST_MACHINE_CODE,
) -> Ed25519PrivateKey:
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
    status = payload["data"]
    assert status["active"] is False
    assert status["restrictedMode"] is True
    assert status["machineCode"]
    assert status["machineCode"] == status["maskedCode"]
    assert "*" in status["machineCode"]
    assert status["machineBound"] is False
    assert status["licenseType"] == "local_device"
    assert status["activatedAt"] is None


def test_license_status_persists_machine_id_across_app_recreation(
    runtime_app,
) -> None:
    client = TestClient(runtime_app, base_url=LEGACY_RUNTIME_BASE_URL)
    first_response = client.get("/api/license/status")

    assert first_response.status_code == 200
    first_payload = first_response.json()

    from app.factory import create_app

    reloaded_client = TestClient(
        create_app(),
        base_url=LEGACY_RUNTIME_BASE_URL,
    )
    second_response = reloaded_client.get("/api/license/status")

    assert second_response.status_code == 200
    second_payload = second_response.json()
    assert second_payload["data"]["machineCode"] == first_payload["data"]["machineCode"]
    assert second_payload["data"]["active"] is False


@pytest.mark.skipif(not HAS_CRYPTOGRAPHY, reason="缺少 cryptography 依赖")
def test_license_activate_persists_grant_across_app_recreation(
    runtime_data_dir: Path,
    monkeypatch,
) -> None:
    private_key = _configure_license_keys(runtime_data_dir, monkeypatch)
    from app.factory import create_app

    activation_code = _issue_activation_code(TEST_MACHINE_CODE, private_key)
    with TestClient(
        create_app(),
        base_url=LEGACY_RUNTIME_BASE_URL,
    ) as client:
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
    assert activated["data"]["licenseType"] == "local_device"
    assert (
        activated["data"]["machineCode"]
        == activated["data"]["maskedCode"]
    )
    assert "*" in activated["data"]["machineCode"]
    assert activated["data"]["activatedAt"]

    from app.factory import create_app

    with TestClient(
        create_app(),
        base_url=LEGACY_RUNTIME_BASE_URL,
    ) as reloaded_client:
        read_response = reloaded_client.get("/api/license/status")

    assert read_response.status_code == 200
    payload = read_response.json()
    assert payload["data"]["active"] is True
    assert payload["data"]["restrictedMode"] is False
    assert payload["data"]["machineBound"] is True
    assert payload["data"]["licenseType"] == "local_device"
    assert payload["data"]["machineCode"] == payload["data"]["maskedCode"]


def test_license_activation_rejects_blank_code_with_error_envelope(
    runtime_client: TestClient,
) -> None:
    response = runtime_client.post("/api/license/activate", json={"activationCode": ""})

    assert response.status_code == 422
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error"] == "请求参数校验失败"
    assert payload["requestId"]
    assert payload["details"]


def test_license_activate_returns_503_when_activation_dependency_is_unavailable(
    runtime_client: TestClient,
) -> None:
    if runtime_client.app.state.license_import_error is None:
        pytest.skip("当前环境已安装 cryptography")

    response = runtime_client.post(
        "/api/license/activate",
        json={"activationCode": "invalid-code"},
    )

    assert response.status_code == 503
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error"] == "许可证安全存储不可用"
    assert payload["error_code"] == "license.store.unavailable"
    assert payload["requestId"]


@pytest.mark.skipif(not HAS_CRYPTOGRAPHY, reason="缺少 cryptography 依赖")
def test_license_activation_rejects_machine_code_mismatch(
    runtime_data_dir: Path,
    monkeypatch,
) -> None:
    private_key = _configure_license_keys(runtime_data_dir, monkeypatch)
    from app.factory import create_app

    with TestClient(
        create_app(),
        base_url=LEGACY_RUNTIME_BASE_URL,
    ) as client:
        response = client.post(
            "/api/license/activate",
            json={
                "activationCode": _issue_activation_code(
                    "TKOPS-OTHER1-OTHER2-OTHER3-OTHER4-OTHER5",
                    private_key,
                )
            },
        )

    assert response.status_code == 403
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error"] == "许可证与本机不匹配"
    assert payload["error_code"] == "license.machine.mismatch"
    assert payload["requestId"]


@pytest.mark.skipif(not HAS_CRYPTOGRAPHY, reason="缺少 cryptography 依赖")
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


@pytest.mark.skipif(not HAS_CRYPTOGRAPHY, reason="缺少 cryptography 依赖")
def test_license_activation_rejects_invalid_signature(
    runtime_data_dir: Path,
    monkeypatch,
) -> None:
    private_key = _configure_license_keys(runtime_data_dir, monkeypatch)
    from app.factory import create_app

    invalid_code = _issue_activation_code(
        TEST_MACHINE_CODE,
        Ed25519PrivateKey.generate(),
    )
    with TestClient(
        create_app(),
        base_url=LEGACY_RUNTIME_BASE_URL,
    ) as client:
        response = client.post(
            "/api/license/activate",
            json={"activationCode": invalid_code},
        )

    assert response.status_code == 403
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error"] == "许可证无效"
    assert payload["error_code"] == "license.invalid"
    assert payload["requestId"]


@pytest.mark.skipif(not HAS_CRYPTOGRAPHY, reason="缺少 cryptography 依赖")
def test_license_events_write_structured_audit_logs(
    runtime_data_dir: Path,
    monkeypatch,
) -> None:
    private_key = _configure_license_keys(runtime_data_dir, monkeypatch)
    from app.factory import create_app

    with TestClient(
        create_app(),
        base_url=LEGACY_RUNTIME_BASE_URL,
    ) as client:
        status_response = client.get("/api/license/status")
        activate_response = client.post(
            "/api/license/activate",
            json={
                "activationCode": _issue_activation_code(
                    TEST_MACHINE_CODE,
                    private_key,
                )
            },
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
    assert "bootstrap.license_status_read" in messages
    assert "bootstrap.license_activated" in messages
