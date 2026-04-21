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
    assert set(payload['data']) == {
        'recentProjects',
        'currentProject',
        'recentTasks',
        'pendingItems',
        'riskSummary',
        'currentAction',
        'generatedAt',
    }
    assert payload['data']['recentProjects'] == []
    assert payload['data']['currentProject'] is None
    assert payload['data']['recentTasks'] == []
    assert len(payload['data']['pendingItems']) == 1
    assert set(payload['data']['pendingItems'][0]) == {
        'id',
        'kind',
        'title',
        'detail',
        'action',
        'targetProjectId',
        'targetTaskId',
    }
    assert payload['data']['riskSummary'] == {'total': 0, 'blocking': 0, 'items': []}
    assert set(payload['data']['currentAction']) == {
        'label',
        'action',
        'targetProjectId',
        'targetTaskId',
    }
    assert payload['data']['generatedAt']


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

    read_context_response = runtime_client.get('/api/dashboard/context')

    assert read_context_response.status_code == 200
    read_context_payload = read_context_response.json()
    assert set(read_context_payload) == {'ok', 'data'}
    assert read_context_payload['ok'] is True
    assert set(read_context_payload['data']) == {'projectId', 'projectName', 'status'}
    assert read_context_payload['data']['projectId'] == project_id


def test_dashboard_project_delete_contract_returns_deleted_summary_and_clears_context(
    runtime_client: TestClient,
) -> None:
    create_response = runtime_client.post(
        '/api/dashboard/projects',
        json={'name': 'Delete Me', 'description': 'dashboard delete contract'},
    )
    assert create_response.status_code == 200
    project_id = create_response.json()['data']['id']

    delete_response = runtime_client.delete(f'/api/dashboard/projects/{project_id}')

    assert delete_response.status_code == 200
    delete_payload = delete_response.json()
    assert set(delete_payload) == {'ok', 'data'}
    assert delete_payload['ok'] is True
    assert set(delete_payload['data']) == {'deleted', 'projectId', 'clearedCurrentProject', 'deletedAt'}
    assert delete_payload['data']['deleted'] is True
    assert delete_payload['data']['projectId'] == project_id
    assert delete_payload['data']['clearedCurrentProject'] is True
    assert delete_payload['data']['deletedAt']

    summary_response = runtime_client.get('/api/dashboard/summary')
    assert summary_response.status_code == 200
    summary_payload = summary_response.json()
    assert summary_payload['data']['recentProjects'] == []
    assert summary_payload['data']['currentProject'] is None


def test_dashboard_summary_contract_exposes_recent_tasks_pending_items_and_risk_summary(
    runtime_app,
    monkeypatch,
) -> None:
    client = TestClient(runtime_app)
    create_response = client.post(
        '/api/dashboard/projects',
        json={'name': 'Summary Project', 'description': 'summary contract'},
    )
    assert create_response.status_code == 200
    project_id = create_response.json()['data']['id']

    monkeypatch.setattr(
        runtime_app.state.task_manager,
        'list_active',
        lambda: [
            type(
                'TaskInfo',
                (),
                {
                    'id': 'task-1',
                    'task_type': 'video_import',
                    'project_id': project_id,
                    'status': 'blocked',
                    'progress': 42,
                    'message': '等待素材修复',
                    'created_at': '2026-04-21T11:00:00Z',
                    'updated_at': '2026-04-21T11:05:00Z',
                },
            )()
        ],
    )

    response = client.get('/api/dashboard/summary')

    assert response.status_code == 200
    payload = response.json()['data']
    assert len(payload['recentTasks']) == 1
    assert set(payload['recentTasks'][0]) == {
        'taskId',
        'taskType',
        'projectId',
        'status',
        'progress',
        'message',
        'createdAt',
        'updatedAt',
    }
    assert payload['recentTasks'][0]['taskId'] == 'task-1'
    assert len(payload['pendingItems']) >= 1
    assert payload['riskSummary']['total'] >= 1
    assert payload['riskSummary']['blocking'] >= 1
    assert len(payload['riskSummary']['items']) >= 1
    assert payload['currentAction']['action'] == 'open-task'
    assert payload['currentAction']['targetTaskId'] == 'task-1'
