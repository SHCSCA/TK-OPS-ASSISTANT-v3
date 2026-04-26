from __future__ import annotations

from fastapi.testclient import TestClient

from services.ai_default_prompts import DEFAULT_AGENT_PROMPT_CONFIG
from services.video_deconstruction_prompt import (
    VIDEO_DECONSTRUCTION_JSON_SCHEMA_TEXT,
    VIDEO_DECONSTRUCTION_OUTPUT_CONTRACT,
)


def test_ai_capabilities_return_defaults_and_provider_status_without_plaintext_secret(
    runtime_client: TestClient,
) -> None:
    response = runtime_client.get('/api/settings/ai-capabilities')

    assert response.status_code == 200
    payload = response.json()
    assert payload['ok'] is True
    assert payload['data']['scope'] == 'runtime_local'
    assert payload['data']['configVersion']
    assert set(payload['data']['diagnosticSummary']) == {
        'configuredProviderCount',
        'readyProviderCount',
        'degradedProviderCount',
        'lastHealthRefreshAt',
    }
    assert len(payload['data']['capabilities']) == 8
    capability_ids = {item['capabilityId'] for item in payload['data']['capabilities']}
    assert capability_ids == {
        'script_generation',
        'script_rewrite',
        'storyboard_generation',
        'tts_generation',
        'subtitle_alignment',
        'video_transcription',
        'video_generation',
        'asset_analysis',
    }
    providers = {item['provider']: item for item in payload['data']['providers']}
    assert {'openai', 'openai_compatible', 'anthropic', 'gemini', 'deepseek', 'openrouter', 'ollama'} <= set(
        providers
    )
    assert providers['openai']['configured'] is False
    assert providers['openai']['maskedSecret'] == ''
    assert providers['openai']['readiness'] == 'not_configured'
    assert providers['openai']['scope'] == 'runtime_local'
    assert 'apiKey' not in providers['openai']
    asset_analysis = next(
        item for item in payload['data']['capabilities']
        if item['capabilityId'] == 'asset_analysis'
    )
    assert asset_analysis['provider'] == 'volcengine'
    assert asset_analysis['model'] == 'doubao-seed-2.0-pro'


def test_ai_capabilities_use_agent_prompt_config_defaults(
    runtime_client: TestClient,
) -> None:
    response = runtime_client.get('/api/settings/ai-capabilities')

    assert response.status_code == 200
    payload = response.json()
    capabilities = {
        item['capabilityId']: item for item in payload['data']['capabilities']
    }

    for capability_id in capabilities:
        expected = DEFAULT_AGENT_PROMPT_CONFIG[capability_id]
        actual = capabilities[capability_id]
        assert actual['agentRole'] == expected['agent_role']
        assert actual['systemPrompt'] == expected['system_prompt']
        assert actual['userPromptTemplate'] == expected['user_prompt_template']

    assert 'quality_review' in DEFAULT_AGENT_PROMPT_CONFIG
    assert 'quality_review' not in capabilities
    assert '{{voice_id}}' in capabilities['tts_generation']['userPromptTemplate']
    assert '{{audio_url}}' in capabilities['subtitle_alignment']['userPromptTemplate']
    assert '{{media_file}}' in capabilities['video_transcription']['userPromptTemplate']
    video_prompt = (
        capabilities['video_transcription']['systemPrompt']
        + capabilities['video_transcription']['userPromptTemplate']
    )
    assert VIDEO_DECONSTRUCTION_OUTPUT_CONTRACT in video_prompt
    assert VIDEO_DECONSTRUCTION_JSON_SCHEMA_TEXT in video_prompt
    assert VIDEO_DECONSTRUCTION_OUTPUT_CONTRACT in capabilities['asset_analysis']['systemPrompt']
    assert VIDEO_DECONSTRUCTION_OUTPUT_CONTRACT in capabilities['asset_analysis']['userPromptTemplate']
    assert VIDEO_DECONSTRUCTION_JSON_SCHEMA_TEXT in capabilities['asset_analysis']['systemPrompt']
    assert VIDEO_DECONSTRUCTION_JSON_SCHEMA_TEXT in capabilities['asset_analysis']['userPromptTemplate']
    asset_prompt = capabilities['asset_analysis']['systemPrompt'] + capabilities['asset_analysis']['userPromptTemplate']
    assert '脚本文案' in asset_prompt
    assert '视频关键帧' in asset_prompt
    assert '内容结构' in asset_prompt
    assert '严格 JSON' in asset_prompt
    assert '不要把文件名、视频时长、分辨率当作主题、脚本、关键帧或内容结构' in asset_prompt
    assert '无法识别语音或字幕时，对应字段使用空字符串' in asset_prompt


