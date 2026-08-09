from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

LEGACY_PROMPT_WRITES = (
    ("POST", "/api/prompt-templates"),
    ("PUT", "/api/prompt-templates/template-one"),
    ("DELETE", "/api/prompt-templates/template-one"),
)


def test_legacy_prompt_template_list_remains_read_only(
    runtime_client: TestClient,
) -> None:
    response = runtime_client.get("/api/prompt-templates")

    assert response.status_code == 200
    assert response.json() == {"ok": True, "data": []}


@pytest.mark.parametrize(
    ("method", "path"),
    LEGACY_PROMPT_WRITES,
    ids=lambda value: str(value),
)
def test_legacy_prompt_template_writes_require_versioned_v1_api(
    runtime_client: TestClient,
    method: str,
    path: str,
) -> None:
    response = runtime_client.request(
        method,
        path,
        content=b"{ definitely-not-json",
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 410
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error_code"] == "legacy.write.unsupported"


def test_legacy_prompt_rejection_does_not_create_template(
    runtime_client: TestClient,
) -> None:
    rejected = runtime_client.post(
        "/api/prompt-templates",
        json={
            "kind": "script",
            "name": "旧接口模板",
            "description": "不得写入",
            "content": "不得保存的正文",
        },
    )

    assert rejected.status_code == 410
    listed = runtime_client.get("/api/prompt-templates")
    assert listed.status_code == 200
    assert listed.json()["data"] == []
