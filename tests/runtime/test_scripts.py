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
        self.calls: list[tuple[str, str]] = []
        self._jobs = AIJobRepository(database_path)

    def generate_text(self, capability_id: str, prompt: str, **kwargs: object) -> FakeGenerationResult:
        self.calls.append((capability_id, prompt))
        provider = 'openai'
        model = 'gpt-5' if capability_id == 'script_generation' else 'gpt-5-mini'
        job = self._jobs.create_running(
            project_id=str(kwargs.get('project_id')) if kwargs.get('project_id') else None,
            capability_id=capability_id,
            provider=provider,
            model=model,
        )
        self._jobs.mark_succeeded(job.id, duration_ms=12)
        if capability_id == 'script_generation':
            return FakeGenerationResult(
                text='Hook line\nBody line\nCTA line',
                provider=provider,
                model=model,
                ai_job_id=job.id,
                request_id=job.id,
            )

        return FakeGenerationResult(
            text='Rewrite hook\nRewrite body\nRewrite cta',
            provider=provider,
            model=model,
            ai_job_id=job.id,
            request_id=job.id,
        )


def test_script_document_supports_manual_save_and_version_history(runtime_app) -> None:
    client = TestClient(runtime_app)

    project_response = client.post(
        '/api/dashboard/projects',
        json={'name': 'Script Project', 'description': 'Script tests'},
    )
    project_id = project_response.json()['data']['id']

    read_response = client.get(f'/api/scripts/projects/{project_id}/document')

    assert read_response.status_code == 200
    empty_payload = read_response.json()['data']
    assert empty_payload['projectId'] == project_id
    assert empty_payload['currentVersion'] is None
    assert empty_payload['versions'] == []
    assert empty_payload['recentJobs'] == []

    save_response = client.put(
        f'/api/scripts/projects/{project_id}/document',
        json={'content': 'Opening hook\nMain point\nCTA'},
    )

    assert save_response.status_code == 200
    saved_payload = save_response.json()['data']
    assert saved_payload['currentVersion']['revision'] == 1
    assert saved_payload['currentVersion']['source'] == 'manual'
    assert saved_payload['currentVersion']['content'] == 'Opening hook\nMain point\nCTA'
    assert len(saved_payload['versions']) == 1


def test_script_generation_and_rewrite_record_ai_jobs(runtime_app) -> None:
    fake_service = FakeAITextGenerationService(runtime_app.state.runtime_config.database_path)
    runtime_app.state.ai_text_generation_service = fake_service
    client = TestClient(runtime_app)

    project_response = client.post(
        '/api/dashboard/projects',
        json={'name': 'AI Script Project', 'description': 'AI script tests'},
    )
    project_id = project_response.json()['data']['id']

    generate_response = client.post(
        f'/api/scripts/projects/{project_id}/generate',
        json={'topic': 'New product launch'},
    )

    assert generate_response.status_code == 200
    generated_payload = generate_response.json()['data']
    assert generated_payload['currentVersion']['revision'] == 1
    assert generated_payload['currentVersion']['source'] == 'ai_generate'
    assert generated_payload['currentVersion']['provider'] == 'openai'
    assert generated_payload['currentVersion']['model'] == 'gpt-5'
    assert generated_payload['recentJobs'][0]['status'] == 'succeeded'
    assert generated_payload['recentJobs'][0]['capabilityId'] == 'script_generation'

    rewrite_response = client.post(
        f'/api/scripts/projects/{project_id}/rewrite',
        json={'instructions': 'Make it more urgent'},
    )

    assert rewrite_response.status_code == 200
    rewritten_payload = rewrite_response.json()['data']
    assert rewritten_payload['currentVersion']['revision'] == 2
    assert rewritten_payload['currentVersion']['source'] == 'ai_rewrite'
    assert len(rewritten_payload['versions']) == 2
    assert rewritten_payload['recentJobs'][0]['capabilityId'] == 'script_rewrite'
    assert fake_service.calls[0][0] == 'script_generation'
    assert fake_service.calls[1][0] == 'script_rewrite'
