from __future__ import annotations

from fastapi.testclient import TestClient


def test_ai_capability_mutations_broadcast_changed_events(
    runtime_client: TestClient,
    monkeypatch,
) -> None:
    captured: list[dict[str, object]] = []

    async def fake_broadcast(message: dict[str, object]) -> None:
        event = dict(message)
        event.setdefault("schema_version", 1)
        captured.append(event)

    monkeypatch.setattr("services.ai_capability_service.ws_manager.broadcast", fake_broadcast)

    settings_response = runtime_client.get("/api/settings/ai-capabilities")
    assert settings_response.status_code == 200
    capabilities = settings_response.json()["data"]["capabilities"]
    capabilities[0]["model"] = "gpt-5.4"

    update_response = runtime_client.put(
        "/api/settings/ai-capabilities",
        json={"capabilities": capabilities},
    )
    assert update_response.status_code == 200

    secret_response = runtime_client.put(
        "/api/settings/ai-capabilities/providers/openai/secret",
        json={"apiKey": "sk-contract-openai-123456"},
    )
    assert secret_response.status_code == 200

    model_response = runtime_client.put(
        "/api/ai-providers/openai/models/contract-writer",
        json={
            "displayName": "Contract Writer",
            "capabilityKinds": ["text_generation"],
            "inputModalities": ["text"],
            "outputModalities": ["text"],
            "contextWindow": 32000,
            "defaultFor": ["script_generation"],
            "enabled": True,
        },
    )
    assert model_response.status_code == 200

    refresh_response = runtime_client.post("/api/ai-providers/health/refresh")
    assert refresh_response.status_code == 200

    assert len(captured) == 4

    update_event, secret_event, model_event, refresh_event = captured
    assert update_event["schema_version"] == 1
    assert update_event["type"] == "ai-capability.changed"
    assert update_event["reason"] == "capability_config_updated"
    assert update_event["scope"] == "runtime_local"
    assert update_event["providerIds"]
    assert capabilities[0]["capabilityId"] in update_event["capabilityIds"]

    assert secret_event["reason"] == "provider_secret_updated"
    assert secret_event["providerIds"] == ["openai"]
    assert secret_event["capabilityIds"]

    assert model_event["reason"] == "provider_model_upserted"
    assert model_event["providerIds"] == ["openai"]
    assert "script_generation" in model_event["capabilityIds"]

    assert refresh_event["reason"] == "provider_health_refreshed"
    assert "openai" in refresh_event["providerIds"]
    assert set(refresh_event["capabilityIds"]) == {
        "script_generation",
        "script_rewrite",
        "storyboard_generation",
        "tts_generation",
        "subtitle_alignment",
        "video_transcription",
        "video_generation",
        "asset_analysis",
    }


def test_ai_capability_settings_contract_uses_settings_prefix_and_expected_shape(
    runtime_client: TestClient,
) -> None:
    response = runtime_client.get('/api/settings/ai-capabilities')

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {'ok', 'data'}
    assert payload['ok'] is True
    assert set(payload['data']) == {
        'capabilities',
        'providers',
        'configVersion',
        'scope',
        'diagnosticSummary',
    }
    assert len(payload['data']['capabilities']) == 8
    assert len(payload['data']['providers']) == 4
    assert set(payload['data']['capabilities'][0]) == {
        'capabilityId',
        'enabled',
        'provider',
        'model',
        'agentRole',
        'systemPrompt',
        'userPromptTemplate',
        'promptPreview',
    }
    assert set(payload['data']['providers'][0]) == {
        'provider',
        'label',
        'configured',
        'maskedSecret',
        'baseUrl',
        'secretSource',
        'supportsTextGeneration',
        'readiness',
        'lastCheckedAt',
        'errorCode',
        'errorMessage',
        'scope',
    }
    assert set(payload['data']['diagnosticSummary']) == {
        'configuredProviderCount',
        'readyProviderCount',
        'degradedProviderCount',
        'lastHealthRefreshAt',
    }
    assert payload['data']['scope'] == 'runtime_local'


