from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from domain.models.ai_execution_evidence import AIErrorEvidence
from domain.models.runtime_event import RuntimeEvent
from domain.models.runtime_task import RuntimeTask
from errors import DomainError, ErrorCode
from services.ai_execution_v1.redaction import assert_safe_evidence
from tests.runtime.p0c_account_integration_support import session
from tests.runtime.p0h_execution_support import (
    execution_payload,
    seed_execution_chain,
    wait_execution,
)
from tests.runtime.p0h_provider_test_server import (
    ControlledProviderScenario,
    ControlledProviderServer,
)


@pytest.mark.parametrize(
    "payload",
    [
        {"credentialRef": "secret_ref"},
        {"safeSummary": "Bearer token-value"},
        {"safeSummary": r"C:\Users\private\source.txt"},
        {"safeSummary": "/home/private/source.txt"},
        {"safeSummary": "owner@example.com"},
        {"safeSummary": "@private_handle"},
        {"safeSummary": "sk-privatecredential0123456789"},
    ],
)
def test_evidence_guard_rejects_sensitive_fields_and_values(
    payload: dict[str, object],
) -> None:
    with pytest.raises(DomainError) as raised:
        assert_safe_evidence(payload)
    assert raised.value.error_code == ErrorCode.AI_EVIDENCE_REDACTION_FAILED


def test_task_event_api_evidence_and_logs_do_not_leak_execution_material(
    licensed_runtime_client: TestClient,
    runtime_data_dir: Path,
) -> None:
    marker = "raw-provider-body-private-marker"
    scenario = ControlledProviderScenario(
        error_status=400,
        error_marker=marker,
    )
    with ControlledProviderServer(scenario) as provider:
        fixture = seed_execution_chain(
            licensed_runtime_client,
            base_urls=(provider.base_url,),
            credentials=(scenario.token,),
            key="redaction",
        )
        payload = execution_payload(fixture)
        private_input = str(payload["input"])
        created = licensed_runtime_client.post(
            f"/api/v1/accounts/{fixture.account_id}/ai-executions",
            headers={
                "If-Match": str(fixture.account_revision),
                "Idempotency-Key": "idem_p0h_redaction_execution",
            },
            json=payload,
        )
        assert created.status_code == 202, created.text
        accepted = dict(created.json()["data"])
        failed = wait_execution(
            licensed_runtime_client,
            account_id=fixture.account_id,
            execution_id=str(accepted["executionId"]),
        )
        assert failed["status"] == "failed"
        evidence_response = licensed_runtime_client.get(
            (
                f"/api/v1/accounts/{fixture.account_id}/ai-executions/"
                f"{accepted['executionId']}/evidence"
            )
        )
        assert evidence_response.status_code == 200, evidence_response.text
        public_text = failed.__repr__() + evidence_response.text

        forbidden = (
            scenario.token,
            marker,
            provider.base_url,
            "你是短视频策划助手，只输出 JSON。",
            "如何建立稳定的短视频选题流程",
            private_input,
            str(runtime_data_dir),
        )
        assert all(value not in public_text for value in forbidden)

        with session(licensed_runtime_client) as database:
            task = database.get(RuntimeTask, accepted["taskId"])
            assert task is not None
            assert set(json.loads(task.config_snapshot_json)["payload"]) == {
                "executionId",
                "snapshotHash",
            }
            events = database.scalars(
                select(RuntimeEvent).where(
                    RuntimeEvent.aggregate_id == accepted["executionId"]
                )
            ).all()
            errors = database.scalars(
                select(AIErrorEvidence).where(
                    AIErrorEvidence.execution_id == accepted["executionId"]
                )
            ).all()
            stored_evidence = "\n".join(
                [task.config_snapshot_json]
                + [row.payload_json for row in events]
                + [
                    "|".join(
                        (
                            row.error_code,
                            row.safe_summary,
                            row.log_id,
                            row.response_body_hash or "",
                        )
                    )
                    for row in errors
                ]
            )
        assert all(value not in stored_evidence for value in forbidden)

    log_text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in runtime_data_dir.rglob("*.log")
    )
    assert all(value not in log_text for value in forbidden)
