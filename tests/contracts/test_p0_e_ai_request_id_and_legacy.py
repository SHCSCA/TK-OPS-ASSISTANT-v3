from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

LEGACY_DANGEROUS_WRITES = (
    ("POST", "/api/settings/ai-providers/openai/models/refresh"),
    ("PUT", "/api/settings/ai-capabilities"),
    ("PUT", "/api/settings/ai-capabilities/providers/openai/secret"),
    ("POST", "/api/settings/ai-capabilities/providers/openai/health-check"),
    ("POST", "/api/ai-providers/health/refresh"),
    ("PUT", "/api/ai-providers/openai/models/gpt-4o"),
    ("POST", "/api/prompt-templates"),
    ("PUT", "/api/prompt-templates/template-one"),
    ("DELETE", "/api/prompt-templates/template-one"),
)


@pytest.mark.parametrize(
    ("method", "path"),
    LEGACY_DANGEROUS_WRITES,
    ids=lambda item: str(item),
)
def test_legacy_ai_dangerous_writes_return_410_without_parsing_body(
    runtime_client: TestClient,
    method: str,
    path: str,
) -> None:
    response = runtime_client.request(
        method,
        path,
        content=b"{ definitely-not-json",
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 410
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error_code"] == "legacy.write.unsupported"


def test_inbound_request_id_is_echoed_on_success(
    licensed_runtime_client: TestClient,
) -> None:
    response = licensed_runtime_client.get(
        "/api/v1/system/providers",
        headers={"X-Request-ID": "req_p0e_contract_echo"},
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "req_p0e_contract_echo"


def test_inbound_request_id_is_echoed_on_error(
    licensed_runtime_client: TestClient,
) -> None:
    response = licensed_runtime_client.get(
        "/api/v1/system/providers/provider-missing",
        headers={"X-Request-ID": "req_p0e_error_echo"},
    )

    assert response.status_code == 404
    assert response.headers["X-Request-ID"] == "req_p0e_error_echo"


def test_ai_create_requires_idempotency_key(
    licensed_runtime_client: TestClient,
) -> None:
    response = licensed_runtime_client.post(
        "/api/v1/system/providers",
        json={
            "name": "缺少幂等键 Provider",
            "adapterType": "openai_compatible",
            "baseUrl": "https://api.example.test/v1",
            "region": None,
            "timeoutMs": 30_000,
            "maxConcurrency": 1,
            "enabled": True,
        },
    )

    assert response.status_code == 422
    assert response.json()["error_code"] == "REQUEST_VALIDATION_FAILED"


def test_ai_revision_mutation_requires_if_match(
    licensed_runtime_client: TestClient,
) -> None:
    created = licensed_runtime_client.post(
        "/api/v1/system/providers",
        headers={"Idempotency-Key": "idem-provider-revision-required"},
        json={
            "name": "修订头 Provider",
            "adapterType": "openai_compatible",
            "baseUrl": "https://api.example.test/v1",
            "region": None,
            "timeoutMs": 30_000,
            "maxConcurrency": 1,
            "enabled": True,
        },
    )
    assert created.status_code == 201, created.text
    provider_id = created.json()["data"]["id"]

    response = licensed_runtime_client.patch(
        f"/api/v1/system/providers/{provider_id}",
        json={"name": "不带修订头"},
    )

    assert response.status_code == 412
    assert response.json()["error_code"] == "REVISION_CONFLICT"
