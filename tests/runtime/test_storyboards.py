from __future__ import annotations

from dataclasses import dataclass

from fastapi.testclient import TestClient

from repositories.ai_job_repository import AIJobRepository
from services.storyboard_scene_parser import parse_storyboard_scenes


@dataclass
class FakeGenerationResult:
    text: str
    provider: str
    model: str
    ai_job_id: str
    request_id: str


class FakeAITextGenerationService:
    def __init__(self, jobs: AIJobRepository) -> None:
        self._jobs = jobs

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


class FencedJsonAITextGenerationService:
    def __init__(self, jobs: AIJobRepository) -> None:
        self._jobs = jobs

    def generate_text(self, capability_id: str, prompt: str, **kwargs: object) -> FakeGenerationResult:
        assert capability_id == 'storyboard_generation'
        job = self._jobs.create_running(
            project_id=str(kwargs.get('project_id')) if kwargs.get('project_id') else None,
            capability_id=capability_id,
            provider='deepseek',
            model='deepseek-chat',
        )
        self._jobs.mark_succeeded(job.id, duration_ms=22)
        return FakeGenerationResult(
            text='''下面是分镜 JSON：
```json
[
  {"title": "开场钩子", "summary": "冰块落入杯中", "visualPrompt": "透明玻璃杯微距俯拍"},
  {"title": "产品特写", "summary": "展示杯身和容量", "visualPrompt": "侧光突出刻度"}
]
```
''',
            provider='deepseek',
            model='deepseek-chat',
            ai_job_id=job.id,
            request_id=job.id,
        )


class MarkdownTableAITextGenerationService:
    def __init__(self, jobs: AIJobRepository) -> None:
        self._jobs = jobs

    def generate_text(self, capability_id: str, prompt: str, **kwargs: object) -> FakeGenerationResult:
        assert capability_id == 'storyboard_generation'
        job = self._jobs.create_running(
            project_id=str(kwargs.get('project_id')) if kwargs.get('project_id') else None,
            capability_id=capability_id,
            provider='deepseek',
            model='deepseek-chat',
        )
        self._jobs.mark_succeeded(job.id, duration_ms=24)
        return FakeGenerationResult(
            text='''| 时间点 | 画面内容 | 镜头/机位 | 字幕/台词 | 音效 |
| --- | --- | --- | --- | --- |
| 0-2s | 冰块落入透明杯 | 微距俯拍 | 春天第一杯冷饮 | 冰块碰杯声 |
| 3-6s | 倒入咖啡并推近杯身 | 侧光特写 | 低糖清爽不腻 | 轻快节拍 |
''',
            provider='deepseek',
            model='deepseek-chat',
            ai_job_id=job.id,
            request_id=job.id,
        )


class PlainMarkdownAITextGenerationService:
    def __init__(self, jobs: AIJobRepository) -> None:
        self._jobs = jobs

    def generate_text(self, capability_id: str, prompt: str, **kwargs: object) -> FakeGenerationResult:
        assert capability_id == 'storyboard_generation'
        job = self._jobs.create_running(
            project_id=str(kwargs.get('project_id')) if kwargs.get('project_id') else None,
            capability_id=capability_id,
            provider='deepseek',
            model='deepseek-chat',
        )
        self._jobs.mark_succeeded(job.id, duration_ms=20)
        return FakeGenerationResult(
            text='# TikTok 分镜执行方案\n\n这是一份没有结构化镜头表的 Markdown 原文。',
            provider='deepseek',
            model='deepseek-chat',
            ai_job_id=job.id,
            request_id=job.id,
        )


