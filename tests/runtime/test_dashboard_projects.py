from __future__ import annotations

from fastapi.testclient import TestClient


def test_dashboard_summary_starts_without_projects(runtime_client: TestClient) -> None:
    response = runtime_client.get('/api/dashboard/summary')

    assert response.status_code == 200
    payload = response.json()
    assert payload['ok'] is True
    assert payload['data']['recentProjects'] == []
    assert payload['data']['currentProject'] is None


def test_project_creation_and_context_persist_across_app_recreation(runtime_app) -> None:
    client = TestClient(runtime_app)

    create_response = client.post(
        '/api/dashboard/projects',
        json={
            'name': 'Launch Sprint',
            'description': 'Primary TikTok campaign'
        },
    )

    assert create_response.status_code == 200
    created = create_response.json()['data']
    assert created['name'] == 'Launch Sprint'
    assert created['description'] == 'Primary TikTok campaign'
    assert created['status'] == 'active'
    assert created['currentScriptVersion'] == 0
    assert created['currentStoryboardVersion'] == 0
    assert created['createdAt']
    assert created['updatedAt']
    assert created['lastAccessedAt']

    context_response = client.put(
        '/api/dashboard/context',
        json={'projectId': created['id']},
    )

    assert context_response.status_code == 200
    context_payload = context_response.json()
    assert context_payload['ok'] is True
    assert context_payload['data']['projectId'] == created['id']
    assert context_payload['data']['projectName'] == 'Launch Sprint'

    from app.factory import create_app

    reloaded_client = TestClient(create_app())
    summary_response = reloaded_client.get('/api/dashboard/summary')

    assert summary_response.status_code == 200
    summary = summary_response.json()['data']
    assert len(summary['recentProjects']) == 1
    assert summary['recentProjects'][0]['id'] == created['id']
    assert summary['currentProject']['projectId'] == created['id']
    assert summary['currentProject']['projectName'] == 'Launch Sprint'
