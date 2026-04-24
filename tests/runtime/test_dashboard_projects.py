from __future__ import annotations

from fastapi.testclient import TestClient


def test_dashboard_summary_starts_without_projects(runtime_client: TestClient) -> None:
    response = runtime_client.get('/api/dashboard/summary')

    assert response.status_code == 200
    payload = response.json()
    assert payload['ok'] is True
    assert payload['data']['recentProjects'] == []
    assert payload['data']['currentProject'] is None
    assert payload['data']['recentTasks'] == []
    assert payload['data']['riskSummary'] == {'total': 0, 'blocking': 0, 'items': []}
    assert payload['data']['pendingItems'][0]['id'] == 'create-first-project'
    assert payload['data']['currentAction']['action'] == 'create-project'
    assert payload['data']['generatedAt']


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
    assert summary['pendingItems'][0]['id'] == 'script-bootstrap'
    assert summary['currentAction']['action'] == 'open-scripts'
    assert summary['currentAction']['targetProjectId'] == created['id']


def test_dashboard_project_delete_soft_deletes_project_and_clears_context(runtime_app) -> None:
    client = TestClient(runtime_app)
    create_response = client.post(
        '/api/dashboard/projects',
        json={'name': 'Delete Flow', 'description': 'soft delete'},
    )
    assert create_response.status_code == 200
    project_id = create_response.json()['data']['id']

    delete_response = client.delete(f'/api/dashboard/projects/{project_id}')

    assert delete_response.status_code == 200
    payload = delete_response.json()['data']
    assert payload['deleted'] is True
    assert payload['projectId'] == project_id
    assert payload['clearedCurrentProject'] is True
    assert payload['deletedAt']

    summary_response = client.get('/api/dashboard/summary')
    assert summary_response.status_code == 200
    summary = summary_response.json()['data']
    assert summary['recentProjects'] == []
    assert summary['currentProject'] is None

    context_response = client.get('/api/dashboard/context')
    assert context_response.status_code == 200
    assert context_response.json()['data'] is None


def test_dashboard_project_delete_blocks_when_active_task_exists(runtime_app, monkeypatch) -> None:
    client = TestClient(runtime_app)
    create_response = client.post(
        '/api/dashboard/projects',
        json={'name': 'Blocked Delete', 'description': 'active task guard'},
    )
    assert create_response.status_code == 200
    project_id = create_response.json()['data']['id']
    task_id = 'task-delete-guard'
    monkeypatch.setattr(
        runtime_app.state.task_manager,
        'list_active',
        lambda: [
            type(
                'TaskInfo',
                (),
                {'id': task_id, 'project_id': project_id, 'status': 'queued'},
            )()
        ],
    )

    delete_response = client.delete(f'/api/dashboard/projects/{project_id}')

    assert delete_response.status_code == 409
    payload = delete_response.json()
    assert payload['ok'] is False
    assert payload['error_code'] == 'project.delete_blocked'
    assert payload['details'] == {
        'next_action': '请先等待任务完成，或取消相关长任务后再删除项目。',
        'task_id': task_id,
        'status': 'queued',
    }


def test_dashboard_summary_uses_active_task_as_current_action_and_risk_source(runtime_app, monkeypatch) -> None:
    client = TestClient(runtime_app)
    create_response = client.post(
        '/api/dashboard/projects',
        json={'name': 'Task Summary', 'description': 'summary with active task'},
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
                    'id': 'task-summary-1',
                    'task_type': 'video_import',
                    'project_id': project_id,
                    'status': 'blocked',
                    'progress': 55,
                    'message': '等待素材修复',
                    'created_at': '2026-04-21T11:00:00Z',
                    'updated_at': '2026-04-21T11:05:00Z',
                },
            )()
        ],
    )

    summary_response = client.get('/api/dashboard/summary')

    assert summary_response.status_code == 200
    summary = summary_response.json()['data']
    assert len(summary['recentTasks']) == 1
    assert summary['recentTasks'][0]['taskId'] == 'task-summary-1'
    assert summary['pendingItems'][0]['id'] == 'task-task-summary-1'
    assert summary['currentAction'] == {
        'label': '继续当前任务',
        'action': 'open-task',
        'targetProjectId': project_id,
        'targetTaskId': 'task-summary-1',
    }
    assert summary['riskSummary']['total'] == 2
    assert summary['riskSummary']['blocking'] == 1
    assert summary['riskSummary']['items'][0]['id'] == 'blocked-task-summary-1'
    assert summary['riskSummary']['items'][1]['id'] == 'delete-guard-task-summary-1'
