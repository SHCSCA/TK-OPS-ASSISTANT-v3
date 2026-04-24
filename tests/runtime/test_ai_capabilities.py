from __future__ import annotations

from fastapi.testclient import TestClient


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
    assert providers['openai']['readiness'] == 'not_configured'
    assert providers['openai']['scope'] == 'runtime_local'
    assert 'apiKey' not in providers['openai']


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
        'video_generation',
        'asset_analysis',
    }


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


def test_generic_video_and_asset_providers_are_configurable_and_refreshable(
    runtime_client: TestClient,
) -> None:
    response = runtime_client.get('/api/settings/ai-providers/catalog')

    assert response.status_code == 200
    providers = {item['provider']: item for item in response.json()['data']}
    for provider_id in {'video_generation_provider', 'asset_analysis_provider'}:
        provider = providers[provider_id]
        assert provider['requiresBaseUrl'] is True
        assert provider['supportsModelDiscovery'] is True
        assert provider['modelSyncMode'] == 'remote'
        assert provider['status'] in {'missing_secret', 'misconfigured'}


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
    assert 'openai' in capabilities['asset_analysis']['providers']
    assert any(
        item['provider'] == 'openai'
        and item['modelId'] == 'gpt-5.4'
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
