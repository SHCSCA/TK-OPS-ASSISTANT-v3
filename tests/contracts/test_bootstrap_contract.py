from __future__ import annotations

from fastapi.testclient import TestClient


def test_initialize_directories_contract_returns_directory_report(
    runtime_client: TestClient,
) -> None:
    response = runtime_client.post("/api/bootstrap/initialize-directories")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"ok", "data"}
    assert payload["ok"] is True
    assert set(payload["data"]) == {
        "rootDir",
        "databasePath",
        "status",
        "directories",
        "checkedAt",
    }
    assert isinstance(payload["data"]["directories"], list)
    assert payload["data"]["directories"]
    assert set(payload["data"]["directories"][0]) == {
        "key",
        "label",
        "path",
        "exists",
        "writable",
        "status",
        "message",
    }


def test_runtime_selfcheck_contract_returns_structured_checks(
    runtime_client: TestClient,
) -> None:
    response = runtime_client.post("/api/bootstrap/runtime-selfcheck")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"ok", "data"}
    assert payload["ok"] is True
    assert set(payload["data"]) == {"status", "runtimeVersion", "checkedAt", "items"}
    assert isinstance(payload["data"]["items"], list)
    assert payload["data"]["items"]
    assert set(payload["data"]["items"][0]) == {
        "key",
        "label",
        "status",
        "detail",
        "errorCode",
        "checkedAt",
    }
