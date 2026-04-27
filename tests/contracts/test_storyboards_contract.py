from __future__ import annotations

from dataclasses import dataclass

from fastapi.testclient import TestClient

from repositories.ai_job_repository import AIJobRepository


@dataclass
class FakeGenerationResult:
    text: str
    provider: str
    model: str
    ai_job_id: str


STORYBOARD_SCENE_KEYS = {
    'sceneId',
    'title',
    'summary',
    'visualPrompt',
    'action',
    'audio',
    'cameraAngle',
    'cameraMovement',
    'shootingNote',
    'shotLabel',
    'shotSize',
    'subtitle',
    'time',
    'transition',
    'visualContent',
    'voiceover',
}


class FakeAITextGenerationService:
    def __init__(self, jobs: AIJobRepository) -> None:
        self._jobs = jobs

    def generate_text(self, capability_id: str, _: dict[str, str], **kwargs: object) -> FakeGenerationResult:
        assert capability_id == 'storyboard_generation'
        job = self._jobs.create_running(
            project_id=str(kwargs.get('project_id')) if kwargs.get('project_id') else None,
            capability_id=capability_id,
            provider='openai',
            model='gpt-5-mini',
        )
        self._jobs.mark_succeeded(job.id, duration_ms=17)
        return FakeGenerationResult(
            text='''[
  {"title": "Hook", "summary": "Fast intro", "visualPrompt": "Close-up motion"},
  {"title": "Problem", "summary": "Pain point", "visualPrompt": "Messy desk"}
]''',
            provider='openai',
            model='gpt-5-mini',
            ai_job_id=job.id,
        )


def assert_storyboard_scene_shape(scene: dict[str, object]) -> None:
    assert set(scene) == STORYBOARD_SCENE_KEYS


def assert_storyboard_version_shape(version: dict[str, object]) -> None:
    assert set(version) == {
        'revision',
        'basedOnScriptRevision',
        'source',
        'scenes',
        'markdown',
        'format',
        'storyboardJson',
        'provider',
        'model',
        'aiJobId',
        'createdAt',
    }
    assert isinstance(version['scenes'], list)
    if version['scenes']:
        assert_storyboard_scene_shape(version['scenes'][0])


def assert_storyboard_document_shape(document: dict[str, object]) -> None:
    assert set(document) == {
        'projectId',
        'basedOnScriptRevision',
        'currentScriptRevision',
        'currentVersion',
        'versions',
        'recentJobs',
        'syncStatus',
        'conflictSummary',
        'latestAiJob',
        'lastOperation',
    }
    assert set(document['conflictSummary']) == {
        'hasConflict',
        'reason',
        'currentScriptRevision',
        'basedOnScriptRevision',
        'storyboardRevision',
    }
    current_version = document['currentVersion']
    if current_version is not None:
        assert_storyboard_version_shape(current_version)
    latest_ai_job = document['latestAiJob']
    if latest_ai_job is not None:
        assert set(latest_ai_job) == {
            'id',
            'capabilityId',
            'provider',
            'model',
            'status',
            'error',
            'durationMs',
            'createdAt',
            'completedAt',
        }
    last_operation = document['lastOperation']
    if last_operation is not None:
        assert set(last_operation) == {
            'revision',
            'source',
            'createdAt',
            'aiJobId',
            'aiJobStatus',
        }


def assert_storyboard_template_shape(template: dict[str, object]) -> None:
    assert set(template) == {'id', 'name', 'description', 'shots'}
    assert isinstance(template['shots'], list)
    if template['shots']:
        assert_storyboard_scene_shape(template['shots'][0])