def test_ai_capabilities_migrate_legacy_asset_analysis_default_prompt(
    runtime_client: TestClient,
) -> None:
    response = runtime_client.get('/api/settings/ai-capabilities')
    capabilities = response.json()['data']['capabilities']
    for item in capabilities:
        if item['capabilityId'] == 'asset_analysis':
            item['agentRole'] = '素材分析 Agent'
            item['systemPrompt'] = '# 素材分析 Agent\n\n你是 TK-OPS 的素材分析 Agent，负责分析用户导入的视频、图片、音频或文档素材。'
            item['userPromptTemplate'] = (
                '请分析以下素材内容，并输出可回流到脚本、分镜、字幕或视频生成的结构化信息。\n\n'
                '## 素材内容\n\n{{content}}\n\n输出要求：输出 Markdown 格式。'
            )

    update_response = runtime_client.put(
        '/api/settings/ai-capabilities',
        json={'capabilities': capabilities},
    )
    assert update_response.status_code == 200

    migrated_response = runtime_client.get('/api/settings/ai-capabilities')
    migrated = {
        item['capabilityId']: item for item in migrated_response.json()['data']['capabilities']
    }
    assert migrated['asset_analysis']['agentRole'] == '视频拆解 Agent'
    assert VIDEO_DECONSTRUCTION_OUTPUT_CONTRACT in migrated['asset_analysis']['systemPrompt']
    assert VIDEO_DECONSTRUCTION_JSON_SCHEMA_TEXT in migrated['asset_analysis']['userPromptTemplate']


def test_ai_capabilities_migrate_legacy_video_transcription_default_prompt(
    runtime_client: TestClient,
) -> None:
    response = runtime_client.get('/api/settings/ai-capabilities')
    capabilities = response.json()['data']['capabilities']
    for item in capabilities:
        if item['capabilityId'] == 'video_transcription':
            item['agentRole'] = '视频转录 Agent'
            item['systemPrompt'] = (
                '# 视频转录 Agent\n\n'
                '你是 TK-OPS 的视频转录 Agent，负责把本地视频或音频中的语音内容转写为纯文本。'
            )
            item['userPromptTemplate'] = '{{media_file}}'

    update_response = runtime_client.put(
        '/api/settings/ai-capabilities',
        json={'capabilities': capabilities},
    )
    assert update_response.status_code == 200

    migrated_response = runtime_client.get('/api/settings/ai-capabilities')
    migrated = {
        item['capabilityId']: item for item in migrated_response.json()['data']['capabilities']
    }
    assert migrated['video_transcription']['agentRole'] == '视频拆解 Agent'
    assert '{{media_file}}' in migrated['video_transcription']['userPromptTemplate']
    assert VIDEO_DECONSTRUCTION_OUTPUT_CONTRACT in migrated['video_transcription']['systemPrompt']
    assert VIDEO_DECONSTRUCTION_JSON_SCHEMA_TEXT in migrated['video_transcription']['userPromptTemplate']


def test_ai_capability_mutations_emit_broadcast_events(runtime_app) -> None:
    client = TestClient(runtime_app)
    captured: list[dict[str, object]] = []

    async def fake_broadcast(message: dict[str, object]) -> None:
        event = dict(message)
        event.setdefault('schema_version', 1)
        captured.append(event)

    from services import ai_capability_service as ai_capability_service_module

    original_broadcast = ai_capability_service_module.ws_manager.broadcast
    ai_capability_service_module.ws_manager.broadcast = fake_broadcast
    try:
        settings_response = client.get('/api/settings/ai-capabilities')
        assert settings_response.status_code == 200
        capabilities = settings_response.json()['data']['capabilities']
        capabilities[0]['model'] = 'gpt-5.4-runtime-test'

        update_response = client.put(
            '/api/settings/ai-capabilities',
            json={'capabilities': capabilities},
        )
        assert update_response.status_code == 200

        secret_response = client.put(
            '/api/settings/ai-capabilities/providers/openai/secret',
            json={'apiKey': 'sk-runtime-test-openai-123456'},
        )
        assert secret_response.status_code == 200

        model_response = client.put(
            '/api/ai-providers/openai/models/runtime-contract-writer',
            json={
                'displayName': 'Runtime Contract Writer',
                'capabilityKinds': ['text_generation'],
                'inputModalities': ['text'],
                'outputModalities': ['text'],
                'contextWindow': 32000,
                'defaultFor': ['script_generation'],
                'enabled': True,
            },
        )
        assert model_response.status_code == 200

        refresh_response = client.post('/api/ai-providers/health/refresh')
        assert refresh_response.status_code == 200
    finally:
        ai_capability_service_module.ws_manager.broadcast = original_broadcast

    assert len(captured) == 4
    assert [event['type'] for event in captured] == [
        'ai-capability.changed',
        'ai-capability.changed',
        'ai-capability.changed',
        'ai-capability.changed',
    ]
    assert [event['reason'] for event in captured] == [
        'capability_config_updated',
        'provider_secret_updated',
        'provider_model_upserted',
        'provider_health_refreshed',
    ]
    assert captured[0]['providerIds']
    assert captured[1]['providerIds'] == ['openai']
    assert 'script_generation' in captured[2]['capabilityIds']
    assert set(captured[3]['capabilityIds']) == {
        'script_generation',
        'script_rewrite',
        'storyboard_generation',
        'tts_generation',
        'subtitle_alignment',
        'video_transcription',
        'video_generation',
        'asset_analysis',
    }


