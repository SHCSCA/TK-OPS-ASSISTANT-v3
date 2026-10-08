from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from domain.models.ai_execution_evidence import AIProviderValidationRun
from domain.models.ai_provider import (
    ModelCapability,
    ModelProfile,
    ProviderProfile,
)
from domain.models.runtime_task import RuntimeTask
from tests.runtime.p0c_account_integration_support import (
    account_revision,
    create_account,
    mutation_headers,
    session,
    wait_account_task,
)
from tests.runtime.p0e_ai_integration_support import create_prompt


@dataclass(frozen=True, slots=True)
class P0HExecutionFixture:
    account_id: str
    account_revision: int
    recipe_version_id: str
    knowledge_snapshot_id: str
    provider_ids: tuple[str, ...]
    model_ids: tuple[str, ...]


def enable_ai_execution(client: TestClient) -> None:
    config = client.app.state.config_bus_service
    current = config.get()
    if current.values.get("ai.execution.enabled") is True:
        return
    config.update(
        {"ai.execution.enabled": True},
        expected_revision=current.revision,
        request_id="req_p0h_execution_enable",
        operation_id="op_p0h_execution_enable",
    )


def seed_execution_chain(
    client: TestClient,
    *,
    base_urls: tuple[str, ...],
    credentials: tuple[str, ...],
    key: str,
    route_max_retries: int = 0,
    route_max_cost_micros: int = 1_000_000,
    route_timeout_ms: int = 5_000,
) -> P0HExecutionFixture:
    if len(base_urls) != len(credentials) or not base_urls:
        raise AssertionError("受控 Provider 配置数量不一致")
    enable_ai_execution(client)
    providers: list[dict[str, object]] = []
    models: list[dict[str, object]] = []
    for index, (base_url, credential) in enumerate(
        zip(base_urls, credentials, strict=True)
    ):
        provider, model = _create_provider_and_model(
            client,
            base_url=base_url,
            credential=credential,
            key=f"{key}-{index}",
        )
        _seed_capabilities(
            client,
            provider_id=str(provider["id"]),
            model_id=str(model["id"]),
            key=f"{key}-{index}",
        )
        providers.append(provider)
        models.append(model)

    prompts = {
        capability: _create_active_prompt(
            client,
            capability_key=capability,
            key=f"{key}-{capability}",
        )
        for capability in ("script_generation", "storyboard_generation")
    }
    model_ids = tuple(str(item["id"]) for item in models)
    for capability in (
        "script_generation",
        "storyboard_generation",
        "text_to_video",
    ):
        _create_active_route(
            client,
            capability_key=capability,
            model_ids=model_ids,
            prompt_id=prompts.get(capability),
            max_retries=(
                route_max_retries
                if capability == "script_generation"
                else 0
            ),
            max_cost_micros=route_max_cost_micros,
            timeout_ms=route_timeout_ms,
            key=key,
        )

    account_id, _ = create_account(
        client,
        name=f"P0-H {key} 账号",
        idempotency_key=f"idem_p0h_account_{key}",
    )
    source = client.post(
        f"/api/v1/accounts/{account_id}/knowledge/sources",
        headers=mutation_headers(
            idempotency_key=f"idem_p0h_source_{key}"
        ),
        json={
            "kind": "text",
            "sourceMode": "text",
            "title": "受控账号知识",
            "text": "该账号面向短视频创作者，表达直接，避免夸张承诺。",
        },
    )
    assert source.status_code == 201, source.text
    source_id = str(source.json()["data"]["id"])
    submitted = client.post(
        f"/api/v1/accounts/{account_id}/knowledge/index-jobs",
        headers=mutation_headers(
            idempotency_key=f"idem_p0h_index_{key}"
        ),
        json={"sourceIds": [source_id]},
    )
    assert submitted.status_code == 202, submitted.text
    indexed = wait_account_task(
        client,
        account_id=account_id,
        task_id=str(submitted.json()["data"]["taskId"]),
    )
    assert indexed["status"] == "completed", indexed
    snapshot = client.post(
        f"/api/v1/accounts/{account_id}/knowledge/snapshots",
        headers=mutation_headers(
            idempotency_key=f"idem_p0h_snapshot_{key}"
        ),
        json={"sourceIds": [source_id], "label": "P0-H 执行快照"},
    )
    assert snapshot.status_code == 201, snapshot.text
    knowledge_snapshot_id = str(snapshot.json()["data"]["id"])

    recipe = client.post(
        f"/api/v1/accounts/{account_id}/ai-recipe/versions",
        headers={
            "If-Match": str(account_revision(client, account_id)),
            "Idempotency-Key": f"idem_p0h_recipe_{key}",
        },
        json={
            "name": "P0-H 真实执行配方",
            "routeOverrides": {},
            "visualStyle": {},
            "voiceProfileRef": None,
            "compositionTemplateRef": None,
            "costPolicy": {},
            "fallbackPolicy": {},
        },
    )
    assert recipe.status_code == 201, recipe.text
    validated = client.post(
        f"/api/v1/accounts/{account_id}/ai-recipe/versions/1/validate",
        headers={"Idempotency-Key": f"idem_p0h_recipe_validate_{key}"},
    )
    assert validated.status_code == 200, validated.text
    assert validated.json()["data"]["validationStatus"] == "valid"
    activated = client.post(
        f"/api/v1/accounts/{account_id}/ai-recipe/versions/1/activate",
        headers={
            "If-Match": str(validated.json()["meta"]["revision"]),
            "Idempotency-Key": f"idem_p0h_recipe_activate_{key}",
        },
    )
    assert activated.status_code == 200, activated.text
    return P0HExecutionFixture(
        account_id=account_id,
        account_revision=account_revision(client, account_id),
        recipe_version_id=str(activated.json()["data"]["activeVersionId"]),
        knowledge_snapshot_id=knowledge_snapshot_id,
        provider_ids=tuple(str(item["id"]) for item in providers),
        model_ids=model_ids,
    )


