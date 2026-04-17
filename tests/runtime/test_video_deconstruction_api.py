from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient


def test_video_deconstruction_stages_and_rerun(runtime_app, tmp_path: Path) -> None:
    client = TestClient(runtime_app)
    project_id = client.post(
        '/api/dashboard/projects',
        json={'name': 'Video Stage Project', 'description': 'Stage tests'},
    ).json()['data']['id']
    video_path = tmp_path / 'stage-test.mp4'
    video_path.write_bytes(b'\x00' * 4096)

    with patch('tasks.video_tasks.probe_video', return_value=None):
        import_response = client.post(
            f'/api/video-deconstruction/projects/{project_id}/import',
            json={'filePath': str(video_path)},
        )

    assert import_response.status_code == 200
    video_id = import_response.json()['data']['id']

    stages_response = client.get(f'/api/video-deconstruction/videos/{video_id}/stages')
    assert stages_response.status_code == 200
    stages = stages_response.json()['data']
    assert [item['stageId'] for item in stages] == [
        'import',
        'transcribe',
        'segment',
        'extract_structure',
    ]
    assert stages[0]['status'] in {'succeeded', 'ready', 'imported'}

    rerun_response = client.post(
        f'/api/video-deconstruction/videos/{video_id}/stages/transcribe/rerun'
    )
    assert rerun_response.status_code == 200
    task_payload = rerun_response.json()['data']
    assert task_payload['taskType'] == 'video-import-stage'
    assert task_payload['projectId'] == project_id

    rerun_stages_response = client.get(f'/api/video-deconstruction/videos/{video_id}/stages')
    assert rerun_stages_response.status_code == 200
    rerun_stages = rerun_stages_response.json()['data']
    assert any(item['stageId'] == 'transcribe' for item in rerun_stages)
