from __future__ import annotations

import json
import time
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

from domain.models.ai_configuration_v1 import ModelCapability, ModelProfile
from domain.models.ai_execution_evidence import AIProviderValidationRun
from tests.runtime.p0e_ai_integration_support import session
from tests.runtime.p0h_provider_test_server import (
    ControlledProviderScenario,
    ControlledProviderServer,
)


def test_openai_compatible_four_stage_validation_persists_real_evidence(
    licensed_runtime_client: TestClient,
) -> None:
    scenario = ControlledProviderScenario()
    with ControlledProviderServer(scenario) as server:
        provider = _create_provider(
            licensed_runtime_client,
            server.base_url,
            key="four-stage",
        )
        provider = _set_credential(
            licensed_runtime_client,
            provider,
            scenario.token,
        )
        health = _submit_and_wait(
            licensed_runtime_client,
            f"/api/v1/system/providers/{provider['id']}/checks",
            key="health-four-stage",
            payload={
                "stages": ["network", "authentication"],
                "force": True,
            },
        )
        assert health["status"] == "completed"
        discovery = _submit_and_wait(
            licensed_runtime_client,
            f"/api/v1/system/providers/{provider['id']}/model-discovery",
            key="models-four-stage",
            payload={"replaceMissing": False},
        )
        assert discovery["status"] == "completed"
        model = _first_model(licensed_runtime_client, str(provider["id"]))
        capability = _submit_and_wait(
            licensed_runtime_client,
            f"/api/v1/system/models/{model['id']}/capability-checks",
            key="capability-four-stage",
            payload={
                "capabilityKeys": ["script_generation"],
                "mode": "real_small_call",
                "force": True,
            },
        )
        assert capability["status"] == "completed"

    with session(licensed_runtime_client) as database:
        evidence = database.scalars(
            select(AIProviderValidationRun).order_by(
                AIProviderValidationRun.created_at.asc()
            )
        ).all()
        stages = {(row.stage, row.status) for row in evidence}
        assert {
            ("network", "verified"),
            ("authentication", "verified"),
            ("model_discovery", "verified"),
            ("real_small_call", "verified"),
        }.issubset(stages)
        real_call = next(row for row in evidence if row.stage == "real_small_call")
        assert real_call.request_hash
        assert real_call.response_hash
        assert json.loads(str(real_call.usage_json))["outputUnits"] == 1
        capability_row = database.scalar(
            select(ModelCapability).where(
                ModelCapability.model_profile_id == model["id"],
                ModelCapability.capability_key == "script_generation",
            )
        )
        assert capability_row is not None
        assert capability_row.contract_verified is True
    post = next(item for item in scenario.received if item["method"] == "POST")
    body = post["body"]
    assert isinstance(body, dict)
    assert body["max_tokens"] <= 8
    assert body["temperature"] == 0.0


def test_authentication_failure_is_layered_and_safe(
    licensed_runtime_client: TestClient,
) -> None:
    scenario = ControlledProviderScenario()
    with ControlledProviderServer(scenario) as server:
        provider = _create_provider(
            licensed_runtime_client,
            server.base_url,
            key="auth-failure",
        )
        provider = _set_credential(
            licensed_runtime_client,
            provider,
            "wrong-token",
        )
        task = _submit_and_wait(
            licensed_runtime_client,
            f"/api/v1/system/providers/{provider['id']}/checks",
            key="auth-failure",
            payload={
                "stages": ["network", "authentication"],
                "force": True,
            },
        )
    assert task["status"] == "failed"
    assert task["errorCode"] == "AI_PROVIDER_AUTH_FAILED"
    with session(licensed_runtime_client) as database:
        rows = database.scalars(select(AIProviderValidationRun)).all()
        assert [(row.stage, row.status) for row in rows] == [
            ("network", "verified"),
            ("authentication", "failed"),
        ]


def test_invalid_generation_response_fails_without_raw_body(
    licensed_runtime_client: TestClient,
) -> None:
    scenario = ControlledProviderScenario(invalid_generation=True)
    with ControlledProviderServer(scenario) as server:
        provider, model = _provider_and_model(
            licensed_runtime_client,
            scenario,
            server.base_url,
            key="invalid-response",
        )
        task = _real_capability_task(
            licensed_runtime_client,
            model,
            key="invalid-response",
        )
    assert task["status"] == "failed"
    assert task["errorCode"] == "AI_PROVIDER_RESPONSE_INVALID"
    with session(licensed_runtime_client) as database:
        evidence = database.scalar(select(AIProviderValidationRun))
        assert evidence is not None
        assert evidence.status == "failed"
        assert evidence.request_hash
        assert evidence.response_hash
        assert scenario.token not in str(evidence.__dict__)
    assert scenario.token not in json.dumps(task, ensure_ascii=False)


