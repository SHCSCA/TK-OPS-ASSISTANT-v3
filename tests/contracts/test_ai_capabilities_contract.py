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
    assert len(payload['data']['providers']) == 4
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

    health_response = runtime_client.post('/api/settings/ai-capabilities/providers/openai/health-check')

    assert health_response.status_code == 200
    health_payload = health_response.json()
    assert set(health_payload) == {'ok', 'data'}
    assert health_payload['ok'] is True
    assert set(health_payload['data']) == {'provider', 'status', 'message'}
    assert health_payload['data']['provider'] == 'openai'
