from __future__ import annotations

from fastapi.testclient import TestClient


def _create_workspace(runtime_client: TestClient, root_path: str) -> str:
    response = runtime_client.post(
        '/api/devices/workspaces',
        json={
            'name': 'Main Workspace',
            'root_path': root_path,
        },
    )
    assert response.status_code == 201
    return response.json()['data']['id']


def test_browser_instance_contract_uses_nested_workspace_routes_and_write_receipts(
    runtime_client: TestClient,
    tmp_path,
) -> None:
    workspace_root = tmp_path / 'workspace-browser-contract'
    workspace_root.mkdir(parents=True, exist_ok=True)
    profile_path = workspace_root / 'profiles' / 'default'
    workspace_id = _create_workspace(runtime_client, str(workspace_root))

    create_response = runtime_client.post(
        f'/api/devices/workspaces/{workspace_id}/browser-instances',
        json={
            'name': 'Default Browser',
            'profilePath': str(profile_path),
        },
    )

    assert create_response.status_code == 201
    create_payload = create_response.json()
    assert set(create_payload) == {'ok', 'data'}
    assert create_payload['ok'] is True
    assert set(create_payload['data']) == {
        'id',
        'workspaceId',
        'name',
        'profilePath',
        'status',
        'lastCheckedAt',
        'lastStartedAt',
        'lastStoppedAt',
        'errorCode',
        'errorMessage',
        'createdAt',
        'updatedAt',
    }

    browser_instance_id = create_payload['data']['id']
    start_response = runtime_client.post(
        f'/api/devices/workspaces/{workspace_id}/browser-instances/{browser_instance_id}/start',
    )

    assert start_response.status_code == 200
    start_payload = start_response.json()['data']
    assert set(start_payload) == {
        'saved',
        'updatedAt',
        'versionOrRevision',
        'objectSummary',
        'browserInstance',
    }
    assert start_payload['saved'] is True
    assert start_payload['browserInstance']['status'] == 'running'

    health_response = runtime_client.post(
        f'/api/devices/workspaces/{workspace_id}/browser-instances/{browser_instance_id}/health-check',
    )
    assert health_response.status_code == 200
    health_payload = health_response.json()['data']
    assert health_payload['browserInstance']['status'] == 'ready'
    assert health_payload['browserInstance']['lastCheckedAt']

    stop_response = runtime_client.post(
        f'/api/devices/workspaces/{workspace_id}/browser-instances/{browser_instance_id}/stop',
    )
    assert stop_response.status_code == 200
    stop_payload = stop_response.json()['data']
    assert stop_payload['browserInstance']['status'] == 'stopped'


def test_browser_instance_alias_routes_keep_workspace_compatibility(
    runtime_client: TestClient,
    tmp_path,
) -> None:
    workspace_root = tmp_path / 'workspace-browser-alias'
    workspace_root.mkdir(parents=True, exist_ok=True)
    workspace_id = _create_workspace(runtime_client, str(workspace_root))

    response = runtime_client.get(f'/api/devices/browser-instances/{workspace_id}')

    assert response.status_code == 200
    payload = response.json()
    assert payload['ok'] is True
    assert payload['data']['id'] == workspace_id
    assert 'root_path' in payload['data']