def test_provider_runtime_config_exposes_protocol_family_and_media_flags(runtime_app) -> None:
    service = runtime_app.state.ai_capability_service

    openai_runtime = service.get_provider_runtime_config('openai')
    openai_compatible_runtime = service.get_provider_runtime_config('openai_compatible')
    volcengine_asr_runtime = service.get_provider_runtime_config('volcengine_asr')
    anthropic_runtime = service.get_provider_runtime_config('anthropic')
    gemini_runtime = service.get_provider_runtime_config('gemini')
    cohere_runtime = service.get_provider_runtime_config('cohere')
    ollama_runtime = service.get_provider_runtime_config('ollama')

    assert openai_runtime.protocol_family == 'openai_responses'
    assert openai_runtime.supports_tts is True
    assert openai_runtime.supports_speech_to_text is True
    assert openai_runtime.requires_secret is True
    assert openai_compatible_runtime.protocol_family == 'openai_chat'
    assert openai_compatible_runtime.supports_tts is False
    assert openai_compatible_runtime.supports_speech_to_text is True
    assert openai_compatible_runtime.requires_secret is True
    assert volcengine_asr_runtime.protocol_family == 'domestic_asr'
    assert volcengine_asr_runtime.supports_speech_to_text is True
    assert anthropic_runtime.protocol_family == 'anthropic_messages'
    assert gemini_runtime.protocol_family == 'gemini_generate'
    assert cohere_runtime.protocol_family == 'cohere_chat'
    assert ollama_runtime.protocol_family == 'openai_chat'
    assert ollama_runtime.requires_secret is False


def test_ai_capability_update_and_secret_status_persist(runtime_app) -> None:
    client = TestClient(runtime_app)

    update_response = client.put(
        '/api/settings/ai-capabilities',
        json={
            'capabilities': [
                {
                    'capabilityId': 'script_generation',
                    'enabled': True,
                    'provider': 'openai',
                    'model': 'gpt-5',
                    'agentRole': 'Senior TikTok script strategist',
                    'systemPrompt': 'Write high-retention short video scripts.',
                    'userPromptTemplate': 'Topic: {{topic}}',
                },
                {
                    'capabilityId': 'script_rewrite',
                    'enabled': True,
                    'provider': 'openai',
                    'model': 'gpt-5-mini',
                    'agentRole': 'Script revision editor',
                    'systemPrompt': 'Improve pacing and hooks.',
                    'userPromptTemplate': 'Rewrite: {{script}}',
                },
                {
                    'capabilityId': 'storyboard_generation',
                    'enabled': True,
                    'provider': 'openai',
                    'model': 'gpt-5-mini',
                    'agentRole': 'Storyboard planner',
                    'systemPrompt': 'Turn scripts into shot plans.',
                    'userPromptTemplate': 'Storyboard: {{script}}',
                },
                {
                    'capabilityId': 'tts_generation',
                    'enabled': False,
                    'provider': 'openai',
                    'model': 'gpt-5-mini',
                    'agentRole': 'Voice designer',
                    'systemPrompt': 'Prepare TTS settings.',
                    'userPromptTemplate': 'Voice: {{script}}',
                },
                {
                    'capabilityId': 'subtitle_alignment',
                    'enabled': False,
                    'provider': 'openai',
                    'model': 'gpt-5-mini',
                    'agentRole': 'Subtitle aligner',
                    'systemPrompt': 'Align subtitles.',
                    'userPromptTemplate': 'Subtitle: {{script}}',
                },
                {
                    'capabilityId': 'video_transcription',
                    'enabled': False,
                    'provider': 'openai',
                    'model': 'whisper-1',
                    'agentRole': 'Video transcriber',
                    'systemPrompt': 'Transcribe video speech.',
                    'userPromptTemplate': '{{media_file}}',
                },
                {
                    'capabilityId': 'video_generation',
                    'enabled': False,
                    'provider': 'openai_compatible',
                    'model': 'custom-video',
                    'agentRole': 'Video generator',
                    'systemPrompt': 'Prepare shots.',
                    'userPromptTemplate': 'Video: {{storyboard}}',
                },
                {
                    'capabilityId': 'asset_analysis',
                    'enabled': False,
                    'provider': 'gemini',
                    'model': 'gemini-2.5-pro',
                    'agentRole': 'Asset analyst',
                    'systemPrompt': 'Analyze assets.',
                    'userPromptTemplate': 'Assets: {{assets}}',
                },
            ]
        },
    )

    assert update_response.status_code == 200
    assert update_response.json()['data']['capabilities'][0]['model'] == 'gpt-5'

    secret_response = client.put(
        '/api/settings/ai-capabilities/providers/openai/secret',
        json={'apiKey': 'sk-test-openai-1234567890'},
    )

    assert secret_response.status_code == 200
    secret_payload = secret_response.json()['data']
    assert secret_payload['provider'] == 'openai'
    assert secret_payload['configured'] is True
    assert secret_payload['maskedSecret'].startswith('sk-t')
    assert '1234567890' not in secret_payload['maskedSecret']

    from app.factory import create_app

    reloaded_client = TestClient(create_app())
    capabilities_response = reloaded_client.get('/api/settings/ai-capabilities')

    assert capabilities_response.status_code == 200
    capabilities_payload = capabilities_response.json()['data']
    updated = {
        item['capabilityId']: item for item in capabilities_payload['capabilities']
    }
    providers = {item['provider']: item for item in capabilities_payload['providers']}
    assert updated['script_generation']['provider'] == 'openai'
    assert updated['script_generation']['model'] == 'gpt-5'
    assert updated['script_generation']['agentRole'] == DEFAULT_AGENT_PROMPT_CONFIG['script_generation']['agent_role']
    assert updated['script_generation']['promptPreview']['editable'] is False
    assert (
        updated['script_generation']['promptPreview']['systemPrompt']
        == DEFAULT_AGENT_PROMPT_CONFIG['script_generation']['system_prompt']
    )
    assert updated['video_generation']['provider'] == 'openai_compatible'
    assert providers['openai']['configured'] is True
    assert providers['openai']['maskedSecret']