def test_storyboard_generation_uses_current_script_and_persists_versions(runtime_app) -> None:
    runtime_app.state.ai_text_generation_service = FakeAITextGenerationService(
        runtime_app.state.ai_job_repository
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
    assert payload['currentScriptRevision'] == 1
    assert payload['currentVersion']['revision'] == 1
    assert payload['currentVersion']['source'] == 'ai_generate'
    assert len(payload['currentVersion']['scenes']) == 2
    assert payload['currentVersion']['provider'] == 'openai'
    assert payload['currentVersion']['model'] == 'gpt-5-mini'
    assert payload['recentJobs'][0]['capabilityId'] == 'storyboard_generation'
    assert payload['syncStatus'] == 'synced'
    assert payload['conflictSummary'] == {
        'hasConflict': False,
        'reason': None,
        'currentScriptRevision': 1,
        'basedOnScriptRevision': 1,
        'storyboardRevision': 1,
    }
    assert payload['latestAiJob']['capabilityId'] == 'storyboard_generation'
    assert payload['lastOperation']['source'] == 'ai_generate'
    assert payload['lastOperation']['aiJobStatus'] == 'succeeded'

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
    assert saved_payload['syncStatus'] == 'synced'
    assert saved_payload['lastOperation']['source'] == 'manual'
    assert saved_payload['lastOperation']['aiJobStatus'] is None


def test_storyboard_generation_accepts_fenced_json_provider_output(runtime_app) -> None:
    runtime_app.state.ai_text_generation_service = FencedJsonAITextGenerationService(
        runtime_app.state.ai_job_repository
    )
    client = TestClient(runtime_app)

    project_response = client.post(
        '/api/dashboard/projects',
        json={'name': 'Storyboard Fenced JSON', 'description': 'fenced json'},
    )
    project_id = project_response.json()['data']['id']

    script_response = client.put(
        f'/api/scripts/projects/{project_id}/document',
        json={'content': '# 春日咖啡冷饮\n\n| 时间 | 画面 |\n| --- | --- |\n| 0-1s | 冰块落入杯中 |'},
    )
    assert script_response.status_code == 200

    generate_response = client.post(f'/api/storyboards/projects/{project_id}/generate')

    assert generate_response.status_code == 200
    payload = generate_response.json()['data']
    assert payload['currentVersion']['provider'] == 'deepseek'
    assert payload['currentVersion']['model'] == 'deepseek-chat'
    assert '```json' in payload['currentVersion']['markdown']
    assert payload['currentVersion']['scenes'][0]['title'] == '开场钩子'
    assert payload['currentVersion']['scenes'][1]['summary'] == '展示杯身和容量'


def test_storyboard_generation_accepts_markdown_table_provider_output(runtime_app) -> None:
    runtime_app.state.ai_text_generation_service = MarkdownTableAITextGenerationService(
        runtime_app.state.ai_job_repository
    )
    client = TestClient(runtime_app)

    project_response = client.post(
        '/api/dashboard/projects',
        json={'name': 'Storyboard Markdown Table', 'description': 'markdown table'},
    )
    project_id = project_response.json()['data']['id']

    script_response = client.put(
        f'/api/scripts/projects/{project_id}/document',
        json={'content': '# 春日咖啡冷饮\n\n请生成可执行分镜。'},
    )
    assert script_response.status_code == 200

    generate_response = client.post(f'/api/storyboards/projects/{project_id}/generate')

    assert generate_response.status_code == 200
    payload = generate_response.json()['data']
    scenes = payload['currentVersion']['scenes']
    assert len(scenes) == 2
    assert scenes[0]['title'] == '镜头1 0-2s'
    assert '冰块落入透明杯' in scenes[0]['summary']
    assert '微距俯拍' in scenes[0]['visualPrompt']
    assert scenes[0]['time'] == '0-2s'
    assert scenes[0]['cameraAngle'] == '微距俯拍'
    assert scenes[0]['voiceover'] == '春天第一杯冷饮'
    assert '| 时间点 | 画面内容 |' in payload['currentVersion']['markdown']


def test_storyboard_markdown_parser_ignores_non_storyboard_document_headings() -> None:
    scenes = parse_storyboard_scenes(
        '\n'.join(
            [
                '# TikTok短视频脚本',
                '',
                '## 1. 脚本元信息',
                '',
                '| 项目 | 内容 |',
                '|---|---|',
                '| 平台 | TikTok |',
                '',
                '## 镜头1 0-3秒',
                '',
                '手持冰霸杯特写，展示杯身和冰块反光。',
                '',
                '## 镜头2 3-6秒',
                '',
                '咖啡倒入杯中，形成分层。',
            ]
        )
    )

    assert len(scenes) == 2
    assert scenes[0]['title'] == '镜头1 0-3秒'
    assert '手持冰霸杯特写' in scenes[0]['summary']
    assert scenes[1]['title'] == '镜头2 3-6秒'


def test_storyboard_generation_preserves_unparsed_markdown_provider_output(runtime_app) -> None:
    runtime_app.state.ai_text_generation_service = PlainMarkdownAITextGenerationService(
        runtime_app.state.ai_job_repository
    )
    client = TestClient(runtime_app)

    project_response = client.post(
        '/api/dashboard/projects',
        json={'name': 'Storyboard Plain Markdown', 'description': 'plain markdown'},
    )
    project_id = project_response.json()['data']['id']

    script_response = client.put(
        f'/api/scripts/projects/{project_id}/document',
        json={'content': '# Spring Iced Coffee'},
    )
    assert script_response.status_code == 200

    generate_response = client.post(f'/api/storyboards/projects/{project_id}/generate')

    assert generate_response.status_code == 200
    payload = generate_response.json()['data']
    assert payload['currentVersion']['markdown'].startswith('# TikTok 分镜执行方案')
    assert payload['currentVersion']['scenes']
    assert '没有结构化镜头表' in payload['currentVersion']['scenes'][0]['summary']


def test_storyboard_manual_save_preserves_markdown_source(runtime_app) -> None:
    client = TestClient(runtime_app)

    project_response = client.post(
        '/api/dashboard/projects',
        json={'name': 'Storyboard Markdown Source', 'description': 'manual markdown'},
    )
    project_id = project_response.json()['data']['id']

    script_response = client.put(
        f'/api/scripts/projects/{project_id}/document',
        json={'content': '# Spring Iced Coffee'},
    )
    assert script_response.status_code == 200

    markdown = '# 手动分镜\n\n这是一份直接在分镜工作面维护的 Markdown 原文。'
    save_response = client.put(
        f'/api/storyboards/projects/{project_id}/document',
        json={
            'basedOnScriptRevision': 1,
            'markdown': markdown,
            'scenes': [],
        },
    )

    assert save_response.status_code == 200
    payload = save_response.json()['data']
    assert payload['currentVersion']['source'] == 'manual'
    assert payload['currentVersion']['markdown'] == markdown
    assert payload['currentVersion']['scenes']
    assert payload['currentVersion']['scenes'][0]['summary']


def test_storyboard_shot_crud_templates_and_sync_from_script(runtime_app) -> None:
    runtime_app.state.ai_text_generation_service = FakeAITextGenerationService(
        runtime_app.state.ai_job_repository
    )
    client = TestClient(runtime_app)

    project_response = client.post(
        '/api/dashboard/projects',
        json={'name': 'Storyboard Shot Project', 'description': 'Storyboard shots'},
    )
    project_id = project_response.json()['data']['id']

    script_response = client.put(
        f'/api/scripts/projects/{project_id}/document',
        json={'content': 'Hook\nProblem\nSolution\nCTA'},
    )
    assert script_response.status_code == 200

    sync_response = client.post(f'/api/storyboards/projects/{project_id}/sync-from-script')
    assert sync_response.status_code == 200
    synced_payload = sync_response.json()['data']
    assert synced_payload['currentVersion']['revision'] == 1
    assert len(synced_payload['currentVersion']['scenes']) == 4
    assert synced_payload['syncStatus'] == 'synced'
    assert synced_payload['lastOperation']['source'] == 'sync_from_script'

    templates_response = client.get('/api/storyboards/templates')
    assert templates_response.status_code == 200
    templates_payload = templates_response.json()['data']
    assert len(templates_payload) >= 1

    create_response = client.post(
        f'/api/storyboards/projects/{project_id}/shots',
        json={
            'title': '追加镜头',
            'summary': '补一段新的镜头说明',
            'visualPrompt': '补充一个更强的画面指令',
        },
    )
    assert create_response.status_code == 200
    created_payload = create_response.json()['data']
    assert created_payload['currentVersion']['revision'] == 2
    created_scene = created_payload['currentVersion']['scenes'][-1]
    assert created_scene['title'] == '追加镜头'
    assert created_payload['syncStatus'] == 'synced'
    assert created_payload['lastOperation']['source'] == 'shot_create'

    shot_id = created_scene['sceneId']
    update_response = client.patch(
        f'/api/storyboards/projects/{project_id}/shots/{shot_id}',
        json={
            'title': '追加镜头-更新',
            'summary': '更新后的镜头说明',
            'visualPrompt': '更新后的画面指令',
        },
    )
    assert update_response.status_code == 200
    updated_payload = update_response.json()['data']
    assert updated_payload['currentVersion']['revision'] == 3
    updated_scene = [
        item for item in updated_payload['currentVersion']['scenes'] if item['sceneId'] == shot_id
    ][0]
    assert updated_scene['title'] == '追加镜头-更新'
    assert updated_payload['lastOperation']['source'] == 'shot_update'

    delete_response = client.delete(f'/api/storyboards/projects/{project_id}/shots/{shot_id}')
    assert delete_response.status_code == 200
    deleted_payload = delete_response.json()['data']
    assert deleted_payload['currentVersion']['revision'] == 4
    assert all(item['sceneId'] != shot_id for item in deleted_payload['currentVersion']['scenes'])
    assert deleted_payload['lastOperation']['source'] == 'shot_delete'


def test_storyboard_document_reports_outdated_when_script_advances(runtime_client: TestClient) -> None:
    project_response = runtime_client.post(
        '/api/dashboard/projects',
        json={'name': 'Storyboard Sync Gap', 'description': 'sync gap'},
    )
    project_id = project_response.json()['data']['id']

    first_script = runtime_client.put(
        f'/api/scripts/projects/{project_id}/document',
        json={'content': 'Hook\nProblem\nSolution'},
    )
    assert first_script.status_code == 200

    sync_response = runtime_client.post(f'/api/storyboards/projects/{project_id}/sync-from-script')
    assert sync_response.status_code == 200

    second_script = runtime_client.put(
        f'/api/scripts/projects/{project_id}/document',
        json={'content': 'Hook updated\nProblem updated\nSolution updated'},
    )
    assert second_script.status_code == 200

    document_response = runtime_client.get(f'/api/storyboards/projects/{project_id}/document')
    assert document_response.status_code == 200
    payload = document_response.json()['data']
    assert payload['currentScriptRevision'] == 2
    assert payload['basedOnScriptRevision'] == 1
    assert payload['syncStatus'] == 'outdated'
    assert payload['conflictSummary'] == {
        'hasConflict': True,
        'reason': '当前分镜基于旧脚本版本，建议先重新同步再继续编辑。',
        'currentScriptRevision': 2,
        'basedOnScriptRevision': 1,
        'storyboardRevision': 1,
    }
