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
    assert set(providers) == {'openai', 'openai_compatible', 'anthropic', 'gemini'}
    assert providers['openai']['configured'] is False
    assert providers['openai']['maskedSecret'] == ''
    assert 'apiKey' not in providers['openai']


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
                    'userPromptTemplate': 'Topic: {{topic}}'
                },
                {
                    'capabilityId': 'script_rewrite',
                    'enabled': True,
                    'provider': 'openai',
                    'model': 'gpt-5-mini',
                    'agentRole': 'Script revision editor',
                    'systemPrompt': 'Improve pacing and hooks.',
                    'userPromptTemplate': 'Rewrite: {{script}}'
                },
                {
                    'capabilityId': 'storyboard_generation',
                    'enabled': True,
                    'provider': 'openai',
                    'model': 'gpt-5-mini',
                    'agentRole': 'Storyboard planner',
                    'systemPrompt': 'Turn scripts into shot plans.',
                    'userPromptTemplate': 'Storyboard: {{script}}'
                },
                {
                    'capabilityId': 'tts_generation',
                    'enabled': False,
                    'provider': 'openai',
                    'model': 'gpt-5-mini',
                    'agentRole': 'Voice designer',
                    'systemPrompt': 'Prepare TTS settings.',
                    'userPromptTemplate': 'Voice: {{script}}'
                },
                {
                    'capabilityId': 'subtitle_alignment',
                    'enabled': False,
                    'provider': 'openai',
                    'model': 'gpt-5-mini',
                    'agentRole': 'Subtitle aligner',
                    'systemPrompt': 'Align subtitles.',
                    'userPromptTemplate': 'Subtitle: {{script}}'
                },
                {
                    'capabilityId': 'video_generation',
                    'enabled': False,
                    'provider': 'openai_compatible',
                    'model': 'custom-video',
                    'agentRole': 'Video generator',
                    'systemPrompt': 'Prepare shots.',
                    'userPromptTemplate': 'Video: {{storyboard}}'
                },
                {
                    'capabilityId': 'asset_analysis',
                    'enabled': False,
                    'provider': 'gemini',
                    'model': 'gemini-2.5-pro',
                    'agentRole': 'Asset analyst',
                    'systemPrompt': 'Analyze assets.',
                    'userPromptTemplate': 'Assets: {{assets}}'
                }
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
