from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select

from domain.models.ai_configuration_v1 import AccountAIRecipe, PromptProfile
from tests.runtime.p0e_ai_integration_support import (
    create_account,
    create_prompt,
    recipe_payload,
    session,
)
from tests.runtime.test_p0_e_ai_provider_model_route_chain import (
    seed_verified_routes,
)


def test_prompt_versions_are_immutable_and_idempotent(
    licensed_runtime_client: TestClient,
) -> None:
    prompt = create_prompt(
        licensed_runtime_client,
        profile_key="prompt-versioned",
        capability_key="script_generation",
        system_prompt="系统正文 v1",
        task_template="任务正文 v1",
    )
    response = licensed_runtime_client.post(
        "/api/v1/system/prompt-profiles/prompt-versioned/versions",
        headers={
            "If-Match": str(prompt["revision"]),
            "Idempotency-Key": "idem-prompt-version-two",
        },
        json={
            "name": "Prompt v2",
            "systemPrompt": "系统正文 v2",
            "taskTemplate": "任务正文 v2",
            "variablesSchema": {"type": "object"},
            "outputSchema": {"type": "object"},
            "visualStylePrefix": "",
            "safetyConstraints": {},
            "createdFromVersion": 1,
        },
    )
    assert response.status_code == 201, response.text
    replay = licensed_runtime_client.post(
        "/api/v1/system/prompt-profiles/prompt-versioned/versions",
        headers={
            "If-Match": str(prompt["revision"]),
            "Idempotency-Key": "idem-prompt-version-two",
        },
        json={
            "name": "Prompt v2",
            "systemPrompt": "系统正文 v2",
            "taskTemplate": "任务正文 v2",
            "variablesSchema": {"type": "object"},
            "outputSchema": {"type": "object"},
            "visualStylePrefix": "",
            "safetyConstraints": {},
            "createdFromVersion": 1,
        },
    )
    assert replay.status_code == 201
    assert replay.json()["data"]["id"] == response.json()["data"]["id"]

    with session(licensed_runtime_client) as database:
        versions = database.scalars(
            select(PromptProfile)
            .where(PromptProfile.profile_key == "prompt-versioned")
            .order_by(PromptProfile.version)
        ).all()
    assert [(row.version, row.system_prompt) for row in versions] == [
        (1, "系统正文 v1"),
        (2, "系统正文 v2"),
    ]
    assert versions[0].content_hash != versions[1].content_hash

    activated = licensed_runtime_client.post(
        "/api/v1/system/prompt-profiles/"
        "prompt-versioned/versions/1/activate",
        headers={
            "If-Match": "2",
            "Idempotency-Key": "idem-prompt-reactivate-old",
        },
    )
    assert activated.status_code == 200, activated.text
    assert activated.json()["data"]["revision"] == 3

    stale = licensed_runtime_client.post(
        "/api/v1/system/prompt-profiles/"
        "prompt-versioned/versions/2/activate",
        headers={
            "If-Match": "2",
            "Idempotency-Key": "idem-prompt-stale-aggregate",
        },
    )
    assert stale.status_code == 412


def test_composition_template_versions_preserve_source_content(
    licensed_runtime_client: TestClient,
) -> None:
    created = licensed_runtime_client.post(
        "/api/v1/system/composition-templates",
        headers={"Idempotency-Key": "idem-template-versioned"},
        json={
            "templateKey": "template-versioned",
            "name": "合成模板 v1",
            "templateType": "mixed_media",
            "aspectRatios": ["9:16"],
            "parameterSchema": {"type": "object"},
            "compositionSpecTemplate": {"layout": "v1"},
            "compatibleCapabilities": {},
            "previewAssetRef": None,
        },
    )
    assert created.status_code == 201, created.text
    revision = int(created.json()["data"]["revision"])

    second = licensed_runtime_client.post(
        "/api/v1/system/composition-templates/template-versioned/versions",
        headers={
            "If-Match": str(revision),
            "Idempotency-Key": "idem-template-version-two",
        },
        json={
            "name": "合成模板 v2",
            "aspectRatios": ["9:16"],
            "parameterSchema": {"type": "object"},
            "compositionSpecTemplate": {"layout": "v2"},
            "compatibleCapabilities": {},
            "previewAssetRef": None,
            "createdFromVersion": 1,
        },
    )
    assert second.status_code == 201, second.text

    first_read = licensed_runtime_client.get(
        "/api/v1/system/composition-templates/"
        "template-versioned/versions/1"
    )
    second_read = licensed_runtime_client.get(
        "/api/v1/system/composition-templates/"
        "template-versioned/versions/2"
    )
    assert first_read.status_code == 200
    assert second_read.status_code == 200
    assert first_read.json()["data"]["compositionSpecTemplate"] == {
        "layout": "v1"
    }
    assert second_read.json()["data"]["compositionSpecTemplate"] == {
        "layout": "v2"
    }
    assert (
        first_read.json()["data"]["contentHash"]
        != second_read.json()["data"]["contentHash"]
    )

    activated = licensed_runtime_client.post(
        "/api/v1/system/composition-templates/"
        "template-versioned/versions/1/activate",
        headers={
            "If-Match": "2",
            "Idempotency-Key": "idem-template-reactivate-old",
        },
    )
    assert activated.status_code == 200, activated.text
    assert activated.json()["data"]["revision"] == 3

    stale = licensed_runtime_client.post(
        "/api/v1/system/composition-templates/"
        "template-versioned/versions/2/activate",
        headers={
            "If-Match": "2",
            "Idempotency-Key": "idem-template-stale-aggregate",
        },
    )
    assert stale.status_code == 412


