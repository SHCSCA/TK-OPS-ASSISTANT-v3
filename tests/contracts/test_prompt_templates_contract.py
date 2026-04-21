from __future__ import annotations

from fastapi.testclient import TestClient


def _assert_ok(payload: dict[str, object]) -> object:
    assert set(payload) == {"ok", "data"}
    assert payload["ok"] is True
    return payload["data"]


def test_prompt_templates_contract_covers_crud_and_list_filter(
    runtime_client: TestClient,
) -> None:
    create_response = runtime_client.post(
        '/api/prompt-templates',
        json={
            'kind': 'script',
            'name': '??????',
            'description': '?????????',
            'content': '????????????????',
        },
    )

    assert create_response.status_code == 200
    created = _assert_ok(create_response.json())
    assert set(created) == {'id', 'kind', 'name', 'description', 'content', 'createdAt', 'updatedAt'}
    assert created['kind'] == 'script'

    list_response = runtime_client.get('/api/prompt-templates', params={'kind': 'script'})
    assert list_response.status_code == 200
    listed = _assert_ok(list_response.json())
    assert len(listed) == 1
    assert listed[0]['id'] == created['id']

    update_response = runtime_client.put(
        f"/api/prompt-templates/{created['id']}",
        json={
            'kind': 'script',
            'name': '??????-??',
            'description': '?????????',
            'content': '????????????',
        },
    )
    assert update_response.status_code == 200
    updated = _assert_ok(update_response.json())
    assert updated['name'] == '??????-??'

    delete_response = runtime_client.delete(f"/api/prompt-templates/{created['id']}")
    assert delete_response.status_code == 200
    assert _assert_ok(delete_response.json()) == {'deleted': True}

    empty_response = runtime_client.get('/api/prompt-templates')
    assert empty_response.status_code == 200
    assert _assert_ok(empty_response.json()) == []


def test_prompt_templates_contract_rejects_empty_payload_fields(
    runtime_client: TestClient,
) -> None:
    response = runtime_client.post(
        '/api/prompt-templates',
        json={
            'kind': '',
            'name': '',
            'description': '',
            'content': '',
        },
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload['ok'] is False
    assert payload['error_code'] == 'request.validation_failed'