def test_ai_capability_update_does_not_persist_user_prompt_edits(runtime_client: TestClient) -> None:
    capabilities = runtime_client.get('/api/settings/ai-capabilities').json()['data']['capabilities']
    for item in capabilities:
        if item['capabilityId'] == 'script_generation':
            item['provider'] = 'openai'
            item['model'] = 'gpt-5'
            item['agentRole'] = '用户自定义角色'
            item['systemPrompt'] = '用户自定义系统提示词'
            item['userPromptTemplate'] = '用户自定义模板 {{topic}}'

    update_response = runtime_client.put(
        '/api/settings/ai-capabilities',
        json={'capabilities': capabilities},
    )

    assert update_response.status_code == 200
    updated = {
        item['capabilityId']: item
        for item in update_response.json()['data']['capabilities']
    }
    assert updated['script_generation']['provider'] == 'openai'
    assert updated['script_generation']['model'] == 'gpt-5'
    assert updated['script_generation']['agentRole'] == DEFAULT_AGENT_PROMPT_CONFIG['script_generation']['agent_role']
    assert updated['script_generation']['systemPrompt'] == DEFAULT_AGENT_PROMPT_CONFIG['script_generation']['system_prompt']
    assert (
        updated['script_generation']['userPromptTemplate']
        == DEFAULT_AGENT_PROMPT_CONFIG['script_generation']['user_prompt_template']
    )


def test_ai_provider_catalog_model_catalog_and_refresh_are_runtime_backed(
    runtime_app,
    monkeypatch,
) -> None:
    client = TestClient(runtime_app)
    catalog_response = client.get('/api/settings/ai-providers/catalog')

    assert catalog_response.status_code == 200
    catalog_payload = catalog_response.json()['data']
    providers = {item['provider']: item for item in catalog_payload}
    assert providers['openai']['kind'] == 'commercial'
    assert providers['openai_compatible']['requiresBaseUrl'] is True
    assert providers['ollama']['kind'] == 'local'
    assert providers['deepseek']['region'] == 'domestic'
    assert providers['deepseek']['supportsModelDiscovery'] is True
    assert providers['volcengine']['category'] == 'model_hub'
    assert providers['custom_openai_compatible']['region'] == 'custom'
    assert 'apiKey' not in providers['openai']

    models_response = client.get('/api/settings/ai-providers/ollama/models')

    assert models_response.status_code == 200
    models = models_response.json()['data']
    assert models
    assert all(item['provider'] == 'ollama' for item in models)
    assert any('text_generation' in item['capabilityTypes'] for item in models)

    def fake_request_json_get(url: str, *, headers: dict[str, str] | None = None) -> dict[str, object]:
        assert url == 'http://127.0.0.1:11434/api/tags'
        return {
            'models': [
                {
                    'name': 'qwen2.5-vl:7b',
                    'model': 'qwen2.5-vl:7b',
                    'details': {
                        'family': 'qwen2.5-vl',
                        'families': ['qwen2.5-vl'],
                    },
                }
            ]
        }

    monkeypatch.setattr('services.ai_capability_service._request_json_get', fake_request_json_get)
    refresh_response = client.post('/api/settings/ai-providers/ollama/models/refresh')

    assert refresh_response.status_code == 200
    refresh_payload = refresh_response.json()['data']
    assert refresh_payload == {
        'provider': 'ollama',
        'status': 'refreshed',
        'message': '已从远端刷新 1 个模型。',
    }

    refreshed_models = client.get('/api/settings/ai-providers/ollama/models').json()['data']
    refreshed = next(item for item in refreshed_models if item['modelId'] == 'qwen2.5-vl:7b')
    assert refreshed['displayName'] == 'qwen2.5-vl:7b'
    assert refreshed['capabilityTypes'] == ['text_generation', 'vision']
    assert refreshed['inputModalities'] == ['text', 'image']


