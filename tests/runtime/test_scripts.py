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
    request_id: str


class FakeAITextGenerationService:
    def __init__(self, jobs: AIJobRepository) -> None:
        self.calls: list[tuple[str, dict[str, str]]] = []
        self._jobs = jobs

    def generate_text(self, capability_id: str, prompt: dict[str, str], **kwargs: object) -> FakeGenerationResult:
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
        if 'count' in prompt:
            count = int(prompt['count'])
            topic = prompt.get('topic', '标题')
            return FakeGenerationResult(
                text='\n'.join(f'{topic} 标题 {index}' for index in range(1, count + 1)),
                provider=provider,
                model=model,
                ai_job_id=job.id,
                request_id=job.id,
            )
        if capability_id == 'script_generation':
            return FakeGenerationResult(
                text='''{
  "schemaVersion": "script_document_v1",
  "title": "New product launch",
  "metadata": {"platform": "TikTok", "videoRatio": "9:16", "duration": "30秒"},
  "segments": [
    {"segmentId": "S01", "time": "0-3秒", "goal": "Hook", "voiceover": "Hook line", "subtitle": "Hook line"},
    {"segmentId": "S02", "time": "3-15秒", "goal": "Body", "voiceover": "Body line", "subtitle": "Body line"},
    {"segmentId": "S03", "time": "15-30秒", "goal": "CTA", "voiceover": "CTA line", "subtitle": "CTA line"}
  ],
  "voiceoverFull": "Hook line\\nBody line\\nCTA line",
  "subtitles": ["Hook line", "Body line", "CTA line"]
}''',
                provider=provider,
                model=model,
                ai_job_id=job.id,
                request_id=job.id,
            )

        if 'segment' in prompt:
            return FakeGenerationResult(
                text='Rewrite hook\nRewrite body\nRewrite cta',
                provider=provider,
                model=model,
                ai_job_id=job.id,
                request_id=job.id,
            )

        return FakeGenerationResult(
            text='''{
  "schemaVersion": "script_document_v1",
  "title": "Rewritten product launch",
  "metadata": {"platform": "TikTok", "videoRatio": "9:16", "duration": "30秒"},
  "segments": [
    {"segmentId": "S01", "time": "0-3秒", "goal": "Hook", "voiceover": "Rewrite hook", "subtitle": "Rewrite hook"},
    {"segmentId": "S02", "time": "3-15秒", "goal": "Body", "voiceover": "Rewrite body", "subtitle": "Rewrite body"},
    {"segmentId": "S03", "time": "15-30秒", "goal": "CTA", "voiceover": "Rewrite cta", "subtitle": "Rewrite cta"}
  ],
  "voiceoverFull": "Rewrite hook\\nRewrite body\\nRewrite cta",
  "subtitles": ["Rewrite hook", "Rewrite body", "Rewrite cta"]
}''',
            provider=provider,
            model=model,
            ai_job_id=job.id,
            request_id=job.id,
        )


