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


SCRIPT_JSON_TEXT = '''{
  "schemaVersion": "script_document_v1",
  "title": "Generated launch script",
  "metadata": {"platform": "TikTok", "videoRatio": "9:16", "duration": "30秒"},
  "segments": [
    {
      "segmentId": "S01",
      "time": "0-3秒",
      "goal": "Hook",
      "voiceover": "Generated script line 1",
      "subtitle": "Generated script line 1",
      "visualSuggestion": "桌面特写",
      "retentionPoint": "强钩子",
      "storyboardHint": "用近景开场"
    },
    {
      "segmentId": "S02",
      "time": "3-30秒",
      "goal": "Body",
      "voiceover": "Generated script line 2",
      "subtitle": "Generated script line 2",
      "visualSuggestion": "产品进入画面",
      "retentionPoint": "结果展示",
      "storyboardHint": "保持竖屏构图"
    }
  ],
  "voiceoverFull": "Generated script line 1\\nGenerated script line 2",
  "subtitles": ["Generated script line 1", "Generated script line 2"]
}'''

REWRITTEN_SCRIPT_JSON_TEXT = '''{
  "schemaVersion": "script_document_v1",
  "title": "Rewritten launch script",
  "metadata": {"platform": "TikTok", "videoRatio": "9:16", "duration": "30秒"},
  "segments": [
    {
      "segmentId": "S01",
      "time": "0-3秒",
      "goal": "Hook",
      "voiceover": "Rewritten script line 1",
      "subtitle": "Rewritten script line 1",
      "visualSuggestion": "旧方案和新方案对比",
      "retentionPoint": "反差",
      "storyboardHint": "用对比镜头"
    },
    {
      "segmentId": "S02",
      "time": "3-30秒",
      "goal": "Body",
      "voiceover": "Rewritten script line 2",
      "subtitle": "Rewritten script line 2",
      "visualSuggestion": "展示操作结果",
      "retentionPoint": "收益证明",
      "storyboardHint": "补充细节特写"
    }
  ],
  "voiceoverFull": "Rewritten script line 1\\nRewritten script line 2",
  "subtitles": ["Rewritten script line 1", "Rewritten script line 2"]
}'''


def assert_script_version_shape(version: dict[str, object]) -> None:
    assert set(version) == {
        'revision',
        'source',
        'content',
        'format',
        'documentJson',
        'provider',
        'model',
        'aiJobId',
        'createdAt',
    }