def test_openai_compatible_provider_model_refresh_reads_remote_model_catalog(
    runtime_app,
    monkeypatch,
) -> None:
    client = TestClient(runtime_app)
    client.put(
        '/api/settings/ai-capabilities/providers/custom_openai_compatible/secret',
        json={
            'apiKey': 'sk-custom-compatible',
            'baseUrl': 'https://custom.example.test/v1',
        },
    )

    captured: dict[str, object] = {}

    def fake_request_json_get(url: str, *, headers: dict[str, str] | None = None) -> dict[str, object]:
        captured['url'] = url
        captured['headers'] = headers
        return {
            'data': [
                {
                    'id': 'custom-text-vision',
                    'name': 'Custom Text Vision',
                    'capabilities': ['text_generation', 'vision'],
                    'input_modalities': ['text', 'image'],
                    'output_modalities': ['text'],
                    'context_length': 128000,
                }
            ]
        }

    monkeypatch.setattr('services.ai_capability_service._request_json_get', fake_request_json_get)
    refresh_response = client.post('/api/settings/ai-providers/custom_openai_compatible/models/refresh')

    assert refresh_response.status_code == 200
    assert refresh_response.json()['data'] == {
        'provider': 'custom_openai_compatible',
        'status': 'refreshed',
        'message': '已从远端刷新 1 个模型。',
    }
    assert captured['url'] == 'https://custom.example.test/v1/models'
    assert captured['headers']['authorization'] == 'Bearer sk-custom-compatible'

    models_response = client.get('/api/settings/ai-providers/custom_openai_compatible/models')
    assert models_response.status_code == 200
    models = {item['modelId']: item for item in models_response.json()['data']}
    assert models['custom-text-vision']['displayName'] == 'Custom Text Vision'
    assert models['custom-text-vision']['capabilityTypes'] == ['text_generation', 'vision']
    assert models['custom-text-vision']['inputModalities'] == ['text', 'image']
    assert models['custom-text-vision']['outputModalities'] == ['text']


def test_openai_compatible_refresh_infers_doubao_seedance_as_video_model(
    runtime_app,
    monkeypatch,
) -> None:
    client = TestClient(runtime_app)
    client.put(
        '/api/settings/ai-capabilities/providers/volcengine/secret',
        json={'apiKey': 'sk-test-volcengine'},
    )

    def fake_request_json_get(url: str, *, headers: dict[str, str] | None = None) -> dict[str, object]:
        assert url == 'https://ark.cn-beijing.volces.com/api/v3/models'
        return {
            'data': [
                {
                    'id': 'doubao-seedance-1-5-pro-251215',
                    'name': 'Doubao-Seedance-1.5-pro 251215',
                }
            ]
        }

    monkeypatch.setattr('services.ai_capability_service._request_json_get', fake_request_json_get)
    refresh_response = client.post('/api/settings/ai-providers/volcengine/models/refresh')

    assert refresh_response.status_code == 200
    models_response = client.get('/api/settings/ai-providers/volcengine/models')
    models = {item['modelId']: item for item in models_response.json()['data']}
    seedance = models['doubao-seedance-1-5-pro-251215']
    assert seedance['capabilityTypes'] == ['video_generation']
    assert seedance['inputModalities'] == ['text', 'image']
    assert seedance['outputModalities'] == ['video']
    assert 'text_generation' not in seedance['capabilityTypes']


def test_volcengine_refresh_infers_doubao_seed_vision_models_as_asset_analysis(
    runtime_app,
    monkeypatch,
) -> None:
    client = TestClient(runtime_app)
    client.put(
        '/api/settings/ai-capabilities/providers/volcengine/secret',
        json={'apiKey': 'sk-test-volcengine'},
    )

    def fake_request_json_get(url: str, *, headers: dict[str, str] | None = None) -> dict[str, object]:
        assert url == 'https://ark.cn-beijing.volces.com/api/v3/models'
        return {
            'data': [
                {
                    'id': 'doubao-seed-2-0-pro-260302',
                    'name': 'Doubao-Seed-2.0-pro',
                },
                {
                    'id': 'doubao-seed-2-0-lite-260326',
                    'name': 'Doubao-Seed-2.0-lite',
                },
            ]
        }

    monkeypatch.setattr('services.ai_capability_service._request_json_get', fake_request_json_get)
    refresh_response = client.post('/api/settings/ai-providers/volcengine/models/refresh')

    assert refresh_response.status_code == 200
    matrix_response = client.get('/api/settings/ai-capabilities/support-matrix')
    capabilities = {
        item['capabilityId']: item
        for item in matrix_response.json()['data']['capabilities']
    }
    asset_model_ids = {
        item['modelId']
        for item in capabilities['asset_analysis']['models']
        if item['provider'] == 'volcengine'
    }
    transcription_model_ids = {
        item['modelId']
        for item in capabilities['video_transcription']['models']
        if item['provider'] == 'volcengine'
    }

    assert 'doubao-seed-2-0-pro-260302' in asset_model_ids
    assert 'doubao-seed-2-0-lite-260326' in asset_model_ids
    assert 'doubao-seed-2-0-pro-260302' in transcription_model_ids
    assert 'doubao-seed-2-0-lite-260326' in transcription_model_ids


