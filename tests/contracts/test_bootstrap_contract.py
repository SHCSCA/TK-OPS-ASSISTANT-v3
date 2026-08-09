from __future__ import annotations

from fastapi.testclient import TestClient


def test_bootstrap_contract_covers_reports_and_envelope(
    licensed_runtime_client: TestClient,
) -> None:
    response = licensed_runtime_client.post(
        "/api/bootstrap/initialize-directories"
    )

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"ok", "data"}
    report = payload["data"]
    assert set(report) == {"rootDir", "databasePath", "status", "directories", "checkedAt"}
    assert report["directories"]
    assert set(report["directories"][0]) == {
        "key",
        "label",
        "path",
        "exists",
        "writable",
        "status",
        "message",
    }


def test_bootstrap_contract_surfaces_server_error(
    licensed_runtime_client: TestClient,
    monkeypatch,
) -> None:
    def _boom(**_: object) -> object:
        raise RuntimeError("boom")

    monkeypatch.setattr(
        licensed_runtime_client.app.state.bootstrap_v1_service,
        "initialize_directories",
        _boom,
    )

    client = TestClient(
        licensed_runtime_client.app,
        base_url=str(licensed_runtime_client.base_url),
        raise_server_exceptions=False,
    )
    response = client.post("/api/bootstrap/initialize-directories")

    assert response.status_code == 500
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error"]


def test_bootstrap_write_contract_requires_active_license(
    runtime_client: TestClient,
) -> None:
    for path in (
        "/api/bootstrap/initialize-directories",
        "/api/bootstrap/runtime-selfcheck",
    ):
        response = runtime_client.post(path)

        assert response.status_code == 403
        payload = response.json()
        assert payload["ok"] is False
        assert payload["error_code"] == "license.invalid"


def test_bootstrap_readiness_contract_returns_blockers_and_actions(
    runtime_client: TestClient,
) -> None:
    response = runtime_client.get("/api/bootstrap/readiness")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"ok", "data"}
    assert payload["ok"] is True
    report = payload["data"]
    assert set(report) == {"status", "canContinue", "checkedAt", "items", "blockers"}
    assert isinstance(report["canContinue"], bool)
    assert report["items"]
    assert set(report["items"][0]) == {
        "key",
        "label",
        "status",
        "detail",
        "errorCode",
        "blockedReason",
        "affectedTarget",
        "nextStep",
        "action",
        "checkedAt",
    }
    if report["items"][0]["action"] is not None:
        assert set(report["items"][0]["action"]) == {"key", "label"}
    if report["blockers"]:
        assert set(report["blockers"][0]) == {
            "key",
            "errorCode",
            "blockedReason",
            "affectedTarget",
            "nextStep",
            "action",
        }
