from __future__ import annotations

from fastapi.testclient import TestClient

from domain.models.ai_execution import AIExecution, AIExecutionJob
from domain.models.runtime_task import RuntimeTask
from errors import ErrorCode
from tests.runtime.p0c_account_integration_support import session
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


def test_post_send_disconnect_becomes_result_unknown_without_retry(
    licensed_runtime_client: TestClient,
) -> None:
    scenario = ControlledProviderScenario(disconnect_after_request=True)
    with ControlledProviderServer(scenario) as provider:
        fixture = seed_execution_chain(
            licensed_runtime_client,
            base_urls=(provider.base_url,),
            credentials=(scenario.token,),
            key="result-unknown",
            route_max_retries=1,
        )
        created = _create(
            licensed_runtime_client,
            fixture,
            key="result-unknown",
        )
        failed = wait_execution(
            licensed_runtime_client,
            account_id=fixture.account_id,
            execution_id=str(created["executionId"]),
        )
        assert failed["status"] == "failed"
        assert failed["failureKind"] == "result_unknown"
        assert failed["errorCode"] == ErrorCode.AI_PROVIDER_RESULT_UNKNOWN
        assert failed["costStatus"] == "unavailable"
        assert len(failed["jobs"]) == 1
        assert len(_posts(scenario)) == 1


def test_running_cancel_reaches_runtime_task_and_marks_billing_unknown(
    licensed_runtime_client: TestClient,
) -> None:
    scenario = ControlledProviderScenario(response_delay_seconds=1.0)
    with ControlledProviderServer(scenario) as provider:
        fixture = seed_execution_chain(
            licensed_runtime_client,
            base_urls=(provider.base_url,),
            credentials=(scenario.token,),
            key="cancel",
            route_timeout_ms=4_000,
        )
        created = _create(
            licensed_runtime_client,
            fixture,
            key="cancel",
        )
        assert scenario.request_started.wait(timeout=3)
        cancelled = licensed_runtime_client.post(
            (
                f"/api/v1/accounts/{fixture.account_id}/ai-executions/"
                f"{created['executionId']}/cancel"
            ),
            headers={"Idempotency-Key": "idem_p0h_cancel_running"},
        )
        assert cancelled.status_code == 200, cancelled.text
        terminal = wait_execution(
            licensed_runtime_client,
            account_id=fixture.account_id,
            execution_id=str(created["executionId"]),
        )
        assert terminal["status"] == "completed"
        assert terminal["completionKind"] == "cancelled"
        assert terminal["costStatus"] == "unavailable"
        assert terminal["outputCount"] == 0
        task = licensed_runtime_client.get(
            f"/api/v1/accounts/{fixture.account_id}/tasks/{created['taskId']}"
        )
        assert task.status_code == 200
        assert task.json()["data"]["completionKind"] == "cancelled"
        assert len(_posts(scenario)) == 1


def test_restart_recovery_distinguishes_sent_and_unsent_work(
    licensed_runtime_client: TestClient,
) -> None:
    scenario = ControlledProviderScenario()
    with ControlledProviderServer(scenario) as provider:
        fixture = seed_execution_chain(
            licensed_runtime_client,
            base_urls=(provider.base_url,),
            credentials=(scenario.token,),
            key="restart",
        )
        created = _create(
            licensed_runtime_client,
            fixture,
            key="restart",
        )
        completed = wait_execution(
            licensed_runtime_client,
            account_id=fixture.account_id,
            execution_id=str(created["executionId"]),
        )
        job_id = str(completed["jobs"][0]["id"])

        _set_interrupted_state(
            licensed_runtime_client,
            execution_id=str(created["executionId"]),
            task_id=str(created["taskId"]),
            job_id=job_id,
            request_sent=True,
        )
        recovery = (
            licensed_runtime_client.app.state.runtime_container.services
            .ai_execution.recovery
        )
        report = recovery.reconcile()
        assert report.result_unknown_count == 1
        unknown = licensed_runtime_client.get(
            (
                f"/api/v1/accounts/{fixture.account_id}/ai-executions/"
                f"{created['executionId']}"
            )
        ).json()["data"]
        assert unknown["failureKind"] == "result_unknown"
        assert unknown["costStatus"] == "unavailable"
        task = licensed_runtime_client.get(
            f"/api/v1/accounts/{fixture.account_id}/tasks/{created['taskId']}"
        ).json()["data"]
        assert task["status"] == "failed"
        assert task["failureKind"] == "restart_interrupted"

        _set_interrupted_state(
            licensed_runtime_client,
            execution_id=str(created["executionId"]),
            task_id=str(created["taskId"]),
            job_id=job_id,
            request_sent=False,
        )
        report = recovery.reconcile()
        assert report.interrupted_count == 1
        interrupted = licensed_runtime_client.get(
            (
                f"/api/v1/accounts/{fixture.account_id}/ai-executions/"
                f"{created['executionId']}"
            )
        ).json()["data"]
        assert interrupted["failureKind"] == "restart_interrupted"
        assert len(_posts(scenario)) == 1


def _create(
    client: TestClient,
    fixture: P0HExecutionFixture,
    *,
    key: str,
) -> dict[str, object]:
    response = client.post(
        f"/api/v1/accounts/{fixture.account_id}/ai-executions",
        headers={
            "If-Match": str(fixture.account_revision),
            "Idempotency-Key": f"idem_p0h_recovery_{key}",
        },
        json=execution_payload(fixture),
    )
    assert response.status_code == 202, response.text
    return dict(response.json()["data"])


def _set_interrupted_state(
    client: TestClient,
    *,
    execution_id: str,
    task_id: str,
    job_id: str,
    request_sent: bool,
) -> None:
    now = "2026-08-10T00:00:00Z"
    with session(client) as database:
        execution = database.get(AIExecution, execution_id)
        task = database.get(RuntimeTask, task_id)
        job = database.get(AIExecutionJob, job_id)
        assert execution is not None and task is not None and job is not None
        execution.status = "running" if request_sent else "queued"
        execution.completion_kind = None
        execution.failure_kind = None
        execution.active_job_id = job_id if request_sent else None
        execution.error_code = None
        execution.error_log_id = None
        execution.completed_at = None
        execution.updated_at = now
        task.status = "running" if request_sent else "queued"
        task.completion_kind = None
        task.failure_kind = None
        task.error_code = None
        task.error_log_id = None
        task.completed_at = None
        task.updated_at = now
        job.status = "running" if request_sent else "failed"
        job.completion_kind = None
        job.failure_kind = None if request_sent else "error"
        job.completed_at = None if request_sent else now
        database.commit()


def _posts(scenario: ControlledProviderScenario) -> list[dict[str, object]]:
    return [item for item in scenario.received if item["method"] == "POST"]