def test_volcengine_legacy_alias_is_hidden_and_resolved_to_latest_remote_model(
    runtime_app,
    monkeypatch,
) -> None:
    client = TestClient(runtime_app)
    client.put(
        '/api/settings/ai-capabilities/providers/volcengine/secret',
        json={'apiKey': 'sk-test-volcengine'},
    )

    def fake_request_json_get(url: str, *, headers: dict[str, str] | None = None) -> dict[str, object]:
        assert url == 'https://ark.cn-beijing.volces.com/api/v3/models'
        return {
            'data': [
                {
                    'id': 'doubao-seed-1-6-250615',
                    'name': 'doubao-seed-1-6',
                    'capabilities': ['text_generation'],
                    'input_modalities': ['text'],
                    'output_modalities': ['text'],
                },
                {
                    'id': 'doubao-seed-1-6-251015',
                    'name': 'doubao-seed-1-6',
                    'capabilities': ['text_generation'],
                    'input_modalities': ['text'],
                    'output_modalities': ['text'],
                },
                {
                    'id': 'doubao-seed-1-6-vision-250815',
                    'name': 'doubao-seed-1-6-vision',
                    'capabilities': ['vision'],
                    'input_modalities': ['text', 'image'],
                    'output_modalities': ['text'],
                },
            ]
        }

    monkeypatch.setattr('services.ai_capability_service._request_json_get', fake_request_json_get)
    refresh_response = client.post('/api/settings/ai-providers/volcengine/models/refresh')
    assert refresh_response.status_code == 200

    models_response = client.get('/api/settings/ai-providers/volcengine/models')
    assert models_response.status_code == 200
    model_ids = {item['modelId'] for item in models_response.json()['data']}
    assert 'doubao-seed-1.6' not in model_ids
    assert 'doubao-seed-1-6-251015' in model_ids

    captured: dict[str, object] = {}

    def fake_probe(runtime, model: str):
        captured['provider'] = runtime.provider
        captured['model'] = model
        return {
            'status': 'ready',
            'message': f'{runtime.provider}:{model}',
            'latency_ms': 18,
        }

    monkeypatch.setattr(
        runtime_app.state.ai_capability_service,
        '_probe_provider_connectivity',
        fake_probe,
    )
    health_response = client.post(
        '/api/settings/ai-capabilities/providers/volcengine/health-check',
        json={'model': 'doubao-seed-1.6'},
    )

    assert health_response.status_code == 200
    payload = health_response.json()['data']
    assert captured == {
        'provider': 'volcengine',
        'model': 'doubao-seed-1-6-251015',
    }
    assert payload['model'] == 'doubao-seed-1-6-251015'


def test_generic_media_providers_are_configurable_and_refreshable(
    runtime_client: TestClient,
) -> None:
    response = runtime_client.get('/api/settings/ai-providers/catalog')

    assert response.status_code == 200
    providers = {item['provider']: item for item in response.json()['data']}
    for provider_id in {'video_generation_provider', 'asset_analysis_provider', 'custom_transcription_provider'}:
        provider = providers[provider_id]
        assert provider['requiresBaseUrl'] is True
        assert provider['supportsModelDiscovery'] is True
        assert provider['modelSyncMode'] == 'remote'
        assert provider['status'] in {'missing_secret', 'misconfigured'}

    for provider_id in {'volcengine_asr', 'aliyun_asr', 'tencent_asr', 'baidu_asr', 'xunfei_asr'}:
        provider = providers[provider_id]
        assert provider['requiresBaseUrl'] is True
        assert provider['supportsModelDiscovery'] is False
        assert provider['modelSyncMode'] == 'manual'
        assert provider['category'] == 'speech_to_text'


def test_openrouter_model_refresh_requires_secret_and_returns_structured_error(runtime_app) -> None:
    client = TestClient(runtime_app)

    response = client.post('/api/settings/ai-providers/openrouter/models/refresh')

    assert response.status_code == 400
    payload = response.json()
    assert payload['ok'] is False
    assert payload['error_code'] == 'provider.model.refresh_missing_secret'


def test_ai_provider_health_check_uses_selected_model_and_real_probe(
    runtime_app,
    monkeypatch,
) -> None:
    client = TestClient(runtime_app)

    client.put(
        '/api/settings/ai-capabilities/providers/openai/secret',
        json={'apiKey': 'sk-test-openai-1234567890'},
    )

    captured: dict[str, object] = {}

    def fake_probe(runtime, model: str):
        captured['provider'] = runtime.provider
        captured['base_url'] = runtime.base_url
        captured['model'] = model
        return {
            'status': 'ready',
            'message': 'OpenAI / gpt-5.4 真实连通性测试通过。',
            'latency_ms': 321,
        }

    monkeypatch.setattr(
        runtime_app.state.ai_capability_service,
        '_probe_provider_connectivity',
        fake_probe,
    )

    response = client.post(
        '/api/settings/ai-capabilities/providers/openai/health-check',
        json={'model': 'gpt-5.4'},
    )

    assert response.status_code == 200
    payload = response.json()['data']
    assert captured == {
        'provider': 'openai',
        'base_url': 'https://api.openai.com/v1/responses',
        'model': 'gpt-5.4',
    }
    assert payload['provider'] == 'openai'
    assert payload['status'] == 'ready'
    assert payload['message'] == 'OpenAI / gpt-5.4 真实连通性测试通过。'
    assert payload['model'] == 'gpt-5.4'
    assert payload['checkedAt']
    assert payload['latencyMs'] == 321