def test_ai_provider_secret_and_health_contract_return_expected_shapes(
    runtime_client: TestClient,
) -> None:
    secret_response = runtime_client.put(
        '/api/settings/ai-capabilities/providers/openai/secret',
        json={'apiKey': 'sk-contract-openai-123456'},
    )

    assert secret_response.status_code == 200
    secret_payload = secret_response.json()
    assert set(secret_payload) == {'ok', 'data'}
    assert secret_payload['ok'] is True
    assert set(secret_payload['data']) == {
        'provider',
        'label',
        'configured',
        'maskedSecret',
        'baseUrl',
        'secretSource',
        'supportsTextGeneration',
        'readiness',
        'lastCheckedAt',
        'errorCode',
        'errorMessage',
        'scope',
    }
    assert secret_payload['data']['provider'] == 'openai'

    health_response = runtime_client.post(
        '/api/settings/ai-capabilities/providers/openai/health-check',
        json={'model': 'gpt-5.4'},
    )

    assert health_response.status_code == 200
    health_payload = health_response.json()
    assert set(health_payload) == {'ok', 'data'}
    assert health_payload['ok'] is True
    assert set(health_payload['data']) == {'provider', 'status', 'message', 'model', 'checkedAt', 'latencyMs'}
    assert health_payload['data']['provider'] == 'openai'


def test_ai_provider_catalog_contract_exposes_multi_provider_registry(
    runtime_client: TestClient,
) -> None:
    response = runtime_client.get('/api/settings/ai-providers/catalog')

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {'ok', 'data'}
    assert payload['ok'] is True
    assert len(payload['data']) == 4

    providers = {item['provider']: item for item in payload['data']}
    assert set(providers) == {'openai', 'deepseek', 'volcengine', 'volcengine_tts'}
    assert set(providers['openai']) == {
        'provider',
        'label',
        'kind',
        'region',
        'category',
        'protocol',
        'modelSyncMode',
        'tags',
        'configured',
        'baseUrl',
        'secretSource',
        'capabilities',
        'requiresBaseUrl',
        'supportsModelDiscovery',
        'status',
    }
    assert 'apiKey' not in providers['openai']
    assert 'text_generation' in providers['openai']['capabilities']
    assert 'tts' not in providers['openai']['capabilities']
    assert providers['volcengine']['region'] == 'domestic'
    assert providers['volcengine']['modelSyncMode'] == 'remote'
    assert 'asset_analysis' in providers['volcengine']['capabilities']
    assert 'video_generation' in providers['volcengine']['capabilities']
    assert 'tts' not in providers['volcengine']['capabilities']
    assert providers['volcengine_tts']['category'] == 'tts'
    assert providers['volcengine_tts']['protocol'] == 'volcengine_tts'
    assert providers['volcengine_tts']['capabilities'] == ['tts']


def test_ai_provider_model_catalog_contract_returns_models_for_provider(
    runtime_client: TestClient,
) -> None:
    response = runtime_client.get('/api/settings/ai-providers/openai/models')

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {'ok', 'data'}
    assert payload['ok'] is True
    assert len(payload['data']) >= 2
    assert set(payload['data'][0]) == {
        'modelId',
        'displayName',
        'provider',
        'capabilityTypes',
        'inputModalities',
        'outputModalities',
        'contextWindow',
        'defaultFor',
        'enabled',
    }
    model_ids = {item['modelId'] for item in payload['data']}
    assert 'gpt-5.4' in model_ids


