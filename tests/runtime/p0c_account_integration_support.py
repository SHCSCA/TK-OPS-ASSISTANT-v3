from __future__ import annotations

import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from domain.models.account import Account
from domain.models.device_workspace import (
    BrowserInstance,
    DeviceWorkspace,
    ExecutionBinding,
)
from domain.models.knowledge import KnowledgeSource


def create_account(
    client: TestClient,
    *,
    name: str,
    idempotency_key: str,
) -> tuple[str, int]:
    response = client.post(
        "/api/v1/accounts",
        headers={"Idempotency-Key": idempotency_key},
        json={
            "name": name,
            "username": None,
            "platform": "tiktok",
        },
    )
    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["ok"] is True
    return str(payload["data"]["id"]), int(payload["meta"]["revision"])


def mutation_headers(
    *,
    revision: int | None = None,
    idempotency_key: str | None = None,
    operation_id: str | None = None,
) -> dict[str, str]:
    headers: dict[str, str] = {}
    if revision is not None:
        headers["If-Match"] = str(revision)
    if idempotency_key is not None:
        headers["Idempotency-Key"] = idempotency_key
    if operation_id is not None:
        headers["X-Operation-ID"] = operation_id
    return headers


def account_revision(client: TestClient, account_id: str) -> int:
    with session(client) as database:
        account = database.get(Account, account_id)
        assert account is not None
        return int(account.revision)


def seed_workspace_and_browser(
    client: TestClient,
    *,
    account_id: str,
    key: str,
    root: Path,
) -> tuple[str, str]:
    workspace_id = f"workspace_{key}"
    browser_id = f"browser_{key}"
    now = datetime.now(UTC)
    with session(client) as database:
        database.add(
            DeviceWorkspace(
                id=workspace_id,
                account_id=account_id,
                name=f"{key} 工作区",
                root_path=str(root / key / "workspace"),
                root_ref=(
                    f"wr_{hashlib.sha256(key.encode('utf-8')).hexdigest()[:32]}"
                ),
                ownership_state="owned",
                revision=2,
                status="ready",
                error_count=0,
                last_used_at=now,
                created_at=now,
                updated_at=now,
            )
        )
        database.flush()
        database.add(
            BrowserInstance(
                id=browser_id,
                account_id=account_id,
                workspace_id=workspace_id,
                name=f"{key} 浏览器",
                profile_path=str(root / key / "browser-profile"),
                status="running",
                process_id=1000,
                debug_port=9222,
                debug_host="127.0.0.1",
                runtime_mode="test",
                executable_path=None,
                runtime_evidence_json=json.dumps(
                    {
                        "schemaVersion": 1,
                        "ownerMarkerVersion": 1,
                        "debugHost": "127.0.0.1",
                    }
                ),
                ownership_state="owned",
                revision=2,
                last_checked_at=now,
                last_started_at=None,
                last_stopped_at=None,
                error_code=None,
                error_message=None,
                created_at=now,
                updated_at=now,
            )
        )
        database.commit()
    return workspace_id, browser_id


def seed_eligible_execution_environment(
    client: TestClient,
    *,
    account_id: str,
    key: str,
    root: Path,
) -> tuple[str, int, str, str]:
    workspace_id, browser_id = seed_workspace_and_browser(
        client,
        account_id=account_id,
        key=key,
        root=root,
    )
    (root / key / "workspace").mkdir(parents=True, exist_ok=True)
    (root / key / "browser-profile").mkdir(parents=True, exist_ok=True)
    environment_id = f"binding_{key}"
    now = datetime.now(UTC)
    with session(client) as database:
        database.add(
            ExecutionBinding(
                id=environment_id,
                account_id=account_id,
                device_workspace_id=workspace_id,
                browser_instance_id=browser_id,
                status="inactive",
                source="runtime-supervisor",
                metadata_json='{"owner":"contract-test"}',
                revision=2,
                created_at=now,
                updated_at=now,
            )
        )
        database.commit()
    # 工作区、浏览器与绑定修订号均为 2，资格证据修订号为三者之和。
    return environment_id, 6, workspace_id, browser_id


def mark_source_ready(
    client: TestClient,
    *,
    account_id: str,
    source_id: str,
    content: str,
) -> str:
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    with session(client) as database:
        source = database.scalar(
            select(KnowledgeSource).where(
                KnowledgeSource.id == source_id,
                KnowledgeSource.account_id == account_id,
            )
        )
        assert source is not None
        source.status = "ready"
        source.content_hash = content_hash
        source.revision = int(source.revision) + 1
        database.commit()
    return content_hash


def session(client: TestClient) -> Session:
    return client.app.state.session_factory()


def error_code(response: Response) -> str:
    payload = response.json()
    assert payload["ok"] is False
    return str(payload["error_code"])


def wait_account_task(
    client: TestClient,
    *,
    account_id: str,
    task_id: str,
    timeout_seconds: float = 5.0,
) -> dict[str, object]:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        response = client.get(
            f"/api/v1/accounts/{account_id}/tasks/{task_id}"
        )
        assert response.status_code == 200, response.text
        task = response.json()["data"]
        if task["status"] in {"completed", "failed"}:
            return task
        time.sleep(0.02)
    raise AssertionError(f"账号任务未在时限内结束：{task_id}")
