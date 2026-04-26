from __future__ import annotations

from fastapi.testclient import TestClient


def test_diagnostics_contract_exposes_check_report_items(
    runtime_client: TestClient,
) -> None:
    response = runtime_client.get("/api/settings/diagnostics")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"ok", "data"}
    assert payload["ok"] is True
    data = payload["data"]
    assert {
        "databasePath",
        "logDir",
        "revision",
        "mode",
        "healthStatus",
        "configScope",
        "checkedAt",
        "overallStatus",
        "items",
    } <= set(data)
    assert data["overallStatus"] in {"ready", "warning", "failed"}
    assert isinstance(data["items"], list)
    assert data["items"]
    assert {
        "id",
        "label",
        "group",
        "status",
        "summary",
        "impact",
        "detail",
        "actionLabel",
        "actionTarget",
    } == set(data["items"][0])
