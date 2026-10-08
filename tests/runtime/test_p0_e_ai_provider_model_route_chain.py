from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from domain.models.ai_configuration_v1 import (
    CapabilityRoute,
    ModelCapability,
    ModelProfile,
    ProviderProfile,
)
from domain.models.runtime_task import RuntimeTask
from domain.models.ai_execution_evidence import AIProviderValidationRun
from domain.models.system_config import SystemConfig
from errors import DomainError, ErrorCode
from tests.runtime.p0e_ai_integration_support import (
    create_model,
    create_prompt,
    create_provider,
    session,
)


def test_provider_creation_is_idempotent_and_rejects_key_reuse(
    licensed_runtime_client: TestClient,
) -> None:
    first = create_provider(licensed_runtime_client, key="idempotent")
    replay = create_provider(licensed_runtime_client, key="idempotent")

    assert replay == first
    conflict = licensed_runtime_client.post(
        "/api/v1/system/providers",
        headers={"Idempotency-Key": "idem-provider-idempotent"},
        json={
            "name": "不同 Provider",
            "adapterType": "openai_compatible",
            "baseUrl": "https://other.example.test/v1",
            "region": None,
            "timeoutMs": 30_000,
            "maxConcurrency": 2,
            "enabled": True,
        },
    )
    assert conflict.status_code == 409
    assert conflict.json()["error_code"] == ErrorCode.REQUEST_CONFLICT.value


def test_unverified_model_is_preserved_as_repairable_route_draft(
    licensed_runtime_client: TestClient,
) -> None:
    provider = create_provider(licensed_runtime_client, key="unverified")
    model = create_model(
        licensed_runtime_client,
        provider_id=str(provider["id"]),
        key="unverified",
    )
    routes = (
        licensed_runtime_client.app.state.ai_configuration_v1_service.routes
    )

    result = routes.put_capability_route(
        "script_generation",
        {
            "primaryModelProfileId": model["id"],
            "fallbackModelProfileId": None,
            "promptProfileId": None,
            "enabled": True,
        },
        expected_revision=0,
        idempotency_key="idem-route-unverified",
        request_id="req-route-unverified",
        operation_id="op-route-unverified",
    )

    assert result.data["validationStatus"] == "invalid"
    assert result.data["validationIssues"]


def test_verified_capability_can_be_routed_and_revision_is_enforced(
    licensed_runtime_client: TestClient,
) -> None:
    provider = create_provider(licensed_runtime_client, key="verified")
    model = create_model(
        licensed_runtime_client,
        provider_id=str(provider["id"]),
        key="verified",
    )
    _seed_verified_capability(
        licensed_runtime_client,
        model_id=str(model["id"]),
        capability_key="script_generation",
    )
    prompt_id = _create_active_prompt(
        licensed_runtime_client,
        key="verified",
        capability_key="script_generation",
    )
    routes = (
        licensed_runtime_client.app.state.ai_configuration_v1_service.routes
    )

    created = licensed_runtime_client.put(
        "/api/v1/system/capability-routes/script_generation",
        headers={
            "If-Match": "0",
            "Idempotency-Key": "idem-route-verified",
        },
        json={
            "primaryModelProfileId": model["id"],
            "fallbackModelProfileId": None,
            "promptProfileId": prompt_id,
            "enabled": True,
        },
    )

    assert created.status_code == 200, created.text
    route = created.json()["data"]
    assert route["validationStatus"] == "valid"
    assert route["revision"] == 3
    with pytest.raises(DomainError) as caught:
        routes.put_capability_route(
            "script_generation",
            {
                "primaryModelProfileId": model["id"],
                "fallbackModelProfileId": None,
                "promptProfileId": None,
                "enabled": False,
            },
            expected_revision=99,
            idempotency_key="idem-route-stale",
            request_id="req-route-stale",
            operation_id="op-route-stale",
        )
    assert caught.value.error_code == ErrorCode.REVISION_CONFLICT.value