class FakeAITextGenerationService:
    def __init__(self, jobs: AIJobRepository) -> None:
        self._jobs = jobs

    def generate_text(self, capability_id: str, prompt: dict[str, str], **kwargs: object) -> FakeGenerationResult:
        job = self._jobs.create_running(
            project_id=str(kwargs.get('project_id')) if kwargs.get('project_id') else None,
            capability_id=capability_id,
            provider='openai',
            model='gpt-5' if capability_id == 'script_generation' else 'gpt-5-mini',
        )
        self._jobs.mark_succeeded(job.id, duration_ms=21)
        if 'count' in prompt:
            count = int(prompt['count'])
            topic = prompt.get('topic', '标题')
            text = '\n'.join(f'{topic} 标题 {index}' for index in range(1, count + 1))
        elif 'segment' in prompt:
            text = 'Rewrite hook\nRewrite body\nRewrite cta'
        elif capability_id == 'script_generation':
            text = SCRIPT_JSON_TEXT
        else:
            text = REWRITTEN_SCRIPT_JSON_TEXT
        return FakeGenerationResult(
            text=text,
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
    assert set(read_payload['data']) == {
        'projectId',
        'currentVersion',
        'versions',
        'recentJobs',
        'isSaved',
        'latestRevision',
        'saveSource',
        'latestAiJob',
        'lastOperation',
    }
    assert read_payload['data']['isSaved'] is False
    assert read_payload['data']['latestRevision'] is None
    assert read_payload['data']['saveSource'] is None
    assert read_payload['data']['latestAiJob'] is None
    assert read_payload['data']['lastOperation'] is None

    save_response = client.put(
        f'/api/scripts/projects/{project_id}/document',
        json={'content': 'Hook\nBody\nCTA'},
    )

    assert save_response.status_code == 200
    save_payload = save_response.json()
    assert set(save_payload) == {'ok', 'data'}
    assert save_payload['ok'] is True
    assert set(save_payload['data']) == {
        'projectId',
        'currentVersion',
        'versions',
        'recentJobs',
        'isSaved',
        'latestRevision',
        'saveSource',
        'latestAiJob',
        'lastOperation',
    }
    assert_script_version_shape(save_payload['data']['currentVersion'])
    assert save_payload['data']['isSaved'] is True
    assert save_payload['data']['latestRevision'] == 1
    assert save_payload['data']['saveSource'] == 'manual'
    assert save_payload['data']['latestAiJob'] is None
    assert set(save_payload['data']['lastOperation']) == {
        'revision',
        'source',
        'createdAt',
        'aiJobId',
        'aiJobStatus',
    }
    assert save_payload['data']['lastOperation']['source'] == 'manual'
    assert save_payload['data']['lastOperation']['aiJobStatus'] is None

    generate_response = client.post(
        f'/api/scripts/projects/{project_id}/generate',
        json={'topic': 'Launch topic'},
    )

    assert generate_response.status_code == 200
    generate_payload = generate_response.json()
    assert set(generate_payload) == {'ok', 'data'}
    assert generate_payload['ok'] is True
    assert set(generate_payload['data']) == {
        'projectId',
        'currentVersion',
        'versions',
        'recentJobs',
        'isSaved',
        'latestRevision',
        'saveSource',
        'latestAiJob',
        'lastOperation',
    }
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
    assert generate_payload['data']['latestRevision'] == 2
    assert generate_payload['data']['saveSource'] == 'ai_generate'
    assert generate_payload['data']['latestAiJob']['capabilityId'] == 'script_generation'
    assert generate_payload['data']['lastOperation']['source'] == 'ai_generate'
    assert generate_payload['data']['lastOperation']['aiJobStatus'] == 'succeeded'


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
    assert set(rewrite_payload['data']) == {
        'projectId',
        'currentVersion',
        'versions',
        'recentJobs',
        'isSaved',
        'latestRevision',
        'saveSource',
        'latestAiJob',
        'lastOperation',
    }
    assert rewrite_payload['data']['saveSource'] == 'ai_rewrite'
    assert rewrite_payload['data']['latestAiJob']['capabilityId'] == 'script_rewrite'
    assert rewrite_payload['data']['lastOperation']['source'] == 'ai_rewrite'
    assert rewrite_payload['data']['lastOperation']['aiJobStatus'] == 'succeeded'


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
    assert_script_version_shape(versions_payload['data'][0])

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
    assert set(rewrite_payload['data']) == {
        'projectId',
        'currentVersion',
        'versions',
        'recentJobs',
        'isSaved',
        'latestRevision',
        'saveSource',
        'latestAiJob',
        'lastOperation',
    }
    assert rewrite_payload['data']['saveSource'] == 'ai_segment_rewrite'
    assert rewrite_payload['data']['lastOperation']['source'] == 'ai_segment_rewrite'
    assert rewrite_payload['data']['lastOperation']['aiJobStatus'] == 'succeeded'

    restore_response = client.post(f'/api/scripts/projects/{project_id}/restore/1')
    assert restore_response.status_code == 200
    restore_payload = restore_response.json()
    assert set(restore_payload) == {'ok', 'data'}
    assert set(restore_payload['data']) == {
        'projectId',
        'currentVersion',
        'versions',
        'recentJobs',
        'isSaved',
        'latestRevision',
        'saveSource',
        'latestAiJob',
        'lastOperation',
    }
    assert restore_payload['data']['saveSource'] == 'restore'
    assert restore_payload['data']['lastOperation']['source'] == 'restore'
    assert restore_payload['data']['lastOperation']['aiJobStatus'] is None
