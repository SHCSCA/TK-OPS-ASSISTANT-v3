from __future__ import annotations

from collections.abc import Mapping

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


def session(client: TestClient) -> Session:
    return client.app.state.session_factory()


def create_provider(
    client: TestClient,
    *,
    key: str,
) -> dict[str, object]:
    response = client.post(
        "/api/v1/system/providers",
        headers={"Idempotency-Key": f"idem-provider-{key}"},
        json={
            "name": f"{key} Provider",
            "adapterType": "openai_compatible",
            "baseUrl": "https://api.example.test/v1",
            "region": None,
            "timeoutMs": 30_000,
            "maxConcurrency": 2,
            "enabled": True,
        },
    )
    assert response.status_code == 201, response.text
    return _data(response.json())


def create_model(
    client: TestClient,
    *,
    provider_id: str,
    key: str,
) -> dict[str, object]:
    response = client.post(
        "/api/v1/system/models",
        headers={"Idempotency-Key": f"idem-model-{key}"},
        json={
            "providerProfileId": provider_id,
            "modelId": f"model-{key}",
            "displayName": f"{key} 模型",
            "enabled": True,
            "baseLimits": {},
        },
    )
    assert response.status_code == 201, response.text
    return _data(response.json())


def create_prompt(
    client: TestClient,
    *,
    profile_key: str,
    capability_key: str,
    system_prompt: str,
    task_template: str,
) -> dict[str, object]:
    response = client.post(
        "/api/v1/system/prompt-profiles",
        headers={"Idempotency-Key": f"idem-prompt-{profile_key}"},
        json={
            "profileKey": profile_key,
            "name": f"{profile_key} Prompt",
            "capabilityKey": capability_key,
            "systemPrompt": system_prompt,
            "taskTemplate": task_template,
            "variablesSchema": {"type": "object"},
            "outputSchema": {"type": "object"},
            "visualStylePrefix": "",
            "safetyConstraints": {},
        },
    )
    assert response.status_code == 201, response.text
    return _data(response.json())


def create_account(
    client: TestClient,
    *,
    key: str,
) -> tuple[str, int]:
    response = client.post(
        "/api/v1/accounts",
        headers={"Idempotency-Key": f"idem-account-{key}"},
        json={
            "name": f"{key} 账号",
            "username": None,
            "platform": "tiktok",
        },
    )
    assert response.status_code == 201, response.text
    payload = response.json()
    return str(payload["data"]["id"]), int(payload["meta"]["revision"])


def recipe_payload(
    *,
    name: str,
    overrides: Mapping[str, object] | None = None,
) -> dict[str, object]:
    return {
        "name": name,
        "routeOverrides": dict(overrides or {}),
        "visualStyle": {},
        "voiceProfileRef": None,
        "compositionTemplateRef": None,
        "costPolicy": {},
        "fallbackPolicy": {},
    }


def _data(payload: Mapping[str, object]) -> dict[str, object]:
    data = payload["data"]
    assert isinstance(data, dict)
    return dict(data)