def test_storyboard_document_contracts_use_storyboards_prefix_and_expected_shape(runtime_app) -> None:
    runtime_app.state.ai_text_generation_service = FakeAITextGenerationService(
        runtime_app.state.ai_job_repository
    )
    client = TestClient(runtime_app)

    create_response = client.post(
        '/api/dashboard/projects',
        json={'name': 'Storyboard Contract', 'description': 'Contract coverage'},
    )
    project_id = create_response.json()['data']['id']

    client.put(
        f'/api/scripts/projects/{project_id}/document',
        json={'content': 'Hook\nProblem\nSolution'},
    )

    read_response = client.get(f'/api/storyboards/projects/{project_id}/document')

    assert read_response.status_code == 200
    read_payload = read_response.json()
    assert set(read_payload) == {'ok', 'data'}
    assert read_payload['ok'] is True
    assert_storyboard_document_shape(read_payload['data'])
    assert read_payload['data']['currentScriptRevision'] == 1
    assert read_payload['data']['syncStatus'] == 'missing_storyboard'
    assert read_payload['data']['latestAiJob'] is None
    assert read_payload['data']['lastOperation'] is None
    assert read_payload['data']['conflictSummary'] == {
        'hasConflict': False,
        'reason': '当前项目还没有分镜版本，可以从脚本同步生成。',
        'currentScriptRevision': 1,
        'basedOnScriptRevision': None,
        'storyboardRevision': None,
    }

    generate_response = client.post(f'/api/storyboards/projects/{project_id}/generate')

    assert generate_response.status_code == 200
    generate_payload = generate_response.json()
    assert set(generate_payload) == {'ok', 'data'}
    assert generate_payload['ok'] is True
    assert_storyboard_document_shape(generate_payload['data'])
    assert generate_payload['data']['currentScriptRevision'] == 1
    assert generate_payload['data']['syncStatus'] == 'synced'
    assert generate_payload['data']['latestAiJob']['capabilityId'] == 'storyboard_generation'
    assert generate_payload['data']['lastOperation']['source'] == 'ai_generate'
    assert generate_payload['data']['lastOperation']['aiJobStatus'] == 'succeeded'

    save_response = client.put(
        f'/api/storyboards/projects/{project_id}/document',
        json={
            'basedOnScriptRevision': 1,
            'scenes': [
                {
                    'sceneId': 'scene-1',
                    'title': 'Hook',
                    'summary': 'Manual summary',
                    'visualPrompt': 'Manual visual',
                }
            ],
        },
    )

    assert save_response.status_code == 200
    save_payload = save_response.json()
    assert set(save_payload) == {'ok', 'data'}
    assert save_payload['ok'] is True
    assert_storyboard_document_shape(save_payload['data'])
    assert save_payload['data']['syncStatus'] == 'synced'
    assert save_payload['data']['latestAiJob']['capabilityId'] == 'storyboard_generation'
    assert save_payload['data']['lastOperation']['source'] == 'manual'
    assert save_payload['data']['lastOperation']['aiJobStatus'] is None


def test_storyboard_shots_templates_and_sync_contract(runtime_app) -> None:
    runtime_app.state.ai_text_generation_service = FakeAITextGenerationService(
        runtime_app.state.ai_job_repository
    )
    client = TestClient(runtime_app)

    create_response = client.post(
        '/api/dashboard/projects',
        json={'name': 'Storyboard Extra Contract', 'description': 'Contract coverage'},
    )
    project_id = create_response.json()['data']['id']
    client.put(
        f'/api/scripts/projects/{project_id}/document',
        json={'content': 'Hook\nProblem\nSolution\nCTA'},
    )

    templates_response = client.get('/api/storyboards/templates')
    assert templates_response.status_code == 200
    templates_payload = templates_response.json()
    assert set(templates_payload) == {'ok', 'data'}
    assert isinstance(templates_payload['data'], list)
    assert templates_payload['data']
    assert_storyboard_template_shape(templates_payload['data'][0])

    sync_response = client.post(f'/api/storyboards/projects/{project_id}/sync-from-script')
    assert sync_response.status_code == 200
    sync_payload = sync_response.json()
    assert set(sync_payload) == {'ok', 'data'}
    assert_storyboard_document_shape(sync_payload['data'])
    assert sync_payload['data']['syncStatus'] == 'synced'
    assert sync_payload['data']['latestAiJob'] is None
    assert sync_payload['data']['lastOperation']['source'] == 'sync_from_script'

    create_shot_response = client.post(
        f'/api/storyboards/projects/{project_id}/shots',
        json={
            'title': '新增镜头',
            'summary': '镜头说明',
            'visualPrompt': '画面提示',
        },
    )
    assert create_shot_response.status_code == 200
    create_shot_payload = create_shot_response.json()
    assert set(create_shot_payload) == {'ok', 'data'}
    assert_storyboard_document_shape(create_shot_payload['data'])
    assert create_shot_payload['data']['syncStatus'] == 'synced'
    assert create_shot_payload['data']['lastOperation']['source'] == 'shot_create'
