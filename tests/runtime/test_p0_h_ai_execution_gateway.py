from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from errors import ErrorCode
from services.ai_execution_v1.concurrency import AIExecutionConcurrencyGate
from services.ai_execution_v1.types import (
    ProviderCallError,
    ProviderFailureCategory,
)
from tests.runtime.p0h_execution_support import (
    P0HExecutionFixture,
    execution_payload,
    seed_execution_chain,
    wait_execution,
)
from tests.runtime.p0h_provider_test_server import (
    ControlledProviderScenario,
    ControlledProviderServer,
)


def test_real_gateway_success_output_evidence_and_same_snapshot_retry(
    licensed_runtime_client: TestClient,
) -> None:
    scenario = ControlledProviderScenario()
    with ControlledProviderServer(scenario) as provider:
        fixture = seed_execution_chain(
            licensed_runtime_client,
            base_urls=(provider.base_url,),
            credentials=(scenario.token,),
            key="success",
        )
        preflight = licensed_runtime_client.post(
            f"/api/v1/accounts/{fixture.account_id}/ai-executions/preflight",
            headers={"If-Match": str(fixture.account_revision)},
            json=_preflight_payload(fixture),
        )
        assert preflight.status_code == 200, preflight.text
        assert preflight.json()["data"]["ready"] is True
        assert preflight.json()["data"]["candidateCount"] == 1

        created = _create_execution(
            licensed_runtime_client,
            fixture,
            key="success",
        )
        completed = wait_execution(
            licensed_runtime_client,
            account_id=fixture.account_id,
            execution_id=str(created["executionId"]),
        )
        assert completed["status"] == "completed"
        assert completed["completionKind"] == "succeeded"
        assert len(completed["jobs"]) == 1
        assert completed["jobs"][0]["completionKind"] == "succeeded"
        assert completed["usage"][0]["inputUnits"] == scenario.input_units
        assert completed["costStatus"] == "estimated"
        assert completed["outputCount"] == 1

        output_id = str(completed["outputs"][0]["id"])
        output = licensed_runtime_client.get(
            (
                f"/api/v1/accounts/{fixture.account_id}/ai-executions/"
                f"{created['executionId']}/outputs/{output_id}"
            )
        )
        assert output.status_code == 200, output.text
        assert output.headers["cache-control"] == "private, no-store"
        assert output.json()["data"]["content"] == scenario.output_text
        evidence = licensed_runtime_client.get(
            (
                f"/api/v1/accounts/{fixture.account_id}/ai-executions/"
                f"{created['executionId']}/evidence"
            )
        )
        assert evidence.status_code == 200, evidence.text
        evidence_data = evidence.json()["data"]
        assert evidence_data["capabilityKey"] == "script_generation"
        assert evidence_data["finalStatus"] == "succeeded"
        assert evidence_data["usageReported"] is True
        assert evidence_data["provider"]["adapterType"] == "openai_compatible"
        assert evidence_data["provider"]["validationStage"] == "real_small_call"
        assert evidence_data["provider"]["validationStatus"] == "verified"
        assert len(evidence_data["provider"]["providerRefHash"]) == 64
        assert len(evidence_data["provider"]["modelIdHash"]) == 64
        assert len(evidence_data["provider"]["validationRunHash"]) == 64
        assert len(evidence_data["responseIdHash"]) == 64
        assert scenario.output_text not in evidence.text
        assert scenario.token not in evidence.text

        retried = licensed_runtime_client.post(
            (
                f"/api/v1/accounts/{fixture.account_id}/ai-executions/"
                f"{created['executionId']}/retry"
            ),
            headers={"Idempotency-Key": "idem_p0h_retry_success"},
            json={"mode": "same_snapshot"},
        )
        assert retried.status_code == 202, retried.text
        retried_data = dict(retried.json()["data"])
        assert retried_data["snapshotHash"] == created["snapshotHash"]
        retry_completed = wait_execution(
            licensed_runtime_client,
            account_id=fixture.account_id,
            execution_id=str(retried_data["executionId"]),
        )
        assert retry_completed["retryOfExecutionId"] == created["executionId"]
        assert retry_completed["status"] == "completed"
        assert len(_posts(scenario)) == 2


def test_gateway_retries_429_once_then_succeeds(
    licensed_runtime_client: TestClient,
) -> None:
    scenario = ControlledProviderScenario(
        response_statuses=[429],
        error_marker="rate-limit-marker-must-not-leak",
        retry_after_seconds=0,
    )
    with ControlledProviderServer(scenario) as provider:
        fixture = seed_execution_chain(
            licensed_runtime_client,
            base_urls=(provider.base_url,),
            credentials=(scenario.token,),
            key="retry",
            route_max_retries=1,
        )
        created = _create_execution(
            licensed_runtime_client,
            fixture,
            key="retry",
        )
        completed = wait_execution(
            licensed_runtime_client,
            account_id=fixture.account_id,
            execution_id=str(created["executionId"]),
        )
        assert completed["status"] == "completed"
        assert [item["retryIndex"] for item in completed["jobs"]] == [0, 1]
        assert completed["jobs"][0]["status"] == "failed"
        assert completed["jobs"][1]["status"] == "completed"
        assert len(_posts(scenario)) == 2
        assert scenario.error_marker not in str(completed)


