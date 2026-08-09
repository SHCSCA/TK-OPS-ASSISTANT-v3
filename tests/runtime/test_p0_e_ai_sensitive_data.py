from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from domain.models.ai_configuration_v1 import ProviderProfile
from domain.models.mutation_idempotency import RuntimeMutationIdempotency
from domain.models.runtime_event import RuntimeEvent
from domain.models.runtime_task import RuntimeTask
from tests.runtime.p0e_ai_integration_support import (
    create_prompt,
    create_provider,
    session,
)


def test_provider_plaintext_credential_is_absent_from_database_and_response(
    licensed_runtime_client: TestClient,
) -> None:
    provider = create_provider(licensed_runtime_client, key="secret-scan")
    provider_id = str(provider["id"])
    secret = "p0e-credential-DO-NOT-LEAK-7b93"

    response = licensed_runtime_client.put(
        f"/api/v1/system/providers/{provider_id}/credential",
        headers={"If-Match": str(provider["revision"])},
        json={"credential": secret},
    )

    assert response.status_code == 200, response.text
    assert secret not in response.text
    provider_response = licensed_runtime_client.get(
        f"/api/v1/system/providers/{provider_id}",
    )
    assert provider_response.status_code == 200, provider_response.text
    provider_data = provider_response.json()["data"]
    assert "credential" not in provider_data
    assert provider_data["credentialSummary"] == {
        "configured": True,
        "maskedValue": None,
    }
    with session(licensed_runtime_client) as database:
        row = database.get(ProviderProfile, provider_id)
        assert row is not None
        assert row.credential_ref is not None
        assert row.credential_ref.startswith("secret://providers/")
        assert secret not in row.credential_ref
        audit_text = _audit_text(database)
    assert secret not in audit_text


def test_prompt_body_is_absent_from_idempotency_and_event_audit(
    licensed_runtime_client: TestClient,
    runtime_data_dir: Path,
) -> None:
    system_prompt = "P0E_SYSTEM_PROMPT_PRIVATE_MARKER_34F1"
    task_template = "P0E_TASK_TEMPLATE_PRIVATE_MARKER_92D8"

    create_prompt(
        licensed_runtime_client,
        profile_key="prompt-sensitive-scan",
        capability_key="script_generation",
        system_prompt=system_prompt,
        task_template=task_template,
    )

    with session(licensed_runtime_client) as database:
        audit_text = _audit_text(database)
    assert system_prompt not in audit_text
    assert task_template not in audit_text
    log_text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in runtime_data_dir.rglob("*.log")
    )
    assert system_prompt not in log_text
    assert task_template not in log_text


def test_provider_task_snapshot_contains_only_refs_and_revisions(
    licensed_runtime_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = create_provider(licensed_runtime_client, key="task-scan")
    provider_id = str(provider["id"])
    secret = "p0e-task-secret-DO-NOT-LEAK-d712"
    credential = licensed_runtime_client.put(
        f"/api/v1/system/providers/{provider_id}/credential",
        headers={"If-Match": str(provider["revision"])},
        json={"credential": secret},
    )
    assert credential.status_code == 200, credential.text
    monkeypatch.setattr(
        licensed_runtime_client.app.state.task_coordinator,
        "_schedule_if_queued",
        lambda _record: None,
    )

    response = licensed_runtime_client.post(
        f"/api/v1/system/providers/{provider_id}/checks",
        headers={"Idempotency-Key": "idem-provider-check-sensitive"},
        json={"force": True},
    )

    assert response.status_code == 202, response.text
    assert secret not in response.text
    task_id = str(response.json()["data"]["taskId"])
    with session(licensed_runtime_client) as database:
        task = database.get(RuntimeTask, task_id)
        assert task is not None
        snapshot = json.loads(task.config_snapshot_json)
        payload = snapshot["payload"]
        assert payload["providerId"] == provider_id
        assert payload["providerRevision"] == 2
        assert "credential" not in payload
        assert "credentialRef" not in payload
        assert secret not in task.config_snapshot_json


def test_runtime_log_files_do_not_receive_sensitive_markers(
    licensed_runtime_client: TestClient,
    runtime_data_dir: Path,
) -> None:
    secret = "p0e-log-secret-DO-NOT-LEAK-42a6"
    provider = create_provider(licensed_runtime_client, key="log-scan")
    response = licensed_runtime_client.put(
        f"/api/v1/system/providers/{provider['id']}/credential",
        headers={"If-Match": str(provider["revision"])},
        json={"credential": secret},
    )
    assert response.status_code == 200, response.text

    log_text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in runtime_data_dir.rglob("*.log")
    )
    assert secret not in log_text


def _audit_text(database: Session) -> str:
    mutations = database.scalars(
        select(RuntimeMutationIdempotency)
    ).all()
    events = database.scalars(select(RuntimeEvent)).all()
    tasks = database.scalars(select(RuntimeTask)).all()
    return "\n".join(
        [
            *(
                f"{row.operation_name}\n{row.response_json}\n"
                f"{row.request_hash}\n{row.idempotency_key_hash}"
                for row in mutations
            ),
            *(row.payload_json for row in events),
            *(row.config_snapshot_json for row in tasks),
        ]
    )
