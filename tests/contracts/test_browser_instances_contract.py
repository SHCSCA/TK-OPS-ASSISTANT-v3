from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from services.browser_runtime import BrowserLaunchResult, BrowserRuntime, BrowserRuntimeHealth


class ContractBrowserRuntime(BrowserRuntime):
    def __init__(self) -> None:
        self.alive = False

    def launch(self, *, profile_path: Path) -> BrowserLaunchResult:
        self.alive = True
        return BrowserLaunchResult(
            process_id=24680,
            debug_host='127.0.0.1',
            debug_port=59444,
            executable_path='G:/fake-browser/contract-browser.exe',
            devtools_url='http://127.0.0.1:59444/json/version',
            metadata={'profilePath': str(profile_path), 'kind': 'contract-process'},
        )

    def health(self, *, process_id: int | None, debug_port: int | None) -> BrowserRuntimeHealth:
        return BrowserRuntimeHealth(
            alive=self.alive and process_id == 24680 and debug_port == 59444,
            process_id=process_id,
            debug_port=debug_port,
            error_code=None if self.alive else 'browser_instance.process_missing',
            error_message=None if self.alive else '浏览器进程不存在或已经退出。',
        )

    def stop(self, *, process_id: int | None) -> BrowserRuntimeHealth:
        self.alive = False
        return BrowserRuntimeHealth(alive=False, process_id=process_id, debug_port=None)

    def launch_supported(self) -> bool:
        return True


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
    runtime_client.app.state.device_workspace_service._browser_runtime = ContractBrowserRuntime()
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
        'processId',
        'debugPort',
        'debugHost',
        'runtimeMode',
        'launchSupported',
        'runtimeEvidence',
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
        'operation',
        'processBoundaryVerified',
        'processSummary',
    }
    assert start_payload['saved'] is True
    assert start_payload['browserInstance']['status'] == 'running'
    assert start_payload['operation'] == 'start'
    assert start_payload['processBoundaryVerified'] is True
    assert start_payload['processSummary']['pid'] == 24680
    assert start_payload['processSummary']['alive'] is True
    assert start_payload['browserInstance']['processId'] == 24680
    assert start_payload['browserInstance']['debugPort'] == 59444
    assert start_payload['browserInstance']['runtimeMode'] == 'local_process'

    health_response = runtime_client.post(
        f'/api/devices/workspaces/{workspace_id}/browser-instances/{browser_instance_id}/health-check',
    )
    assert health_response.status_code == 200
    health_payload = health_response.json()['data']
    assert health_payload['browserInstance']['status'] == 'ready'
    assert health_payload['browserInstance']['lastCheckedAt']
    assert health_payload['processBoundaryVerified'] is True

    stop_response = runtime_client.post(
        f'/api/devices/workspaces/{workspace_id}/browser-instances/{browser_instance_id}/stop',
    )
    assert stop_response.status_code == 200
    stop_payload = stop_response.json()['data']
    assert stop_payload['browserInstance']['status'] == 'stopped'
    assert stop_payload['operation'] == 'stop'
    assert stop_payload['processBoundaryVerified'] is True
    assert stop_payload['processSummary']['alive'] is False
    assert stop_payload['browserInstance']['processId'] is None
    assert stop_payload['browserInstance']['debugPort'] is None


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
