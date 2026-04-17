from __future__ import annotations

from fastapi.testclient import TestClient


def test_dashboard_summary_contract_uses_dashboard_prefix_and_expected_shape(
    runtime_client: TestClient,
) -> None:
    response = runtime_client.get('/api/dashboard/summary')

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {'ok', 'data'}
    assert payload['ok'] is True
    assert {
        'greeting',
        'heroContext',
        'recentProjects',
        'todos',
        'exceptions',
        'health',
        'generatedAt',
    }.issubset(payload['data'])
    assert payload['data']['recentProjects'] == []
    assert payload['data']['heroContext']['currentProject'] is None
    assert payload['data']['todos'] == []
    assert payload['data']['exceptions'] == []


def test_dashboard_project_and_context_contracts_return_expected_shapes(
    runtime_client: TestClient,
) -> None:
    create_response = runtime_client.post(
        '/api/dashboard/projects',
        json={'name': 'Contract Project', 'description': 'Contract coverage'},
    )

    assert create_response.status_code == 200
    create_payload = create_response.json()
    assert set(create_payload) == {'ok', 'data'}
    assert create_payload['ok'] is True
    assert set(create_payload['data']) == {
        'id',
        'name',
        'description',
        'status',
        'currentScriptVersion',
        'currentStoryboardVersion',
        'createdAt',
        'updatedAt',
        'lastAccessedAt',
    }

    project_id = create_payload['data']['id']

    context_response = runtime_client.put(
        '/api/dashboard/context',
        json={'projectId': project_id},
    )

    assert context_response.status_code == 200
    context_payload = context_response.json()
    assert set(context_payload) == {'ok', 'data'}
    assert context_payload['ok'] is True
    assert set(context_payload['data']) == {'projectId', 'projectName', 'status'}
    assert context_payload['data']['projectId'] == project_id

    clear_context_response = runtime_client.put(
        '/api/dashboard/context',
        json={'projectId': None},
    )

    assert clear_context_response.status_code == 200
    clear_context_payload = clear_context_response.json()
    assert set(clear_context_payload) == {'ok', 'data'}
    assert clear_context_payload['ok'] is True
    assert clear_context_payload['data'] is None

    read_context_response = runtime_client.get('/api/dashboard/context')

    assert read_context_response.status_code == 200
    read_context_payload = read_context_response.json()
    assert set(read_context_payload) == {'ok', 'data'}
    assert read_context_payload['ok'] is True
    assert read_context_payload['data'] is None
