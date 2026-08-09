from __future__ import annotations

from fastapi.testclient import TestClient


def test_license_status_contract_uses_license_prefix_and_expected_shape(
    runtime_client: TestClient,
) -> None:
    response = runtime_client.get("/api/license/status")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"ok", "data"}
    assert payload["ok"] is True
    assert set(payload["data"]) == {
        "active",
        "restrictedMode",
        "machineCode",
        "machineBound",
        "licenseType",
        "maskedCode",
        "activatedAt",
    }
    assert payload["data"]["machineCode"] == payload["data"]["maskedCode"]
    assert payload["data"]["licenseType"] == "local_device"


def test_license_activate_contract_returns_expected_shape(
    runtime_client: TestClient,
) -> None:
    response = runtime_client.post(
        "/api/license/activate",
        json={"activationCode": "invalid-code"},
    )

    assert response.status_code in {403, 503}
    payload = response.json()
    assert payload["ok"] is False
    assert set(payload) >= {"ok", "error", "error_code", "requestId"}
    assert payload["error_code"] in {
        "license.invalid",
        "license.store.unavailable",
    }


def test_license_legacy_contract_rejects_untrusted_host(
    runtime_client: TestClient,
) -> None:
    client = TestClient(
        runtime_client.app,
        base_url="http://testserver",
        raise_server_exceptions=False,
    )

    response = client.get("/api/license/status")

    assert response.status_code == 400
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error_code"] == "runtime.host.invalid"


def test_license_legacy_contract_rejects_untrusted_origin(
    runtime_client: TestClient,
) -> None:
    response = runtime_client.get(
        "/api/license/status",
        headers={"Origin": "https://untrusted.example"},
    )

    assert response.status_code == 403
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error_code"] == "runtime.origin.forbidden"