def execution_payload(
    fixture: P0HExecutionFixture,
    *,
    max_cost_micros: int | None = None,
    allow_fallback: bool = True,
) -> dict[str, object]:
    policy: dict[str, object] = {"allowFallback": allow_fallback}
    if max_cost_micros is not None:
        policy["maxCostMicros"] = max_cost_micros
    return {
        "capabilityKey": "script_generation",
        "knowledgeSnapshotId": fixture.knowledge_snapshot_id,
        "recipeVersionId": fixture.recipe_version_id,
        "input": {"topic": "如何建立稳定的短视频选题流程"},
        "executionPolicy": policy,
    }


def wait_execution(
    client: TestClient,
    *,
    account_id: str,
    execution_id: str,
    timeout_seconds: float = 8.0,
) -> dict[str, object]:
    import time

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        response = client.get(
            f"/api/v1/accounts/{account_id}/ai-executions/{execution_id}"
        )
        assert response.status_code == 200, response.text
        data = dict(response.json()["data"])
        if data["status"] in {"completed", "failed"}:
            return data
        time.sleep(0.02)
    raise AssertionError(f"AI 执行未在时限内结束：{execution_id}")


def _create_provider_and_model(
    client: TestClient,
    *,
    base_url: str,
    credential: str,
    key: str,
) -> tuple[dict[str, object], dict[str, object]]:
    provider_response = client.post(
        "/api/v1/system/providers",
        headers={"Idempotency-Key": f"idem_p0h_provider_{key}"},
        json={
            "name": f"P0-H {key}",
            "adapterType": "openai_compatible",
            "baseUrl": base_url,
            "region": None,
            "proxyRef": None,
            "timeoutMs": 5_000,
            "maxConcurrency": 2,
            "enabled": True,
            "extraParams": {"protocolVariant": "chat_completions"},
            "costPolicy": {
                "pricingRevision": 1,
                "inputMicrosPerMillionUnits": 1_000_000,
                "outputMicrosPerMillionUnits": 2_000_000,
            },
        },
    )
    assert provider_response.status_code == 201, provider_response.text
    provider = dict(provider_response.json()["data"])
    credential_response = client.put(
        f"/api/v1/system/providers/{provider['id']}/credential",
        headers={"If-Match": str(provider["revision"])},
        json={"credential": credential},
    )
    assert credential_response.status_code == 200, credential_response.text
    model_response = client.post(
        "/api/v1/system/models",
        headers={"Idempotency-Key": f"idem_p0h_model_{key}"},
        json={
            "providerProfileId": provider["id"],
            "modelId": "p0h-text-model",
            "displayName": f"P0-H {key} 模型",
            "enabled": True,
            "baseLimits": {},
        },
    )
    assert model_response.status_code == 201, model_response.text
    return provider, dict(model_response.json()["data"])