def test_missing_usage_is_partial_and_cannot_verify_capability(
    licensed_runtime_client: TestClient,
) -> None:
    scenario = ControlledProviderScenario(omit_usage=True)
    with ControlledProviderServer(scenario) as server:
        _provider, model = _provider_and_model(
            licensed_runtime_client,
            scenario,
            server.base_url,
            key="usage-partial",
        )
        task = _real_capability_task(
            licensed_runtime_client,
            model,
            key="usage-partial",
        )
    assert task["status"] == "completed"
    with session(licensed_runtime_client) as database:
        evidence = database.scalar(select(AIProviderValidationRun))
        capability = database.scalar(
            select(ModelCapability).where(
                ModelCapability.model_profile_id == model["id"]
            )
        )
        assert evidence is not None and evidence.status == "partial"
        assert capability is not None
        assert capability.contract_verified is False


def test_external_error_marker_never_reaches_audit_or_logs(
    licensed_runtime_client: TestClient,
    runtime_data_dir: Path,
) -> None:
    marker = "P0H-RAW-PROVIDER-SECRET-MARKER-91D2"
    scenario = ControlledProviderScenario(
        error_status=500,
        error_marker=marker,
    )
    with ControlledProviderServer(scenario) as server:
        _provider, model = _provider_and_model(
            licensed_runtime_client,
            scenario,
            server.base_url,
            key="redaction",
        )
        task = _real_capability_task(
            licensed_runtime_client,
            model,
            key="redaction",
        )
    assert task["status"] == "failed"
    assert marker not in json.dumps(task, ensure_ascii=False)
    with session(licensed_runtime_client) as database:
        evidence = database.scalar(select(AIProviderValidationRun))
        assert evidence is not None
        assert marker not in str(evidence.__dict__)
    logs = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in runtime_data_dir.rglob("*.log")
    )
    assert marker not in logs


def _create_provider(
    client: TestClient,
    base_url: str,
    *,
    key: str,
) -> dict[str, object]:
    response = client.post(
        "/api/v1/system/providers",
        headers={"Idempotency-Key": f"idem-p0h-provider-{key}"},
        json={
            "name": f"P0-H {key}",
            "adapterType": "openai_compatible",
            "baseUrl": base_url,
            "region": None,
            "proxyRef": None,
            "timeoutMs": 5_000,
            "maxConcurrency": 1,
            "enabled": True,
            "extraParams": {"protocolVariant": "chat_completions"},
            "costPolicy": {},
        },
    )
    assert response.status_code == 201, response.text
    return dict(response.json()["data"])


def _set_credential(
    client: TestClient,
    provider: dict[str, object],
    credential: str,
) -> dict[str, object]:
    response = client.put(
        f"/api/v1/system/providers/{provider['id']}/credential",
        headers={"If-Match": str(provider["revision"])},
        json={"credential": credential},
    )
    assert response.status_code == 200, response.text
    updated = dict(provider)
    updated["revision"] = response.json()["data"]["providerRevision"]
    return updated


def _provider_and_model(
    client: TestClient,
    scenario: ControlledProviderScenario,
    base_url: str,
    *,
    key: str,
) -> tuple[dict[str, object], dict[str, object]]:
    provider = _set_credential(
        client,
        _create_provider(client, base_url, key=key),
        scenario.token,
    )
    response = client.post(
        "/api/v1/system/models",
        headers={"Idempotency-Key": f"idem-p0h-model-{key}"},
        json={
            "providerProfileId": provider["id"],
            "modelId": scenario.model_id,
            "displayName": "P0-H 文本模型",
            "enabled": True,
            "baseLimits": {},
        },
    )
    assert response.status_code == 201, response.text
    return provider, dict(response.json()["data"])


def _first_model(client: TestClient, provider_id: str) -> dict[str, object]:
    response = client.get(
        "/api/v1/system/models",
        params={"providerId": provider_id},
    )
    assert response.status_code == 200, response.text
    items = response.json()["data"]["items"]
    assert len(items) == 1
    return dict(items[0])


def _real_capability_task(
    client: TestClient,
    model: dict[str, object],
    *,
    key: str,
) -> dict[str, object]:
    return _submit_and_wait(
        client,
        f"/api/v1/system/models/{model['id']}/capability-checks",
        key=f"capability-{key}",
        payload={
            "capabilityKeys": ["script_generation"],
            "mode": "real_small_call",
            "force": True,
        },
    )


def _submit_and_wait(
    client: TestClient,
    path: str,
    *,
    key: str,
    payload: dict[str, object],
) -> dict[str, object]:
    response = client.post(
        path,
        headers={"Idempotency-Key": f"idem-p0h-task-{key}"},
        json=payload,
    )
    assert response.status_code == 202, response.text
    task_id = response.json()["data"]["taskId"]
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        current = client.get(f"/api/v1/system/tasks/{task_id}")
        assert current.status_code == 200, current.text
        task = current.json()["data"]
        if task["status"] in {"completed", "failed"}:
            return dict(task)
        time.sleep(0.02)
    raise AssertionError(f"系统任务未在时限内结束：{task_id}")