class JsonScriptAITextGenerationService:
    def __init__(self, jobs: AIJobRepository) -> None:
        self._jobs = jobs

    def generate_text(self, capability_id: str, prompt: dict[str, str], **kwargs: object) -> FakeGenerationResult:
        provider = 'openai'
        model = 'gpt-5'
        job = self._jobs.create_running(
            project_id=str(kwargs.get('project_id')) if kwargs.get('project_id') else None,
            capability_id=capability_id,
            provider=provider,
            model=model,
        )
        self._jobs.mark_succeeded(job.id, duration_ms=10)
        if capability_id == 'script_generation':
            text = '''
            {
              "schemaVersion": "script_document_v1",
              "title": "春日咖啡冷饮短视频脚本",
              "metadata": {
                "platform": "TikTok",
                "videoRatio": "9:16",
                "duration": "30秒",
                "targetUsers": "办公室人群",
                "videoGoal": "种草",
                "contentStyle": "真实口播",
                "shootingMethod": "产品实拍",
                "language": "中文",
                "scriptVersion": "v1",
                "handoff": "可进入脚本改写 / 分镜生成"
              },
              "strategy": {
                "corePainPoint": "下午犯困，冷饮变淡",
                "userEmotion": "想要清爽又省事",
                "contentAngle": "办公室续命咖啡",
                "mainHook": "一杯撑到下班",
                "conversionGoal": "评论互动",
                "complianceNote": "避免绝对化承诺"
              },
              "hooks": [
                {"label": "钩子方案一", "text": "下午三点别再喝温咖啡了。"}
              ],
              "segments": [
                {
                  "segmentId": "S01",
                  "time": "0-3秒",
                  "goal": "钩子",
                  "voiceover": "下午三点别再喝温咖啡了。",
                  "subtitle": "下午三点，拒绝温咖啡",
                  "visualSuggestion": "手把旧杯推开，冰霸杯放到桌面中心",
                  "retentionPoint": "痛点直击",
                  "storyboardHint": "开场用桌面特写"
                },
                {
                  "segmentId": "S02",
                  "time": "3-7秒",
                  "goal": "解决方案",
                  "voiceover": "这一杯冰咖啡能陪我撑完整个下午。",
                  "subtitle": "一杯撑完整个下午",
                  "visualSuggestion": "倒入冰块和咖啡，展示分层",
                  "retentionPoint": "视觉证明",
                  "storyboardHint": "用慢动作展示分层"
                }
              ],
              "voiceoverFull": "下午三点别再喝温咖啡了。\\n这一杯冰咖啡能陪我撑完整个下午。",
              "subtitles": ["下午三点，拒绝温咖啡", "一杯撑完整个下午"],
              "shootingChecklist": {
                "scenes": ["办公室桌面"],
                "props": ["冰霸杯", "冰块", "咖啡"],
                "characters": ["年轻白领"],
                "angles": ["桌面特写", "侧光近景"],
                "closeups": ["冰块", "杯身"]
              },
              "editingSuggestions": {
                "openingPace": "快切",
                "middlePace": "跟随倒咖啡节奏",
                "endingPace": "轻 CTA",
                "subtitleStyle": "短句大字",
                "bgm": "轻快 Lo-fi",
                "sfx": "冰块声",
                "transition": "推拉切"
              },
              "cta": {
                "comment": "你下午喝冰咖啡吗？",
                "save": "先收藏，拍的时候照着用",
                "conversion": "链接放在置顶评论"
              },
              "backupTitles": ["春日冰咖啡续命杯"],
              "backupHooks": ["这杯冷饮真的适合办公室"],
              "tags": ["#咖啡", "#办公室", "#TikTok"],
              "handoff": {
                "nextAgent": "storyboard_generation",
                "scriptRevision": "v1",
                "segmentIds": ["S01", "S02"],
                "videoRatio": "9:16",
                "readyForStoryboard": true,
                "readyForTts": true,
                "readyForSubtitle": true,
                "notes": "按 segment_id 拆解分镜。"
              }
            }
            '''
        else:
            text = '''
            {
              "schemaVersion": "script_document_v1",
              "title": "改写后春日咖啡脚本",
              "metadata": {"platform": "TikTok", "videoRatio": "9:16", "duration": "30秒"},
              "segments": [
                {
                  "segmentId": "S01",
                  "time": "0-3秒",
                  "goal": "钩子强化",
                  "voiceover": "别让下午的咖啡变成一杯水。",
                  "subtitle": "别让咖啡变成水",
                  "visualSuggestion": "旧杯和冰霸杯并排对比",
                  "retentionPoint": "反差",
                  "storyboardHint": "对比镜头"
                }
              ],
              "voiceoverFull": "别让下午的咖啡变成一杯水。",
              "subtitles": ["别让咖啡变成水"]
            }
            '''
        return FakeGenerationResult(
            text=text,
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
    assert empty_payload['isSaved'] is False
    assert empty_payload['latestRevision'] is None
    assert empty_payload['saveSource'] is None
    assert empty_payload['latestAiJob'] is None
    assert empty_payload['lastOperation'] is None

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
    assert saved_payload['isSaved'] is True
    assert saved_payload['latestRevision'] == 1
    assert saved_payload['saveSource'] == 'manual'
    assert saved_payload['latestAiJob'] is None
    assert saved_payload['lastOperation']['source'] == 'manual'
    assert saved_payload['lastOperation']['aiJobStatus'] is None


def test_script_generation_and_rewrite_record_ai_jobs(runtime_app) -> None:
    fake_service = FakeAITextGenerationService(runtime_app.state.ai_job_repository)
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
    assert generated_payload['isSaved'] is True
    assert generated_payload['latestRevision'] == 1
    assert generated_payload['saveSource'] == 'ai_generate'
    assert generated_payload['latestAiJob']['capabilityId'] == 'script_generation'
    assert generated_payload['lastOperation']['source'] == 'ai_generate'
    assert generated_payload['lastOperation']['aiJobStatus'] == 'succeeded'

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
    assert rewritten_payload['latestRevision'] == 2
    assert rewritten_payload['saveSource'] == 'ai_rewrite'
    assert rewritten_payload['latestAiJob']['capabilityId'] == 'script_rewrite'
    assert rewritten_payload['lastOperation']['source'] == 'ai_rewrite'
    assert rewritten_payload['lastOperation']['aiJobStatus'] == 'succeeded'
    assert fake_service.calls[0][0] == 'script_generation'
    assert fake_service.calls[1][0] == 'script_rewrite'


def test_script_generation_and_rewrite_store_json_document_as_canonical_source(runtime_app) -> None:
    runtime_app.state.ai_text_generation_service = JsonScriptAITextGenerationService(
        runtime_app.state.ai_job_repository
    )
    client = TestClient(runtime_app)

    project_response = client.post(
        '/api/dashboard/projects',
        json={'name': 'JSON Script Project', 'description': 'structured script'},
    )
    project_id = project_response.json()['data']['id']

    generate_response = client.post(
        f'/api/scripts/projects/{project_id}/generate',
        json={'topic': '春日咖啡冷饮'},
    )

    assert generate_response.status_code == 200
    generated = generate_response.json()['data']['currentVersion']
    assert generated['format'] == 'json_v1'
    assert generated['documentJson']['title'] == '春日咖啡冷饮短视频脚本'
    assert generated['documentJson']['segments'][0]['segmentId'] == 'S01'
    assert '下午三点别再喝温咖啡了。' in generated['documentJson']['voiceoverFull']
    assert 'TikTok短视频脚本' not in generated['content']

    rewrite_response = client.post(
        f'/api/scripts/projects/{project_id}/rewrite',
        json={'instructions': '强化痛点'},
    )

    assert rewrite_response.status_code == 200
    rewritten = rewrite_response.json()['data']['currentVersion']
    assert rewritten['format'] == 'json_v1'
    assert rewritten['documentJson']['title'] == '改写后春日咖啡脚本'
    assert rewritten['documentJson']['segments'][0]['voiceover'] == '别让下午的咖啡变成一杯水。'


def test_script_versions_title_variants_restore_and_segment_rewrite(runtime_app) -> None:
    fake_service = FakeAITextGenerationService(runtime_app.state.ai_job_repository)
    runtime_app.state.ai_text_generation_service = fake_service
    client = TestClient(runtime_app)

    project_response = client.post(
        '/api/dashboard/projects',
        json={'name': 'Script Versions Project', 'description': 'Script version tests'},
    )
    project_id = project_response.json()['data']['id']

    first_save = client.put(
        f'/api/scripts/projects/{project_id}/document',
        json={'content': 'Draft hook\nDraft body\nDraft CTA'},
    )
    assert first_save.status_code == 200

    second_save = client.put(
        f'/api/scripts/projects/{project_id}/document',
        json={'content': 'Fresh hook\nFresh body\nFresh CTA'},
    )
    assert second_save.status_code == 200

    versions_response = client.get(f'/api/scripts/projects/{project_id}/versions')
    assert versions_response.status_code == 200
    versions_payload = versions_response.json()['data']
    assert [item['revision'] for item in versions_payload] == [2, 1]

    title_response = client.post(
        f'/api/scripts/projects/{project_id}/title-variants',
        json={'topic': 'Launch', 'count': 3},
    )
    assert title_response.status_code == 200
    title_payload = title_response.json()['data']
    assert [item['title'] for item in title_payload] == [
        'Launch 标题 1',
        'Launch 标题 2',
        'Launch 标题 3',
    ]
    assert fake_service.calls[-1][0] == 'script_generation'
    assert fake_service.calls[-1][1]['count'] == '3'

    rewrite_response = client.post(
        f'/api/scripts/projects/{project_id}/segments/2/rewrite',
        json={'instructions': '把第二段改得更有号召力'},
    )

    assert rewrite_response.status_code == 200
    rewrite_payload = rewrite_response.json()['data']
    assert rewrite_payload['currentVersion']['revision'] == 3
    assert rewrite_payload['currentVersion']['content'] == 'Fresh hook\nRewrite body\nFresh CTA'
    assert rewrite_payload['latestRevision'] == 3
    assert rewrite_payload['saveSource'] == 'ai_segment_rewrite'
    assert rewrite_payload['lastOperation']['source'] == 'ai_segment_rewrite'
    assert rewrite_payload['lastOperation']['aiJobStatus'] == 'succeeded'

    restore_response = client.post(f'/api/scripts/projects/{project_id}/restore/1')
    assert restore_response.status_code == 200
    restore_payload = restore_response.json()['data']
    assert restore_payload['currentVersion']['revision'] == 4
    assert restore_payload['currentVersion']['content'] == 'Draft hook\nDraft body\nDraft CTA'
    assert restore_payload['latestRevision'] == 4
    assert restore_payload['saveSource'] == 'restore'
    assert restore_payload['lastOperation']['source'] == 'restore'
    assert restore_payload['lastOperation']['aiJobStatus'] is None

    final_versions = client.get(f'/api/scripts/projects/{project_id}/versions').json()['data']
    assert [item['revision'] for item in final_versions] == [4, 3, 2, 1]


def test_script_rewrite_requires_existing_saved_version(runtime_client: TestClient) -> None:
    project_response = runtime_client.post(
        '/api/dashboard/projects',
        json={'name': 'Rewrite Guard', 'description': 'rewrite requires saved version'},
    )
    project_id = project_response.json()['data']['id']

    rewrite_response = runtime_client.post(
        f'/api/scripts/projects/{project_id}/rewrite',
        json={'instructions': '改得更紧凑'},
    )

    assert rewrite_response.status_code == 400
    assert rewrite_response.json()['error'] == '请先保存或生成脚本版本，再执行改写。'