def _seed_capabilities(
    client: TestClient,
    *,
    provider_id: str,
    model_id: str,
    key: str,
) -> None:
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    with session(client) as database:
        provider = database.get(ProviderProfile, provider_id)
        model = database.get(ModelProfile, model_id)
        assert provider is not None and provider.active_revision_id is not None
        assert model is not None and model.active_revision_id is not None
        for index, capability_key in enumerate(
            ("script_generation", "storyboard_generation", "text_to_video")
        ):
            digest = hashlib.sha256(
                f"{key}:{capability_key}".encode("utf-8")
            ).hexdigest()
            task_id = f"task_p0h_{digest[:24]}"
            database.add(
                RuntimeTask(
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
            )
            database.flush()
            database.add(
                ModelCapability(
                    id=f"cap_p0h_{digest[:24]}",
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
                    id=f"pval_p0h_{digest[:24]}",
                    provider_profile_id=provider_id,
                    provider_revision=int(provider.revision),
                    model_profile_id=model_id,
                    model_revision=int(model.revision),
                    capability_key=capability_key,
                    stage="real_small_call",
                    status="verified",
                    task_id=task_id,
                    request_hash=digest,
                    response_hash=digest,
                    response_id_hash=digest,
                    usage_json=(
                        '{"inputUnits":1,"outputUnits":1,"totalUnits":2}'
                    ),
                    duration_ms=index + 1,
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
    capability_key: str,
    key: str,
) -> str:
    profile_key = f"p0h-{key}"
    prompt = create_prompt(
        client,
        profile_key=profile_key,
        capability_key=capability_key,
        system_prompt="你是短视频策划助手，只输出 JSON。",
        task_template="根据受控输入与账号知识生成结果。",
    )
    activated = client.post(
        f"/api/v1/system/prompt-profiles/{profile_key}/versions/1/activate",
        headers={
            "If-Match": str(prompt["revision"]),
            "Idempotency-Key": f"idem_p0h_prompt_activate_{key}",
        },
    )
    assert activated.status_code == 200, activated.text
    return str(activated.json()["data"]["activeVersionId"])


def _create_active_route(
    client: TestClient,
    *,
    capability_key: str,
    model_ids: tuple[str, ...],
    prompt_id: str | None,
    max_retries: int,
    max_cost_micros: int,
    timeout_ms: int,
    key: str,
) -> None:
    created = client.post(
        f"/api/v1/system/capability-routes/{capability_key}/revisions",
        headers={
            "If-Match": "0",
            "Idempotency-Key": f"idem_p0h_route_{key}_{capability_key}",
        },
        json={
            "promptProfileId": prompt_id,
            "candidates": [
                {"modelProfileId": model_id} for model_id in model_ids
            ],
            "timeoutMs": timeout_ms,
            "maxRetries": max_retries,
            "retryPolicy": {
                "maxOutputUnits": 16,
                "knowledgeMaxInputUnits": 128,
                "requireReportedUsage": True,
            },
            "maxConcurrency": 2,
            "maxCostMicros": max_cost_micros,
            "currency": "USD",
            "enabled": True,
        },
    )
    assert created.status_code == 201, created.text
    validated = client.post(
        f"/api/v1/system/capability-routes/{capability_key}/revisions/1/validate",
        headers={
            "Idempotency-Key": (
                f"idem_p0h_route_validate_{key}_{capability_key}"
            )
        },
    )
    assert validated.status_code == 200, validated.text
    assert validated.json()["data"]["status"] == "valid"
    activated = client.post(
        f"/api/v1/system/capability-routes/{capability_key}/revisions/1/activate",
        headers={
            "If-Match": str(validated.json()["meta"]["revision"]),
            "Idempotency-Key": (
                f"idem_p0h_route_activate_{key}_{capability_key}"
            ),
        },
    )
    assert activated.status_code == 200, activated.text


__all__ = [
    "P0HExecutionFixture",
    "enable_ai_execution",
    "execution_payload",
    "seed_execution_chain",
    "wait_execution",
]