def test_service_layer_400_errors_keep_structured_error_codes_in_envelope(
    runtime_app,
) -> None:
    client = TestClient(runtime_app)

    def _load_capabilities() -> list[dict[str, object]]:
        response = client.get('/api/settings/ai-capabilities')
        assert response.status_code == 200
        return list(response.json()['data']['capabilities'])

    def _save_capabilities(items: list[dict[str, object]]) -> None:
        response = client.put('/api/settings/ai-capabilities', json={'capabilities': items})
        assert response.status_code == 200

    def _create_project() -> str:
        response = client.post(
            '/api/dashboard/projects',
            json={'name': 'AI 错误码项目', 'description': 'error codes'},
        )
        assert response.status_code == 200
        return response.json()['data']['id']

    def _generate(project_id: str):
        return client.post(f'/api/scripts/projects/{project_id}/generate', json={'topic': 'TK-OPS'})

    capabilities = _load_capabilities()
    for item in capabilities:
        if item['capabilityId'] == 'script_generation':
            item['enabled'] = False
    _save_capabilities(capabilities)
    response = _generate(_create_project())
    assert response.status_code == 400
    payload = response.json()
    assert payload['ok'] is False
    assert payload['error_code'] == 'ai_capability_disabled'

    capabilities = _load_capabilities()
    for item in capabilities:
        if item['capabilityId'] == 'script_generation':
            item['enabled'] = True
            item['provider'] = 'openai'
            item['model'] = 'gpt-5'
    _save_capabilities(capabilities)
    response = _generate(_create_project())
    assert response.status_code == 400
    payload = response.json()
    assert payload['error_code'] == 'ai_provider_not_configured'

    client.put(
        '/api/settings/ai-capabilities/providers/openai_compatible/secret',
        json={'apiKey': 'sk-test-openai-compatible'},
    )
    capabilities = _load_capabilities()
    for item in capabilities:
        if item['capabilityId'] == 'script_generation':
            item['enabled'] = True
            item['provider'] = 'openai_compatible'
            item['model'] = 'custom-compatible-model'
    _save_capabilities(capabilities)
    response = _generate(_create_project())
    assert response.status_code == 400
    payload = response.json()
    assert payload['error_code'] == 'ai_provider_base_url_missing'

    capabilities = _load_capabilities()
    for item in capabilities:
        if item['capabilityId'] == 'script_generation':
            item['enabled'] = True
            item['provider'] = 'video_generation_provider'
            item['model'] = 'video-default'
    _save_capabilities(capabilities)
    response = _generate(_create_project())
    assert response.status_code == 400
    payload = response.json()
    assert payload['error_code'] == 'ai_provider_unsupported'


def test_ai_capability_support_matrix_limits_models_by_capability(
    runtime_client: TestClient,
) -> None:
    response = runtime_client.get('/api/settings/ai-capabilities/support-matrix')

    assert response.status_code == 200
    matrix = response.json()['data']
    capabilities = {item['capabilityId']: item for item in matrix['capabilities']}

    assert set(capabilities) == {
        'script_generation',
        'script_rewrite',
        'storyboard_generation',
        'tts_generation',
        'subtitle_alignment',
        'video_transcription',
        'video_generation',
        'asset_analysis',
    }
    assert 'openai' in capabilities['script_generation']['providers']
    assert all(
        'tts' in item['capabilityTypes'] or item['provider'].endswith('_speech')
        for item in capabilities['tts_generation']['models']
    )
    assert any(
        item['provider'] == 'video_generation_provider'
        for item in capabilities['video_generation']['models']
    )
    assert 'openai' in capabilities['subtitle_alignment']['providers']
    assert any(
        item['provider'] == 'openai'
        and item['modelId'] == 'gpt-5-mini'
        for item in capabilities['subtitle_alignment']['models']
    )
    assert 'openai' in capabilities['video_transcription']['providers']
    assert any(
        item['provider'] == 'openai'
        and item['modelId'] == 'whisper-1'
        for item in capabilities['video_transcription']['models']
    )
    assert 'custom_transcription_provider' in capabilities['video_transcription']['providers']
    assert {
        'volcengine_asr',
        'aliyun_asr',
        'tencent_asr',
        'baidu_asr',
        'xunfei_asr',
    } <= set(capabilities['video_transcription']['providers'])
    assert 'gemini' in capabilities['video_transcription']['providers']
    assert 'asset_analysis_provider' in capabilities['video_transcription']['providers']
    assert 'video_generation_provider' not in capabilities['video_transcription']['providers']
    assert any(
        item['provider'] == 'volcengine'
        and item['modelId'] == 'doubao-seed-2.0-pro'
        for item in capabilities['video_transcription']['models']
    )
    assert 'openai' in capabilities['asset_analysis']['providers']
    assert 'volcengine' in capabilities['asset_analysis']['providers']
    assert any(
        item['provider'] == 'openai'
        and item['modelId'] == 'gpt-5.4'
        for item in capabilities['asset_analysis']['models']
    )
    assert any(
        item['provider'] == 'volcengine'
        and item['modelId'] == 'doubao-seed-2.0-pro'
        for item in capabilities['asset_analysis']['models']
    )


