from __future__ import annotations

from fastapi.testclient import TestClient


def _assert_ok(payload: dict[str, object]) -> object:
    assert set(payload) == {"ok", "data"}
    assert payload["ok"] is True
    return payload["data"]


def test_legacy_prompt_template_writes_are_retired_and_list_stays_read_only(
    runtime_client: TestClient,
) -> None:
    before = runtime_client.get('/api/prompt-templates', params={'kind': 'script'})
    assert before.status_code == 200
    assert _assert_ok(before.json()) == []

    responses = (
        runtime_client.post(
            '/api/prompt-templates',
            json={
                'kind': 'script',
                'name': '旧脚本模板',
                'description': '旧接口不得继续写入',
                'content': '不会被保存的提示词',
            },
        ),
        runtime_client.put(
            '/api/prompt-templates/template-one',
            json={
                'kind': 'script',
                'name': '旧脚本模板新版',
                'description': '旧接口不得继续写入',
                'content': '不会被保存的提示词',
            },
        ),
        runtime_client.delete('/api/prompt-templates/template-one'),
    )

    for response in responses:
        assert response.status_code == 410
        payload = response.json()
        assert payload['ok'] is False
        assert payload['error_code'] == 'legacy.write.unsupported'

    after = runtime_client.get('/api/prompt-templates')
    assert after.status_code == 200
    assert _assert_ok(after.json()) == []


def test_prompt_templates_contract_rejects_legacy_write_before_body_validation(
    runtime_client: TestClient,
) -> None:
    response = runtime_client.post(
        '/api/prompt-templates',
        content=b'{ definitely-not-json',
        headers={'Content-Type': 'application/json'},
    )

    assert response.status_code == 410
    payload = response.json()
    assert payload['ok'] is False
    assert payload['error_code'] == 'legacy.write.unsupported'
