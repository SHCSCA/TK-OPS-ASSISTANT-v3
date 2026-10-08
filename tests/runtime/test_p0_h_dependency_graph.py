from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import select

from domain.models.ai_configuration_v1 import (
    AccountAIRecipe,
    CapabilityRouteRevision,
    CompositionTemplateProfile,
    ModelCapability,
    ModelProfile,
    ProviderProfile,
)
from domain.models.ai_execution_evidence import AIProviderValidationRun
from domain.models.ai_execution_snapshot import AIDependencySnapshot
from domain.models.runtime_task import RuntimeTask
from tests.runtime.p0e_ai_integration_support import (
    create_account,
    create_model,
    create_prompt,
    create_provider,
    recipe_payload,
    session,
)


def test_route_revision_activation_rechecks_immutable_dependency_hash(
    licensed_runtime_client: TestClient,
) -> None:
    provider, model = _create_validated_model(
        licensed_runtime_client,
        key="route-drift",
        capabilities=("script_generation",),
    )
    prompt_id = _activate_prompt(
        licensed_runtime_client,
        key="route-drift",
        capability_key="script_generation",
    )
    draft = _create_route_revision(
        licensed_runtime_client,
        capability_key="script_generation",
        model_id=str(model["id"]),
        prompt_id=prompt_id,
        expected_revision=0,
        key="route-drift",
    )
    validated = licensed_runtime_client.post(
        "/api/v1/system/capability-routes/script_generation/"
        "revisions/1/validate",
        headers={"Idempotency-Key": "idem-route-drift-validate"},
    )
    assert validated.status_code == 200, validated.text
    validation = validated.json()["data"]
    assert validation["status"] == "valid"
    original_hash = validation["dependencySnapshot"]["contentHash"]

    changed = licensed_runtime_client.patch(
        f"/api/v1/system/providers/{provider['id']}",
        headers={"If-Match": str(provider["revision"])},
        json={"name": "漂移后的 Provider"},
    )
    assert changed.status_code == 200, changed.text

    blocked = licensed_runtime_client.post(
        "/api/v1/system/capability-routes/script_generation/"
        "revisions/1/activate",
        headers={
            "If-Match": str(validated.json()["meta"]["revision"]),
            "Idempotency-Key": "idem-route-drift-activate",
        },
    )
    assert blocked.status_code == 409, blocked.text
    assert blocked.json()["error_code"] == "AI_DEPENDENCY_INVALID"

    preview = licensed_runtime_client.get(
        "/api/v1/system/ai-dependencies",
        params={
            "ownerType": "route",
            "ownerId": draft["capabilityRouteId"],
            "ownerRevision": 1,
        },
    )
    assert preview.status_code == 200, preview.text
    preview_data = preview.json()["data"]
    assert preview_data["status"] == "invalid"
    assert preview_data["issues"][0]["code"] == (
        "AI_PROVIDER_REAL_VALIDATION_REQUIRED"
    )
    assert preview_data["contentHash"] != original_hash

    with session(licensed_runtime_client) as database:
        stored = database.scalar(select(AIDependencySnapshot))
        revision = database.scalar(select(CapabilityRouteRevision))
        assert stored is not None
        assert revision is not None
        assert stored.status == "valid"
        assert stored.content_hash == original_hash
        assert revision.status == "draft"


