from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient


def test_video_deconstruction_stages_and_rerun_contract(runtime_app, tmp_path: Path) -> None:
    client = TestClient(runtime_app)
    project_id = client.post(
        '/api/dashboard/projects',
        json={'name': 'Video Contract', 'description': 'Stage contract'},
    ).json()['data']['id']
    video_path = tmp_path / 'contract-video.mp4'
    video_path.write_bytes(b'\x00' * 4096)

    with patch('tasks.video_tasks.probe_video', return_value=None):
        import_response = client.post(
            f'/api/video-deconstruction/projects/{project_id}/import',
            json={'filePath': str(video_path)},
        )

    video_id = import_response.json()['data']['id']

    stages_response = client.get(f'/api/video-deconstruction/videos/{video_id}/stages')
    assert stages_response.status_code == 200
    stages_payload = stages_response.json()
    assert set(stages_payload) == {'ok', 'data'}
    assert isinstance(stages_payload['data'], list)
    assert set(stages_payload['data'][0]) == {
        'stageId',
        'label',
        'status',
        'progressPct',
        'resultSummary',
        'errorMessage',
        'updatedAt',
        'canRerun',
    }

    rerun_response = client.post(
        f'/api/video-deconstruction/videos/{video_id}/stages/transcribe/rerun'
    )
    assert rerun_response.status_code == 200
    rerun_payload = rerun_response.json()
    assert set(rerun_payload) == {'ok', 'data'}
    assert set(rerun_payload['data']) == {
        'id',
        'taskType',
        'projectId',
        'status',
        'progress',
        'message',
        'createdAt',
        'updatedAt',
    }
