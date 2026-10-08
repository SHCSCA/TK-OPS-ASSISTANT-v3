from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select

from domain.models.ai_execution import AIExecution, AIExecutionJob
from domain.models.ai_execution_evidence import (
    AIErrorEvidence,
    AIExecutionOutput,
    AIUsageRecord,
)
from domain.models.runtime_event import RuntimeEvent
from errors import ErrorCode
from tests.runtime.p0c_account_integration_support import (
    create_account,
    session,
)
from tests.runtime.p0h_execution_support import (
    execution_payload,
    seed_execution_chain,
    wait_execution,
)
from tests.runtime.p0h_provider_test_server import (
    ControlledProviderScenario,
    ControlledProviderServer,
)


def test_execution_detail_output_evidence_cursor_and_events_are_account_scoped(
    licensed_runtime_client: TestClient,
) -> None:
    scenario = ControlledProviderScenario()
    with ControlledProviderServer(scenario) as provider:
        fixture = seed_execution_chain(
            licensed_runtime_client,
            base_urls=(provider.base_url,),
            credentials=(scenario.token,),
            key="isolation",
        )
        created = licensed_runtime_client.post(
            f"/api/v1/accounts/{fixture.account_id}/ai-executions",
            headers={
                "If-Match": str(fixture.account_revision),
                "Idempotency-Key": "idem_p0h_isolation_execution",
            },
            json=execution_payload(fixture),
        )
        assert created.status_code == 202, created.text
        accepted = dict(created.json()["data"])
        completed = wait_execution(
            licensed_runtime_client,
            account_id=fixture.account_id,
            execution_id=str(accepted["executionId"]),
        )
        output_id = str(completed["outputs"][0]["id"])
        retried = licensed_runtime_client.post(
            (
                f"/api/v1/accounts/{fixture.account_id}/ai-executions/"
                f"{accepted['executionId']}/retry"
            ),
            headers={"Idempotency-Key": "idem_p0h_isolation_retry_a"},
            json={"mode": "same_snapshot"},
        )
        assert retried.status_code == 202, retried.text
        wait_execution(
            licensed_runtime_client,
            account_id=fixture.account_id,
            execution_id=str(retried.json()["data"]["executionId"]),
        )
        account_b, _ = create_account(
            licensed_runtime_client,
            name="P0-H 隔离账号 B",
            idempotency_key="idem_p0h_isolation_account_b",
        )

        page_a = licensed_runtime_client.get(
            f"/api/v1/accounts/{fixture.account_id}/ai-executions",
            params={"limit": 1},
        )
        assert page_a.status_code == 200, page_a.text
        cursor = page_a.json()["meta"]["nextCursor"]
        assert isinstance(cursor, str)
        page_b = licensed_runtime_client.get(
            f"/api/v1/accounts/{account_b}/ai-executions"
        )
        assert page_b.status_code == 200
        assert page_b.json()["data"]["items"] == []
        cross_cursor = licensed_runtime_client.get(
            f"/api/v1/accounts/{account_b}/ai-executions",
            params={"limit": 1, "cursor": cursor},
        )
        assert cross_cursor.status_code == 422
        assert (
            cross_cursor.json()["error_code"]
            == ErrorCode.REQUEST_VALIDATION_FAILED
        )

        base = (
            f"/api/v1/accounts/{account_b}/ai-executions/"
            f"{accepted['executionId']}"
        )
        hidden_requests = (
            licensed_runtime_client.get(base),
            licensed_runtime_client.get(f"{base}/evidence"),
            licensed_runtime_client.get(f"{base}/outputs/{output_id}"),
            licensed_runtime_client.post(
                f"{base}/cancel",
                headers={"Idempotency-Key": "idem_p0h_cross_cancel"},
            ),
            licensed_runtime_client.post(
                f"{base}/retry",
                headers={"Idempotency-Key": "idem_p0h_cross_retry"},
                json={"mode": "same_snapshot"},
            ),
        )
        for response in hidden_requests:
            assert response.status_code == 404, response.text
            assert response.json()["error_code"] == ErrorCode.AI_EXECUTION_NOT_FOUND

        with session(licensed_runtime_client) as database:
            execution = database.get(AIExecution, accepted["executionId"])
            assert execution is not None
            assert execution.account_id == fixture.account_id
            for model in (
                AIExecutionJob,
                AIUsageRecord,
                AIExecutionOutput,
                AIErrorEvidence,
            ):
                rows = database.scalars(
                    select(model).where(
                        model.execution_id == accepted["executionId"]
                    )
                ).all()
                assert all(row.account_id == fixture.account_id for row in rows)
            events = database.scalars(
                select(RuntimeEvent).where(
                    RuntimeEvent.aggregate_id == accepted["executionId"]
                )
            ).all()
            assert events
            assert all(row.account_id == fixture.account_id for row in events)
            assert all(
                row.topic == f"account:{fixture.account_id}:ai-executions"
                for row in events
            )
