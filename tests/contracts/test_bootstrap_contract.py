from __future__ import annotations

from fastapi.testclient import TestClient


def test_bootstrap_contract_covers_reports_and_envelope(runtime_client: TestClient) -> None:
    response = runtime_client.post("/api/bootstrap/initialize-directories")

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


def test_bootstrap_contract_surfaces_server_error(runtime_client: TestClient, monkeypatch) -> None:
    def _boom() -> object:
        raise RuntimeError("boom")

    monkeypatch.setattr(runtime_client.app.state.settings_service, "get_settings", _boom)

    client = TestClient(runtime_client.app, raise_server_exceptions=False)
    response = client.post("/api/bootstrap/initialize-directories")

    assert response.status_code == 500
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error"]
