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
    assert set(read_payload['data']) == {
        'projectId',
        'basedOnScriptRevision',
        'currentVersion',
        'versions',
        'recentJobs',
    }

    generate_response = client.post(f'/api/storyboards/projects/{project_id}/generate')

    assert generate_response.status_code == 200
    generate_payload = generate_response.json()
    assert set(generate_payload) == {'ok', 'data'}
    assert generate_payload['ok'] is True
    assert set(generate_payload['data']) == {
        'projectId',
        'basedOnScriptRevision',
        'currentVersion',
        'versions',
        'recentJobs',
    }
    assert set(generate_payload['data']['currentVersion']) == {
        'revision',
        'basedOnScriptRevision',
        'source',
        'scenes',
        'provider',
        'model',
        'aiJobId',
        'createdAt',
    }
    assert set(generate_payload['data']['currentVersion']['scenes'][0]) == {
        'sceneId',
        'title',
        'summary',
        'visualPrompt',
    }

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
    assert set(save_payload['data']) == {
        'projectId',
        'basedOnScriptRevision',
        'currentVersion',
        'versions',
        'recentJobs',
    }
