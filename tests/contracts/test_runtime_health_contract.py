from __future__ import annotations

from fastapi.testclient import TestClient

def test_health_contract_uses_settings_prefix_and_json_envelope(
    runtime_client: TestClient,
) -> None:
    client = runtime_client

    response = client.get("/api/settings/health")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"ok", "data"}
    assert payload["ok"] is True
    assert {
        "runtime",
        "aiProvider",
        "renderQueue",
        "publishingQueue",
        "taskBus",
        "license",
        "lastSyncAt",
    }.issubset(payload["data"])
    assert set(payload["data"]["runtime"]) == {"status", "port", "uptimeMs", "version"}
    assert set(payload["data"]["aiProvider"]) == {
        "status",
        "latencyMs",
        "providerId",
        "providerName",
        "lastChecked",
    }
    assert set(payload["data"]["renderQueue"]) == {"running", "queued", "avgWaitMs"}
    assert set(payload["data"]["publishingQueue"]) == {"pendingToday", "failedToday"}
    assert set(payload["data"]["taskBus"]) == {"running", "queued", "blocked", "failed24h"}
    assert set(payload["data"]["license"]) == {"status", "expiresAt"}