def test_model_capability_check_freezes_only_model_and_provider_revisions(
    licensed_runtime_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = create_provider(licensed_runtime_client, key="cap-check")
    model = create_model(
        licensed_runtime_client,
        provider_id=str(provider["id"]),
        key="cap-check",
    )
    monkeypatch.setattr(
        licensed_runtime_client.app.state.task_coordinator,
        "_schedule_if_queued",
        lambda _record: None,
    )

    response = licensed_runtime_client.post(
        f"/api/v1/system/models/{model['id']}/capability-checks",
        headers={"Idempotency-Key": "idem-model-capability-check"},
        json={
            "capabilityKeys": ["script_generation"],
            "force": True,
        },
    )

    assert response.status_code == 202, response.text
    task_id = str(response.json()["data"]["taskId"])
    with session(licensed_runtime_client) as database:
        task = database.get(RuntimeTask, task_id)
        assert task is not None
        assert task.task_type == "model.capability_check"
        payload = json.loads(task.config_snapshot_json)["payload"]
    assert payload == {
        "modelProfileId": model["id"],
        "modelRevision": model["revision"],
        "providerRevision": provider["revision"],
        "capabilityKeys": ["script_generation"],
        "mode": "contract_only",
        "force": True,
    }


def test_provider_health_is_resolved_without_changing_ai_config_revision(
    licensed_runtime_client: TestClient,
) -> None:
    provider = create_provider(licensed_runtime_client, key="health-route")
    model = create_model(
        licensed_runtime_client,
        provider_id=str(provider["id"]),
        key="health-route",
    )
    _seed_verified_capability(
        licensed_runtime_client,
        model_id=str(model["id"]),
        capability_key="script_generation",
    )
    prompt_id = _create_active_prompt(
        licensed_runtime_client,
        key="health-route",
        capability_key="script_generation",
    )
    created = licensed_runtime_client.put(
        "/api/v1/system/capability-routes/script_generation",
        headers={
            "If-Match": "0",
            "Idempotency-Key": "idem-route-health-dynamic",
        },
        json={
            "primaryModelProfileId": model["id"],
            "fallbackModelProfileId": None,
            "promptProfileId": prompt_id,
            "enabled": True,
        },
    )
    assert created.status_code == 200, created.text

    with session(licensed_runtime_client) as database:
        before = database.get(SystemConfig, 1)
        route = database.get(CapabilityRoute, created.json()["data"]["id"])
        provider_row = database.get(ProviderProfile, provider["id"])
        assert before is not None
        assert route is not None
        assert provider_row is not None
        revision = before.ai_config_revision
        assert route.validation_status == "valid"
        provider_row.enabled = False
        provider_row.revision += 1
        database.commit()

    listed = licensed_runtime_client.get(
        "/api/v1/system/capability-routes"
    )
    assert listed.status_code == 200, listed.text
    current = listed.json()["data"]["items"][0]
    assert current["validationStatus"] == "invalid"
    assert current["validationIssues"][0]["code"] == "AI_PROVIDER_DISABLED"
    with session(licensed_runtime_client) as database:
        current_config = database.get(SystemConfig, 1)
        assert current_config is not None
        assert current_config.ai_config_revision == revision


def seed_verified_routes(
    client: TestClient,
    *,
    key: str,
) -> tuple[dict[str, object], dict[str, object]]:
    provider = create_provider(client, key=key)
    model = create_model(
        client,
        provider_id=str(provider["id"]),
        key=key,
    )
    routes = client.app.state.ai_configuration_v1_service.routes
    for index, capability_key in enumerate(
        (
            "script_generation",
            "storyboard_generation",
            "text_to_video",
        )
    ):
        _seed_verified_capability(
            client,
            model_id=str(model["id"]),
            capability_key=capability_key,
            suffix=str(index),
        )
        prompt_id = (
            _create_active_prompt(
                client,
                key=f"{key}-{index}",
                capability_key=capability_key,
            )
            if capability_key != "text_to_video"
            else None
        )
        routes.put_capability_route(
            capability_key,
            {
                "primaryModelProfileId": model["id"],
                "fallbackModelProfileId": None,
                "promptProfileId": prompt_id,
                "enabled": True,
            },
            expected_revision=0,
            idempotency_key=f"idem-route-{key}-{index}",
            request_id=f"req-route-{key}-{index}",
            operation_id=f"op-route-{key}-{index}",
        )
    return provider, model


def _seed_verified_capability(
    client: TestClient,
    *,
    model_id: str,
    capability_key: str,
    suffix: str = "0",
) -> None:
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    with session(client) as database:
        model = database.get(ModelProfile, model_id)
        assert model is not None
        provider = database.get(
            ProviderProfile,
            model.provider_profile_id,
        )
        assert provider is not None
        provider.enabled = True
        provider.health_status = "ready"
        digest = hashlib.sha256(
            f"{model_id}:{capability_key}:{suffix}".encode("utf-8")
        ).hexdigest()
        task_id = f"task_{digest[:24]}"
        task = RuntimeTask(
                id=task_id,
                scope="system",
                account_id=None,
                task_type="model.capability_check",
                status="completed",
                completion_kind="succeeded",
                failure_kind=None,
                progress=1.0,
                cancellable=True,
                timeout_at=None,
                attempt=1,
                retry_of_task_id=None,
                config_snapshot_json="{}",
                result_ref=None,
                error_code=None,
                error_log_id=None,
                revision=1,
                created_at=now,
                started_at=now,
                completed_at=now,
                updated_at=now,
                idempotency_key_hash=digest,
                request_hash=digest,
                handler_version=2,
            )
        database.add(task)
        database.flush([task])
        database.add(
            ModelCapability(
                id=f"cap_{model_id}_{suffix}",
                model_profile_id=model_id,
                capability_key=capability_key,
                declared_supported=True,
                adapter_supported=True,
                contract_verified=True,
                input_modalities_json='["text"]',
                output_modalities_json='["text"]',
                parameter_schema_json="{}",
                source_urls_json="[]",
                known_limits_json="{}",
                verified_at=now,
                contract_revision=1,
            )
        )
        database.add(
            AIProviderValidationRun(
                id=f"pval_{digest[:24]}",
                provider_profile_id=provider.id,
                provider_revision=int(provider.revision),
                model_profile_id=model_id,
                model_revision=int(model.revision),
                capability_key=capability_key,
                stage="real_small_call",
                status="verified",
                task_id=task_id,
                request_hash=digest,
                response_hash=digest,
                response_id_hash=None,
                usage_json='{"outputUnits":1}',
                duration_ms=1,
                error_code=None,
                error_log_id=None,
                verified_at=now,
                created_at=now,
            )
        )
        database.commit()


def _create_active_prompt(
    client: TestClient,
    *,
    key: str,
    capability_key: str,
) -> str:
    prompt = create_prompt(
        client,
        profile_key=f"route-{key}",
        capability_key=capability_key,
        system_prompt="系统提示",
        task_template="任务提示",
    )
    activated = client.post(
        f"/api/v1/system/prompt-profiles/route-{key}/versions/1/activate",
        headers={
            "If-Match": str(prompt["revision"]),
            "Idempotency-Key": f"idem-route-{key}-prompt-activate",
        },
    )
    assert activated.status_code == 200, activated.text
    return str(activated.json()["data"]["activeVersionId"])