def test_recipe_reads_and_versions_are_account_isolated(
    licensed_runtime_client: TestClient,
) -> None:
    account_a, revision_a = create_account(
        licensed_runtime_client,
        key="recipe-a",
    )
    account_b, _ = create_account(
        licensed_runtime_client,
        key="recipe-b",
    )
    created = licensed_runtime_client.post(
        f"/api/v1/accounts/{account_a}/ai-recipe/versions",
        headers={
            "If-Match": str(revision_a),
            "Idempotency-Key": "idem-recipe-account-a",
        },
        json=recipe_payload(name="账号 A 配方"),
    )
    assert created.status_code == 201, created.text
    assert created.json()["meta"]["revision"] == revision_a + 1
    assert created.json()["data"]["revision"] == 1

    replay = licensed_runtime_client.post(
        f"/api/v1/accounts/{account_a}/ai-recipe/versions",
        headers={
            "If-Match": str(revision_a),
            "Idempotency-Key": "idem-recipe-account-a",
        },
        json=recipe_payload(name="账号 A 配方"),
    )
    assert replay.status_code == 201, replay.text
    assert replay.json()["meta"]["revision"] == revision_a + 1

    response = licensed_runtime_client.get(
        f"/api/v1/accounts/{account_b}/ai-recipe/versions"
    )
    assert response.status_code == 200
    assert response.json()["data"]["items"] == []
    with session(licensed_runtime_client) as database:
        assert database.scalar(
            select(AccountAIRecipe).where(
                AccountAIRecipe.account_id == account_b
            )
        ) is None


def test_system_ai_revision_drift_blocks_recipe_activation(
    licensed_runtime_client: TestClient,
) -> None:
    provider, _ = seed_verified_routes(
        licensed_runtime_client,
        key="revision-drift",
    )
    account_id, account_revision = create_account(
        licensed_runtime_client,
        key="revision-drift",
    )
    created = licensed_runtime_client.post(
        f"/api/v1/accounts/{account_id}/ai-recipe/versions",
        headers={
            "If-Match": str(account_revision),
            "Idempotency-Key": "idem-recipe-drift-create",
        },
        json=recipe_payload(name="修订漂移配方"),
    )
    assert created.status_code == 201, created.text

    validation = licensed_runtime_client.post(
        f"/api/v1/accounts/{account_id}/ai-recipe/versions/1/validate",
        headers={"Idempotency-Key": "idem-recipe-drift-validate"},
    )
    assert validation.status_code == 200, validation.text
    assert validation.json()["data"]["validationStatus"] == "valid"
    account_revision = int(validation.json()["meta"]["revision"])

    provider_update = licensed_runtime_client.patch(
        f"/api/v1/system/providers/{provider['id']}",
        headers={"If-Match": str(provider["revision"])},
        json={"name": "修订已变化 Provider"},
    )
    assert provider_update.status_code == 200, provider_update.text

    validation_replay = licensed_runtime_client.post(
        f"/api/v1/accounts/{account_id}/ai-recipe/versions/1/validate",
        headers={"Idempotency-Key": "idem-recipe-drift-validate"},
    )
    assert validation_replay.status_code == 200
    assert validation_replay.json()["data"] == validation.json()["data"]
    assert (
        validation_replay.json()["meta"]["revision"]
        == validation.json()["meta"]["revision"]
    )

    activation = licensed_runtime_client.post(
        f"/api/v1/accounts/{account_id}/ai-recipe/versions/1/activate",
        headers={
            "If-Match": str(account_revision),
            "Idempotency-Key": "idem-recipe-drift-activate",
        },
    )
    assert activation.status_code == 422
    assert activation.json()["error_code"] == "AI_RECIPE_INVALID"
    with session(licensed_runtime_client) as database:
        recipe = database.scalar(
            select(AccountAIRecipe).where(
                AccountAIRecipe.account_id == account_id,
                AccountAIRecipe.version == 1,
            )
        )
        assert recipe is not None
        assert recipe.status == "draft"
