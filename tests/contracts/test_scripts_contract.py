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
        job = self._jobs.create_running(
            project_id=str(kwargs.get('project_id')) if kwargs.get('project_id') else None,
            capability_id=capability_id,
            provider='openai',
            model='gpt-5' if capability_id == 'script_generation' else 'gpt-5-mini',
        )
        self._jobs.mark_succeeded(job.id, duration_ms=21)
        return FakeGenerationResult(
            text='Generated script line 1\nGenerated script line 2'
            if capability_id == 'script_generation'
            else 'Rewritten script line 1\nRewritten script line 2',
            provider='openai',
            model='gpt-5' if capability_id == 'script_generation' else 'gpt-5-mini',
            ai_job_id=job.id,
        )


def test_script_document_contracts_use_scripts_prefix_and_expected_shape(runtime_app) -> None:
    runtime_app.state.ai_text_generation_service = FakeAITextGenerationService(
        runtime_app.state.ai_job_repository
    )
    client = TestClient(runtime_app)

    create_response = client.post(
        '/api/dashboard/projects',
        json={'name': 'Script Contract', 'description': 'Contract coverage'},
    )
    project_id = create_response.json()['data']['id']

    read_response = client.get(f'/api/scripts/projects/{project_id}/document')

    assert read_response.status_code == 200
    read_payload = read_response.json()
    assert set(read_payload) == {'ok', 'data'}
    assert read_payload['ok'] is True
    assert set(read_payload['data']) == {'projectId', 'currentVersion', 'versions', 'recentJobs'}

    save_response = client.put(
        f'/api/scripts/projects/{project_id}/document',
        json={'content': 'Hook\nBody\nCTA'},
    )

    assert save_response.status_code == 200
    save_payload = save_response.json()
    assert set(save_payload) == {'ok', 'data'}
    assert save_payload['ok'] is True
    assert set(save_payload['data']) == {'projectId', 'currentVersion', 'versions', 'recentJobs'}
    assert set(save_payload['data']['currentVersion']) == {
        'revision',
        'source',
        'content',
        'provider',
        'model',
        'aiJobId',
        'createdAt',
    }

    generate_response = client.post(
        f'/api/scripts/projects/{project_id}/generate',
        json={'topic': 'Launch topic'},
    )

    assert generate_response.status_code == 200
    generate_payload = generate_response.json()
    assert set(generate_payload) == {'ok', 'data'}
    assert generate_payload['ok'] is True
    assert set(generate_payload['data']) == {'projectId', 'currentVersion', 'versions', 'recentJobs'}
    assert set(generate_payload['data']['recentJobs'][0]) == {
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


def test_script_rewrite_contract_keeps_json_envelope(runtime_app) -> None:
    runtime_app.state.ai_text_generation_service = FakeAITextGenerationService(
        runtime_app.state.ai_job_repository
    )
    client = TestClient(runtime_app)

    create_response = client.post(
        '/api/dashboard/projects',
        json={'name': 'Script Rewrite Contract', 'description': 'Contract coverage'},
    )
    project_id = create_response.json()['data']['id']
    client.put(
        f'/api/scripts/projects/{project_id}/document',
        json={'content': 'Draft script'},
    )

    rewrite_response = client.post(
        f'/api/scripts/projects/{project_id}/rewrite',
        json={'instructions': 'Make it tighter'},
    )

    assert rewrite_response.status_code == 200
    rewrite_payload = rewrite_response.json()
    assert set(rewrite_payload) == {'ok', 'data'}
    assert rewrite_payload['ok'] is True
    assert set(rewrite_payload['data']) == {'projectId', 'currentVersion', 'versions', 'recentJobs'}


def test_script_versions_title_variants_and_segment_rewrite_contract(runtime_app) -> None:
    runtime_app.state.ai_text_generation_service = FakeAITextGenerationService(
        runtime_app.state.ai_job_repository
    )
    client = TestClient(runtime_app)

    create_response = client.post(
        '/api/dashboard/projects',
        json={'name': 'Script Extra Contract', 'description': 'Contract coverage'},
    )
    project_id = create_response.json()['data']['id']
    client.put(
        f'/api/scripts/projects/{project_id}/document',
        json={'content': 'Draft hook\nDraft body\nDraft CTA'},
    )

    versions_response = client.get(f'/api/scripts/projects/{project_id}/versions')
    assert versions_response.status_code == 200
    versions_payload = versions_response.json()
    assert set(versions_payload) == {'ok', 'data'}
    assert isinstance(versions_payload['data'], list)
    assert set(versions_payload['data'][0]) == {
        'revision',
        'source',
        'content',
        'provider',
        'model',
        'aiJobId',
        'createdAt',
    }

    title_response = client.post(
        f'/api/scripts/projects/{project_id}/title-variants',
        json={'topic': 'Launch', 'count': 2},
    )
    assert title_response.status_code == 200
    title_payload = title_response.json()
    assert set(title_payload) == {'ok', 'data'}
    assert len(title_payload['data']) == 2
    assert set(title_payload['data'][0]) == {'title'}

    rewrite_response = client.post(
        f'/api/scripts/projects/{project_id}/segments/2/rewrite',
        json={'instructions': '更有号召力'},
    )
    assert rewrite_response.status_code == 200
    rewrite_payload = rewrite_response.json()
    assert set(rewrite_payload) == {'ok', 'data'}
    assert set(rewrite_payload['data']) == {'projectId', 'currentVersion', 'versions', 'recentJobs'}

    restore_response = client.post(f'/api/scripts/projects/{project_id}/restore/1')
    assert restore_response.status_code == 200
    restore_payload = restore_response.json()
    assert set(restore_payload) == {'ok', 'data'}
    assert set(restore_payload['data']) == {'projectId', 'currentVersion', 'versions', 'recentJobs'}
