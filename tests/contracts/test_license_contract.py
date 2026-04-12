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


def test_license_activate_contract_returns_expected_shape(
    runtime_client: TestClient,
) -> None:
    response = runtime_client.post(
        "/api/license/activate",
        json={"activationCode": "invalid-code"},
    )

    assert response.status_code in {200, 400}
    payload = response.json()
    if payload["ok"] is True:
        assert set(payload) == {"ok", "data"}
        assert set(payload["data"]) == {
            "active",
            "restrictedMode",
            "machineCode",
            "machineBound",
            "licenseType",
            "maskedCode",
            "activatedAt",
        }
    else:
        assert set(payload) >= {"ok", "error"}
