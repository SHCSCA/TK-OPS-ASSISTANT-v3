from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fastapi.testclient import TestClient

from repositories.ai_job_repository import AIJobRepository


@dataclass
class FakeGenerationResult:
    text: str
    provider: str
    model: str
    ai_job_id: str
    request_id: str


class FakeAITextGenerationService:
    def __init__(self, database_path: Path) -> None:
        self._jobs = AIJobRepository(database_path)

    def generate_text(self, capability_id: str, prompt: str, **kwargs: object) -> FakeGenerationResult:
        assert capability_id == 'storyboard_generation'
        job = self._jobs.create_running(
            project_id=str(kwargs.get('project_id')) if kwargs.get('project_id') else None,
            capability_id=capability_id,
            provider='openai',
            model='gpt-5-mini',
        )
        self._jobs.mark_succeeded(job.id, duration_ms=18)
        return FakeGenerationResult(
            text='''[
  {"title": "Hook", "summary": "Fast intro", "visualPrompt": "Close-up motion"},
  {"title": "Problem", "summary": "Show the pain point", "visualPrompt": "Messy desk scene"}
]''',
            provider='openai',
            model='gpt-5-mini',
            ai_job_id=job.id,
            request_id=job.id,
        )


def test_storyboard_generation_uses_current_script_and_persists_versions(runtime_app) -> None:
    runtime_app.state.ai_text_generation_service = FakeAITextGenerationService(
        runtime_app.state.runtime_config.database_path
    )
    client = TestClient(runtime_app)

    project_response = client.post(
        '/api/dashboard/projects',
        json={'name': 'Storyboard Project', 'description': 'Storyboard tests'},
    )
    project_id = project_response.json()['data']['id']

    script_response = client.put(
        f'/api/scripts/projects/{project_id}/document',
        json={'content': 'Hook\nProblem\nSolution\nCTA'},
    )

    assert script_response.status_code == 200

    generate_response = client.post(f'/api/storyboards/projects/{project_id}/generate')

    assert generate_response.status_code == 200
    payload = generate_response.json()['data']
    assert payload['projectId'] == project_id
    assert payload['basedOnScriptRevision'] == 1
    assert payload['currentVersion']['revision'] == 1
    assert payload['currentVersion']['source'] == 'ai_generate'
    assert len(payload['currentVersion']['scenes']) == 2
    assert payload['currentVersion']['provider'] == 'openai'
    assert payload['currentVersion']['model'] == 'gpt-5-mini'
    assert payload['recentJobs'][0]['capabilityId'] == 'storyboard_generation'

    save_response = client.put(
        f'/api/storyboards/projects/{project_id}/document',
        json={
            'basedOnScriptRevision': 1,
            'scenes': [
                {
                    'sceneId': 'scene-1',
                    'title': 'Hook',
                    'summary': 'Manual summary',
                    'visualPrompt': 'Manual visual'
                }
            ]
        },
    )

    assert save_response.status_code == 200
    saved_payload = save_response.json()['data']
    assert saved_payload['currentVersion']['revision'] == 2
    assert saved_payload['currentVersion']['source'] == 'manual'
    assert saved_payload['currentVersion']['scenes'][0]['summary'] == 'Manual summary'
