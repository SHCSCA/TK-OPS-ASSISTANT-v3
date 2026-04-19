from __future__ import annotations

from fastapi.testclient import TestClient


def test_ai_capabilities_return_defaults_and_provider_status_without_plaintext_secret(
    runtime_client: TestClient,
) -> None:
    response = runtime_client.get('/api/settings/ai-capabilities')

    assert response.status_code == 200
    payload = response.json()
    assert payload['ok'] is True
    assert len(payload['data']['capabilities']) == 7
    capability_ids = {item['capabilityId'] for item in payload['data']['capabilities']}
    assert capability_ids == {
        'script_generation',
        'script_rewrite',
        'storyboard_generation',
        'tts_generation',
        'subtitle_alignment',
        'video_generation',
        'asset_analysis',
    }
    providers = {item['provider']: item for item in payload['data']['providers']}
    assert {'openai', 'openai_compatible', 'anthropic', 'gemini', 'deepseek', 'openrouter', 'ollama'} <= set(
        providers
    )
    assert providers['openai']['configured'] is False
    assert providers['openai']['maskedSecret'] == ''
    assert 'apiKey' not in providers['openai']


def test_provider_runtime_config_exposes_protocol_family_and_tts_flags(runtime_app) -> None:
    service = runtime_app.state.ai_capability_service

    openai_runtime = service.get_provider_runtime_config('openai')
    openai_compatible_runtime = service.get_provider_runtime_config('openai_compatible')
    anthropic_runtime = service.get_provider_runtime_config('anthropic')
    gemini_runtime = service.get_provider_runtime_config('gemini')
    cohere_runtime = service.get_provider_runtime_config('cohere')
    ollama_runtime = service.get_provider_runtime_config('ollama')

    assert openai_runtime.protocol_family == 'openai_responses'
    assert openai_runtime.supports_tts is True
    assert openai_runtime.requires_secret is True
    assert openai_compatible_runtime.protocol_family == 'openai_chat'
    assert openai_compatible_runtime.supports_tts is False
    assert openai_compatible_runtime.requires_secret is True
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
    assert updated['script_generation']['agentRole'] == 'Senior TikTok script strategist'
    assert updated['video_generation']['provider'] == 'openai_compatible'
    assert providers['openai']['configured'] is True
    assert providers['openai']['maskedSecret']


def test_ai_provider_catalog_model_catalog_and_refresh_are_runtime_backed(
    runtime_client: TestClient,
) -> None:
    catalog_response = runtime_client.get('/api/settings/ai-providers/catalog')

    assert catalog_response.status_code == 200
    catalog_payload = catalog_response.json()['data']
    providers = {item['provider']: item for item in catalog_payload}
    assert providers['openai']['kind'] == 'commercial'
    assert providers['openai_compatible']['requiresBaseUrl'] is True
    assert providers['ollama']['kind'] == 'local'
    assert providers['deepseek']['supportsModelDiscovery'] is False
    assert 'apiKey' not in providers['openai']

    models_response = runtime_client.get('/api/settings/ai-providers/ollama/models')

    assert models_response.status_code == 200
    models = models_response.json()['data']
    assert models
    assert all(item['provider'] == 'ollama' for item in models)
    assert any('text_generation' in item['capabilityTypes'] for item in models)

    refresh_response = runtime_client.post('/api/settings/ai-providers/ollama/models/refresh')

    assert refresh_response.status_code == 200
    refresh_payload = refresh_response.json()['data']
    assert refresh_payload == {
        'provider': 'ollama',
        'status': 'static_catalog',
        'message': '当前模型目录来自内置注册表，暂未执行远端刷新。',
    }


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