def test_legacy_route_put_preserves_invalid_draft_and_marks_adapter(
    licensed_runtime_client: TestClient,
) -> None:
    provider = create_provider(licensed_runtime_client, key="legacy-draft")
    model = create_model(
        licensed_runtime_client,
        provider_id=str(provider["id"]),
        key="legacy-draft",
    )
    prompt_id = _activate_prompt(
        licensed_runtime_client,
        key="legacy-draft",
        capability_key="script_generation",
    )
    response = licensed_runtime_client.put(
        "/api/v1/system/capability-routes/script_generation",
        headers={
            "If-Match": "0",
            "Idempotency-Key": "idem-legacy-invalid-draft",
        },
        json={
            "primaryModelProfileId": model["id"],
            "fallbackModelProfileId": None,
            "promptProfileId": prompt_id,
            "enabled": True,
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["data"]["validationStatus"] == "invalid"
    assert payload["meta"]["compatibilityAdapter"] is True
    assert payload["data"]["validationIssues"][0]["code"] == (
        "AI_PROVIDER_REAL_VALIDATION_REQUIRED"
    )
    revisions = licensed_runtime_client.get(
        "/api/v1/system/capability-routes/script_generation/revisions"
    )
    assert revisions.status_code == 200, revisions.text
    assert revisions.json()["data"]["items"][0]["status"] == "draft"


def test_recipe_and_template_versions_receive_dependency_snapshots(
    licensed_runtime_client: TestClient,
) -> None:
    _, model = _create_validated_model(
        licensed_runtime_client,
        key="recipe-chain",
        capabilities=(
            "script_generation",
            "storyboard_generation",
            "text_to_video",
        ),
    )
    for capability_key in (
        "script_generation",
        "storyboard_generation",
        "text_to_video",
    ):
        prompt_id = (
            _activate_prompt(
                licensed_runtime_client,
                key=f"recipe-{capability_key}",
                capability_key=capability_key,
            )
            if capability_key != "text_to_video"
            else None
        )
        _create_validate_activate_route(
            licensed_runtime_client,
            capability_key=capability_key,
            model_id=str(model["id"]),
            prompt_id=prompt_id,
        )

    template = licensed_runtime_client.post(
        "/api/v1/system/composition-templates",
        headers={"Idempotency-Key": "idem-h2-template-create"},
        json={
            "templateKey": "h2-template",
            "name": "H2 合成模板",
            "templateType": "mixed_media",
            "aspectRatios": ["9:16"],
            "parameterSchema": {"type": "object"},
            "compositionSpecTemplate": {"layout": "vertical"},
            "compatibleCapabilities": {"required": ["text_to_video"]},
            "previewAssetRef": None,
        },
    )
    assert template.status_code == 201, template.text
    template_validation = licensed_runtime_client.post(
        "/api/v1/system/composition-templates/h2-template/versions/1/validate",
        headers={"Idempotency-Key": "idem-h2-template-validate"},
    )
    assert template_validation.status_code == 200, template_validation.text
    assert template_validation.json()["data"]["dependencySnapshot"][
        "status"
    ] == "valid"
    template_activation = licensed_runtime_client.post(
        "/api/v1/system/composition-templates/h2-template/versions/1/activate",
        headers={
            "If-Match": str(template_validation.json()["meta"]["revision"]),
            "Idempotency-Key": "idem-h2-template-activate",
        },
    )
    assert template_activation.status_code == 200, template_activation.text
    template_id = template_activation.json()["data"]["activeVersionId"]

    account_id, account_revision = create_account(
        licensed_runtime_client,
        key="h2-recipe",
    )
    body = recipe_payload(name="H2 账号配方")
    body["compositionTemplateRef"] = template_id
    created_recipe = licensed_runtime_client.post(
        f"/api/v1/accounts/{account_id}/ai-recipe/versions",
        headers={
            "If-Match": str(account_revision),
            "Idempotency-Key": "idem-h2-recipe-create",
        },
        json=body,
    )
    assert created_recipe.status_code == 201, created_recipe.text
    recipe_validation = licensed_runtime_client.post(
        f"/api/v1/accounts/{account_id}/ai-recipe/versions/1/validate",
        headers={"Idempotency-Key": "idem-h2-recipe-validate"},
    )
    assert recipe_validation.status_code == 200, recipe_validation.text
    assert recipe_validation.json()["data"]["dependencySnapshot"][
        "status"
    ] == "valid"
    activated_recipe = licensed_runtime_client.post(
        f"/api/v1/accounts/{account_id}/ai-recipe/versions/1/activate",
        headers={
            "If-Match": str(recipe_validation.json()["meta"]["revision"]),
            "Idempotency-Key": "idem-h2-recipe-activate",
        },
    )
    assert activated_recipe.status_code == 200, activated_recipe.text

    with session(licensed_runtime_client) as database:
        template_row = database.scalar(select(CompositionTemplateProfile))
        recipe_row = database.scalar(select(AccountAIRecipe))
        assert template_row is not None
        assert recipe_row is not None
        assert template_row.dependency_snapshot_id is not None
        assert recipe_row.dependency_snapshot_id is not None


def _create_validated_model(
    client: TestClient,
    *,
    key: str,
    capabilities: tuple[str, ...],
) -> tuple[dict[str, object], dict[str, object]]:
    provider = create_provider(client, key=key)
    model = create_model(
        client,
        provider_id=str(provider["id"]),
        key=key,
    )
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    with session(client) as database:
        provider_row = database.get(ProviderProfile, provider["id"])
        model_row = database.get(ModelProfile, model["id"])
        assert provider_row is not None
        assert model_row is not None
        for index, capability_key in enumerate(capabilities):
            task_id = f"task_h2_{key}_{index}"
            digest = hashlib.sha256(task_id.encode("utf-8")).hexdigest()
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
                    id=f"cap_h2_{key}_{index}",
                    model_profile_id=str(model["id"]),
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
                    id=f"pval_h2_{key}_{index}",
                    provider_profile_id=str(provider["id"]),
                    provider_revision=int(provider_row.revision),
                    model_profile_id=str(model["id"]),
                    model_revision=int(model_row.revision),
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
    return provider, model


def _activate_prompt(
    client: TestClient,
    *,
    key: str,
    capability_key: str,
) -> str:
    prompt = create_prompt(
        client,
        profile_key=f"prompt-{key}",
        capability_key=capability_key,
        system_prompt="你是短视频策划助手。",
        task_template="输出受控结果。",
    )
    activated = client.post(
        f"/api/v1/system/prompt-profiles/prompt-{key}/versions/1/activate",
        headers={
            "If-Match": str(prompt["revision"]),
            "Idempotency-Key": f"idem-prompt-{key}-activate",
        },
    )
    assert activated.status_code == 200, activated.text
    return str(activated.json()["data"]["activeVersionId"])


def _create_route_revision(
    client: TestClient,
    *,
    capability_key: str,
    model_id: str,
    prompt_id: str | None,
    expected_revision: int,
    key: str,
) -> dict[str, object]:
    response = client.post(
        f"/api/v1/system/capability-routes/{capability_key}/revisions",
        headers={
            "If-Match": str(expected_revision),
            "Idempotency-Key": f"idem-{key}-route-create",
        },
        json={
            "promptProfileId": prompt_id,
            "candidates": [{"modelProfileId": model_id}],
            "timeoutMs": 60_000,
            "maxRetries": 1,
            "retryPolicy": {},
            "maxConcurrency": 1,
            "maxCostMicros": 1_000_000,
            "currency": "USD",
            "enabled": True,
        },
    )
    assert response.status_code == 201, response.text
    return dict(response.json()["data"])


def _create_validate_activate_route(
    client: TestClient,
    *,
    capability_key: str,
    model_id: str,
    prompt_id: str | None,
) -> None:
    _create_route_revision(
        client,
        capability_key=capability_key,
        model_id=model_id,
        prompt_id=prompt_id,
        expected_revision=0,
        key=capability_key,
    )
    validated = client.post(
        f"/api/v1/system/capability-routes/{capability_key}/revisions/1/validate",
        headers={"Idempotency-Key": f"idem-{capability_key}-route-validate"},
    )
    assert validated.status_code == 200, validated.text
    assert validated.json()["data"]["status"] == "valid"
    activated = client.post(
        f"/api/v1/system/capability-routes/{capability_key}/revisions/1/activate",
        headers={
            "If-Match": str(validated.json()["meta"]["revision"]),
            "Idempotency-Key": f"idem-{capability_key}-route-activate",
        },
    )
    assert activated.status_code == 200, activated.text