def test_gateway_falls_back_in_frozen_candidate_order(
    licensed_runtime_client: TestClient,
) -> None:
    first = ControlledProviderScenario(
        error_status=503,
        error_marker="first-provider-body",
    )
    second = ControlledProviderScenario(token="p0h-second-token")
    with (
        ControlledProviderServer(first) as first_provider,
        ControlledProviderServer(second) as second_provider,
    ):
        fixture = seed_execution_chain(
            licensed_runtime_client,
            base_urls=(first_provider.base_url, second_provider.base_url),
            credentials=(first.token, second.token),
            key="fallback",
        )
        created = _create_execution(
            licensed_runtime_client,
            fixture,
            key="fallback",
        )
        completed = wait_execution(
            licensed_runtime_client,
            account_id=fixture.account_id,
            execution_id=str(created["executionId"]),
        )
        assert completed["status"] == "completed"
        assert [item["fallbackIndex"] for item in completed["jobs"]] == [0, 1]
        assert len(_posts(first)) == 1
        assert len(_posts(second)) == 1
        assert first.error_marker not in str(completed)


def test_hard_budget_blocks_preflight_and_quarantines_actual_overrun(
    licensed_runtime_client: TestClient,
) -> None:
    scenario = ControlledProviderScenario(
        input_units=1_000,
        output_units=1_000,
    )
    with ControlledProviderServer(scenario) as provider:
        fixture = seed_execution_chain(
            licensed_runtime_client,
            base_urls=(provider.base_url,),
            credentials=(scenario.token,),
            key="cost",
        )
        blocked = licensed_runtime_client.post(
            f"/api/v1/accounts/{fixture.account_id}/ai-executions/preflight",
            headers={"If-Match": str(fixture.account_revision)},
            json=_preflight_payload(fixture, max_cost_micros=1),
        )
        assert blocked.status_code == 409, blocked.text
        assert blocked.json()["error_code"] == ErrorCode.AI_COST_LIMIT_EXCEEDED
        assert _posts(scenario) == []

        created = _create_execution(
            licensed_runtime_client,
            fixture,
            key="cost-overrun",
            max_cost_micros=500,
        )
        failed = wait_execution(
            licensed_runtime_client,
            account_id=fixture.account_id,
            execution_id=str(created["executionId"]),
        )
        assert failed["status"] == "failed"
        assert failed["errorCode"] == ErrorCode.AI_COST_LIMIT_EXCEEDED
        assert failed["costMicros"] == 3_000
        assert failed["outputs"][0]["quarantined"] is True
        output_id = str(failed["outputs"][0]["id"])
        output = licensed_runtime_client.get(
            (
                f"/api/v1/accounts/{fixture.account_id}/ai-executions/"
                f"{created['executionId']}/outputs/{output_id}"
            )
        )
        assert output.status_code == 409
        assert output.json()["error_code"] == ErrorCode.AI_COST_LIMIT_EXCEEDED


def test_concurrency_gate_has_independent_cancellable_queue_timeout() -> None:
    async def exercise() -> None:
        gate = AIExecutionConcurrencyGate(1)
        started = asyncio.Event()
        release = asyncio.Event()

        async def holder() -> None:
            async with gate.lease(
                account_id="acct_gate_a",
                route_provider_key="route:provider",
                limit=1,
                timeout_seconds=1,
                cancellation_probe=lambda: None,
            ):
                started.set()
                await release.wait()

        task = asyncio.create_task(holder())
        await started.wait()
        with pytest.raises(ProviderCallError) as raised:
            async with gate.lease(
                account_id="acct_gate_b",
                route_provider_key="route:provider",
                limit=1,
                timeout_seconds=0.02,
                cancellation_probe=lambda: None,
            ):
                raise AssertionError("并发门禁不应放行")
        assert raised.value.category is ProviderFailureCategory.TIMEOUT
        assert raised.value.request_sent is False
        release.set()
        await task

    asyncio.run(exercise())


def _create_execution(
    client: TestClient,
    fixture: P0HExecutionFixture,
    *,
    key: str,
    max_cost_micros: int | None = None,
) -> dict[str, object]:
    response = client.post(
        f"/api/v1/accounts/{fixture.account_id}/ai-executions",
        headers={
            "If-Match": str(fixture.account_revision),
            "Idempotency-Key": f"idem_p0h_execution_{key}",
        },
        json=execution_payload(
            fixture,
            max_cost_micros=max_cost_micros,
        ),
    )
    assert response.status_code == 202, response.text
    return dict(response.json()["data"])


def _preflight_payload(
    fixture: P0HExecutionFixture,
    *,
    max_cost_micros: int | None = None,
) -> dict[str, object]:
    policy: dict[str, object] = {"allowFallback": True}
    if max_cost_micros is not None:
        policy["maxCostMicros"] = max_cost_micros
    return {
        "capabilityKey": "script_generation",
        "knowledgeSnapshotId": fixture.knowledge_snapshot_id,
        "recipeVersionId": fixture.recipe_version_id,
        "inputSummary": {"estimatedInputUnits": 16},
        "executionPolicy": policy,
    }


def _posts(scenario: ControlledProviderScenario) -> list[dict[str, object]]:
    return [item for item in scenario.received if item["method"] == "POST"]