def test_domestic_provider_model_catalog_marks_media_capabilities(
    runtime_client: TestClient,
) -> None:
    response = runtime_client.get('/api/settings/ai-providers/volcengine/models')

    assert response.status_code == 200
    payload = response.json()
    assert payload['ok'] is True
    models = payload['data']
    assert any(
        item['provider'] == 'volcengine'
        and 'asset_analysis' in item['capabilityTypes']
        and 'video' in item['inputModalities']
        and 'text' in item['outputModalities']
        for item in models
    )
    assert any(
        item['provider'] == 'volcengine'
        and 'video_generation' in item['capabilityTypes']
        and 'video' in item['outputModalities']
        for item in models
    )

    tts_response = runtime_client.get('/api/settings/ai-providers/volcengine_tts/models')
    assert tts_response.status_code == 200
    tts_models = tts_response.json()['data']
    assert any(
        item['provider'] == 'volcengine_tts'
        and 'tts' in item['capabilityTypes']
        and 'audio' in item['outputModalities']
        for item in tts_models
    )


def test_hidden_ai_provider_model_refresh_contract_returns_error_envelope(
    runtime_app,
) -> None:
    client = TestClient(runtime_app)
    response = client.post('/api/settings/ai-providers/ollama/models/refresh')

    assert response.status_code == 404
    payload = response.json()
    assert payload['ok'] is False
    assert payload['error'] == '当前版本暂未接入该 AI Provider。'


def test_ai_capability_support_matrix_contract_maps_capabilities_to_models(
    runtime_client: TestClient,
) -> None:
    response = runtime_client.get('/api/settings/ai-capabilities/support-matrix')

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {'ok', 'data'}
    assert payload['ok'] is True
    assert set(payload['data']) == {'capabilities'}
    assert len(payload['data']['capabilities']) == 8

    script_generation = next(
        item
        for item in payload['data']['capabilities']
        if item['capabilityId'] == 'script_generation'
    )
    assert set(script_generation) == {'capabilityId', 'providers', 'models'}
    assert 'openai' in script_generation['providers']
    assert any(
        item['provider'] == 'openai' and item['modelId'] == 'gpt-5.4'
        for item in script_generation['models']
    )


def test_unknown_ai_provider_uses_chinese_error_envelope(
    runtime_client: TestClient,
) -> None:
    response = runtime_client.get('/api/settings/ai-providers/not_real/models')

    assert response.status_code == 404
    payload = response.json()
    assert payload['ok'] is False
    assert payload['error'] == '当前版本暂未接入该 AI Provider。'
    assert payload['requestId']

def test_ai_provider_health_aggregate_contract_returns_expected_shape(
    runtime_client: TestClient,
) -> None:
    response = runtime_client.get('/api/ai-providers/health')

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {'ok', 'data'}
    assert payload['ok'] is True
    assert set(payload['data']) == {'providers', 'refreshedAt'}
    assert payload['data']['refreshedAt'] is None
    assert len(payload['data']['providers']) == 4
    assert set(payload['data']['providers'][0]) == {
        'provider',
        'label',
        'readiness',
        'lastCheckedAt',
        'latencyMs',
        'errorCode',
        'errorMessage',
    }


def test_ai_provider_model_upsert_contract_returns_write_receipt_and_model_shape(
    runtime_client: TestClient,
) -> None:
    response = runtime_client.put(
        '/api/ai-providers/openai/models/contract-writer',
        json={
            'displayName': 'Contract Writer',
            'capabilityKinds': ['text_generation'],
            'inputModalities': ['text'],
            'outputModalities': ['text'],
            'contextWindow': 32000,
            'defaultFor': ['script_generation'],
            'enabled': True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {'ok', 'data'}
    assert payload['ok'] is True
    assert set(payload['data']) == {
        'saved',
        'wasUpsert',
        'updatedAt',
        'versionOrRevision',
        'objectSummary',
        'model',
    }
    assert payload['data']['saved'] is True
    assert payload['data']['wasUpsert'] is False
    assert payload['data']['objectSummary'] == {
        'provider': 'openai',
        'modelId': 'contract-writer',
        'displayName': 'Contract Writer',
    }
    assert set(payload['data']['model']) == {
        'modelId',
        'displayName',
        'provider',
        'capabilityTypes',
        'inputModalities',
        'outputModalities',
        'contextWindow',
        'defaultFor',
        'enabled',
    }