def test_no_access_model_is_hidden_from_provider_catalog_and_support_matrix(
    runtime_app,
    monkeypatch,
) -> None:
    client = TestClient(runtime_app)
    client.put(
        '/api/settings/ai-capabilities/providers/volcengine/secret',
        json={'apiKey': 'sk-test-volcengine'},
    )

    def fake_probe(runtime, model: str):
        assert runtime.provider == 'volcengine'
        assert model == 'doubao-seed-1.6'
        return {
            'status': 'misconfigured',
            'message': (
                '远端返回 HTTP 404：The model or endpoint doubao-seed-1.6 '
                'does not exist or you do not have access to it.'
            ),
            'latency_ms': 32,
        }

    monkeypatch.setattr(
        runtime_app.state.ai_capability_service,
        '_probe_provider_connectivity',
        fake_probe,
    )

    health_response = client.post(
        '/api/settings/ai-capabilities/providers/volcengine/health-check',
        json={'model': 'doubao-seed-1.6'},
    )

    assert health_response.status_code == 200
    health = health_response.json()['data']
    assert health['status'] == 'misconfigured'
    assert '已从可选模型中屏蔽' in health['message']

    models_response = client.get('/api/settings/ai-providers/volcengine/models')
    assert models_response.status_code == 200
    model_ids = {item['modelId'] for item in models_response.json()['data']}
    assert 'doubao-seed-1.6' not in model_ids

    matrix_response = client.get('/api/settings/ai-capabilities/support-matrix')
    capabilities = {item['capabilityId']: item for item in matrix_response.json()['data']['capabilities']}
    assert all(
        not (item['provider'] == 'volcengine' and item['modelId'] == 'doubao-seed-1.6')
        for item in capabilities['script_generation']['models']
    )

def test_ai_provider_health_refresh_persists_aggregate_snapshots(
    runtime_app,
    monkeypatch,
) -> None:
    client = TestClient(runtime_app)
    client.put(
        '/api/settings/ai-capabilities/providers/openai/secret',
        json={'apiKey': 'sk-test-openai-health'},
    )

    def fake_probe(runtime, model: str):
        return {
            'status': 'ready' if runtime.provider in {'openai', 'ollama'} else 'offline',
            'message': f'{runtime.provider}:{model}',
            'latency_ms': 123,
        }

    monkeypatch.setattr(
        runtime_app.state.ai_capability_service,
        '_probe_provider_connectivity',
        fake_probe,
    )

    refresh_response = client.post('/api/ai-providers/health/refresh')
    assert refresh_response.status_code == 200
    refresh_payload = refresh_response.json()['data']
    assert refresh_payload['refreshedAt']
    providers = {item['provider']: item for item in refresh_payload['providers']}
    assert providers['openai']['readiness'] == 'ready'
    assert providers['openai']['latencyMs'] == 123
    assert providers['openai']['errorCode'] is None
    assert providers['openai']['lastCheckedAt']

    from app.factory import create_app

    reloaded_client = TestClient(create_app())
    health_response = reloaded_client.get('/api/ai-providers/health')
    assert health_response.status_code == 200
    persisted = {item['provider']: item for item in health_response.json()['data']['providers']}
    assert persisted['openai']['readiness'] == 'ready'
    assert persisted['openai']['errorMessage'] is None


def test_ai_provider_model_upsert_persists_and_support_matrix_reads_capability_kinds(
    runtime_client: TestClient,
) -> None:
    invalid_response = runtime_client.put(
        '/api/ai-providers/openai/models/runtime-writer',
        json={
            'displayName': 'Runtime Writer',
            'capabilityKinds': [],
            'inputModalities': ['text'],
            'outputModalities': ['text'],
            'contextWindow': 64000,
            'defaultFor': ['script_generation'],
            'enabled': True,
        },
    )
    assert invalid_response.status_code == 400
    assert invalid_response.json()['error_code'] == 'provider.model.capability_required'

    create_response = runtime_client.put(
        '/api/ai-providers/openai/models/runtime-writer',
        json={
            'displayName': 'Runtime Writer',
            'capabilityKinds': ['text_generation'],
            'inputModalities': ['text'],
            'outputModalities': ['text'],
            'contextWindow': 64000,
            'defaultFor': ['script_generation'],
            'enabled': True,
        },
    )
    assert create_response.status_code == 200
    assert create_response.json()['data']['wasUpsert'] is False

    update_response = runtime_client.put(
        '/api/ai-providers/openai/models/runtime-writer',
        json={
            'displayName': 'Runtime Writer v2',
            'capabilityKinds': ['text_generation'],
            'inputModalities': ['text'],
            'outputModalities': ['text'],
            'contextWindow': 128000,
            'defaultFor': ['script_generation'],
            'enabled': True,
        },
    )
    assert update_response.status_code == 200
    assert update_response.json()['data']['wasUpsert'] is True

    models_response = runtime_client.get('/api/settings/ai-providers/openai/models')
    assert models_response.status_code == 200
    models = {item['modelId']: item for item in models_response.json()['data']}
    assert models['runtime-writer']['displayName'] == 'Runtime Writer v2'
    assert models['runtime-writer']['contextWindow'] == 128000

    matrix_response = runtime_client.get('/api/settings/ai-capabilities/support-matrix')
    assert matrix_response.status_code == 200
    capabilities = {
        item['capabilityId']: item
        for item in matrix_response.json()['data']['capabilities']
    }
    assert any(
        item['provider'] == 'openai' and item['modelId'] == 'runtime-writer'
        for item in capabilities['script_generation']['models']
    )
