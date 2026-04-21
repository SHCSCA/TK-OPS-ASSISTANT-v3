from __future__ import annotations

from fastapi.testclient import TestClient


def test_ai_capability_settings_contract_uses_settings_prefix_and_expected_shape(
    runtime_client: TestClient,
) -> None:
    response = runtime_client.get('/api/settings/ai-capabilities')

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {'ok', 'data'}
    assert payload['ok'] is True
    assert set(payload['data']) == {'capabilities', 'providers'}
    assert len(payload['data']['capabilities']) == 7
    assert len(payload['data']['providers']) >= 10
    assert set(payload['data']['capabilities'][0]) == {
        'capabilityId',
        'enabled',
        'provider',
        'model',
        'agentRole',
        'systemPrompt',
        'userPromptTemplate',
    }
    assert set(payload['data']['providers'][0]) == {
        'provider',
        'label',
        'configured',
        'maskedSecret',
        'baseUrl',
        'secretSource',
        'supportsTextGeneration',
    }


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
    assert len(payload['data']) >= 10

    providers = {item['provider']: item for item in payload['data']}
    assert {'openai', 'openai_compatible', 'anthropic', 'gemini', 'deepseek', 'openrouter', 'ollama'} <= set(
        providers
    )
    assert set(providers['openai']) == {
        'provider',
        'label',
        'kind',
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


def test_ai_capability_support_matrix_contract_maps_capabilities_to_models(
    runtime_client: TestClient,
) -> None:
    response = runtime_client.get('/api/settings/ai-capabilities/support-matrix')

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {'ok', 'data'}
    assert payload['ok'] is True
    assert set(payload['data']) == {'capabilities'}
    assert len(payload['data']['capabilities']) == 7

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
    assert payload['error'] == '未找到 AI Provider。'
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
    assert len(payload['data']['providers']) >= 10
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

