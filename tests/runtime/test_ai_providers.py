from __future__ import annotations

import base64
import json
import urllib.error
from dataclasses import asdict
from typing import Any

import pytest

from ai.providers import dispatch_text_generation, dispatch_tts, has_tts_adapter
from ai.providers._http import request_bytes, request_json
from ai.providers.anthropic_messages import AnthropicMessagesTextGenerationAdapter
from ai.providers.base import (
    TTSAdapter,
    TTSRequest,
    TTSResponse,
    TextGenerationAdapter,
    TextGenerationMediaInput,
    TextGenerationRequest,
    TextGenerationResponse,
)
from ai.providers.cohere_chat import CohereChatTextGenerationAdapter
from ai.providers.errors import ProviderHTTPException
from ai.providers.gemini_generate import GeminiGenerateTextGenerationAdapter
from ai.providers.openai_chat import OpenAIChatTextGenerationAdapter
from ai.providers.openai_responses import OpenAIResponsesTextGenerationAdapter
from ai.providers.tts_openai import OpenAITTSAdapter
from services.ai_capability_service import ProviderRuntimeConfig


class _FakeBinaryResponse:
    def __init__(self, body: bytes, *, headers: dict[str, str] | None = None) -> None:
        self._body = body
        self.headers = headers or {}

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "_FakeBinaryResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def close(self) -> None:
        return None


def test_provider_dataclasses_expose_defaults_and_fields() -> None:
    request = TextGenerationRequest(
        model='gpt-5',
        system_prompt='系统提示',
        user_prompt='用户提示',
    )
    response = TextGenerationResponse(text='输出内容')
    tts_request = TTSRequest(text='你好', voice_id='alloy', model='gpt-4o-mini-tts')
    tts_response = TTSResponse(audio_bytes=b'abc')

    assert request.model == 'gpt-5'
    assert request.request_id is None
    assert request.temperature is None
    assert response.text == '输出内容'
    assert response.model is None
    assert response.provider_request_id is None
    assert response.response_headers == {}
    assert response.finish_reason is None
    assert tts_request.output_format == 'mp3'
    assert tts_request.speed == 1.0
    assert tts_response.content_type == 'audio/mpeg'
    assert tts_response.duration_ms is None
    assert tts_response.provider_request_id is None
    assert tts_response.response_headers == {}
    assert asdict(tts_response)['audio_bytes'] == b'abc'


def test_provider_response_metadata_fields_can_be_set() -> None:
    response = TextGenerationResponse(
        text='输出',
        provider='openai',
        model='gpt-5',
        provider_request_id='req-1',
        response_headers={'x-request-id': 'req-1'},
        finish_reason='stop',
    )
    tts_response = TTSResponse(
        audio_bytes=b'abc',
        provider='openai',
        model='gpt-4o-mini-tts',
        provider_request_id='tts-1',
        response_headers={'x-request-id': 'tts-1'},
    )

    assert response.provider_request_id == 'req-1'
    assert response.response_headers['x-request-id'] == 'req-1'
    assert response.finish_reason == 'stop'
    assert tts_response.provider_request_id == 'tts-1'
    assert tts_response.response_headers['x-request-id'] == 'tts-1'


def test_provider_http_exception_keeps_error_code() -> None:
    exc = ProviderHTTPException(
        status_code=502,
        detail='AI Provider 认证失败，请检查 API Key。',
        error_code='ai_provider_auth_failed',
    )

    assert exc.status_code == 502
    assert exc.error_code == 'ai_provider_auth_failed'
    assert exc.detail == 'AI Provider 认证失败，请检查 API Key。'


def test_request_json_applies_bearer_header_custom_header_and_query_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_urlopen(request, timeout=None):
        captured['url'] = request.full_url
        captured['method'] = request.get_method()
        captured['headers'] = {key.lower(): value for key, value in request.header_items()}
        captured['body'] = request.data
        captured['timeout'] = timeout
        return _FakeBinaryResponse(b'{"ok": true, "data": {"message": "hello"}}')

    monkeypatch.setattr('urllib.request.urlopen', fake_urlopen)

    payload = request_json(
        'https://example.com/v1/chat',
        payload={'text': '你好'},
        bearer_token='bearer-token',
        headers={'X-Custom-Header': '中文值'},
        api_key='query-key',
        api_key_query_name='key',
        timeout=12,
    )

    assert payload == {'ok': True, 'data': {'message': 'hello'}}
    assert captured['url'] == 'https://example.com/v1/chat?key=query-key'
    assert captured['method'] == 'POST'
    assert captured['headers']['authorization'] == 'Bearer bearer-token'
    assert captured['headers']['x-custom-header'] == '中文值'
    assert captured['headers']['content-type'] == 'application/json'
    assert json.loads(captured['body'].decode('utf-8')) == {'text': '你好'}
    assert captured['timeout'] == 12


def test_request_json_handles_empty_body_as_empty_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_urlopen(request, timeout=None):
        return _FakeBinaryResponse(b'')

    monkeypatch.setattr('urllib.request.urlopen', fake_urlopen)

    with pytest.raises(ProviderHTTPException) as exc_info:
        request_json('https://example.com/v1/chat', payload={'text': 'hello'})

    assert exc_info.value.error_code == 'ai_provider_empty_response'
    assert '空' in str(exc_info.value.detail)


def test_request_json_rejects_non_json_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_urlopen(request, timeout=None):
        return _FakeBinaryResponse(b'plain text')

    monkeypatch.setattr('urllib.request.urlopen', fake_urlopen)

    with pytest.raises(ProviderHTTPException) as exc_info:
        request_json('https://example.com/v1/chat', payload={'text': 'hello'})

    assert exc_info.value.error_code == 'ai_provider_empty_response'
    assert 'JSON' in str(exc_info.value.detail)


def test_request_json_rejects_non_dict_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_urlopen(request, timeout=None):
        return _FakeBinaryResponse(b'["ok", "data"]')

    monkeypatch.setattr('urllib.request.urlopen', fake_urlopen)

    with pytest.raises(ProviderHTTPException) as exc_info:
        request_json('https://example.com/v1/chat', payload={'text': 'hello'})

    assert exc_info.value.error_code == 'ai_provider_empty_response'
    assert 'JSON' in str(exc_info.value.detail)


def test_openai_chat_adapter_sends_video_url_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_request_json(endpoint, *, bearer_token, headers, payload, timeout):
        captured['endpoint'] = endpoint
        captured['bearer_token'] = bearer_token
        captured['headers'] = headers
        captured['payload'] = payload
        captured['timeout'] = timeout
        return {'choices': [{'message': {'content': '已完成视频拆解'}}]}

    monkeypatch.setattr('ai.providers.openai_chat.request_json', fake_request_json)

    adapter = OpenAIChatTextGenerationAdapter(
        base_url='https://ark.cn-beijing.volces.com/api/v3',
        api_key='test-key',
    )
    result = adapter.generate(
        TextGenerationRequest(
            model='doubao-seed-2-0-pro-260215',
            system_prompt='系统',
            user_prompt='请拆解视频',
            request_id='req-video',
            media_inputs=(
                TextGenerationMediaInput(
                    kind='video',
                    url='data:video/mp4;base64,AAAA',
                    mime_type='video/mp4',
                    fps=1.0,
                    filename='demo.mp4',
                ),
            ),
        )
    )

    assert result.text == '已完成视频拆解'
    payload = captured['payload']
    assert isinstance(payload, dict)
    messages = payload['messages']
    assert messages[1]['role'] == 'user'
    assert messages[1]['content'] == [
        {
            'type': 'video_url',
            'video_url': {'url': 'data:video/mp4;base64,AAAA', 'fps': 1.0},
        },
        {'type': 'text', 'text': '请拆解视频'},
    ]


def test_request_bytes_reads_binary_response(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(request, timeout=None):
        return _FakeBinaryResponse(b'\x00\x01\x02')

    monkeypatch.setattr('urllib.request.urlopen', fake_urlopen)

    audio_bytes = request_bytes(
        'https://example.com/v1/audio',
        headers={'X-Trace': 'trace-1'},
        bearer_token='token-1',
    )

    assert audio_bytes == b'\x00\x01\x02'


@pytest.mark.parametrize(
    ('status_code', 'expected_code'),
    [
        (400, 'request.invalid_payload'),
        (404, 'runtime.resource_not_found'),
        (422, 'request.validation_failed'),
        (401, 'ai_provider_auth_failed'),
        (403, 'ai_provider_auth_failed'),
        (429, 'ai_provider_rate_limited'),
        (503, 'ai_provider_server_error'),
    ],
)
def test_request_json_maps_http_errors_to_provider_exception(
    monkeypatch: pytest.MonkeyPatch,
    status_code: int,
    expected_code: str,
) -> None:
    def fake_urlopen(request, timeout=None):
        raise urllib.error.HTTPError(
            request.full_url,
            status_code,
            'error',
            hdrs=None,
            fp=_FakeBinaryResponse('{"error": {"message": "服务异常"}}'.encode('utf-8')),
        )

    monkeypatch.setattr('urllib.request.urlopen', fake_urlopen)

    with pytest.raises(ProviderHTTPException) as exc_info:
        request_json('https://example.com/v1/chat', payload={'text': 'hello'})

    assert exc_info.value.status_code == 502
    assert exc_info.value.error_code == expected_code
    assert 'AI Provider' in str(exc_info.value.detail)
    assert '服务异常' in str(exc_info.value.detail)


def test_request_json_maps_timeout_and_unreachable_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_timeout(request, timeout=None):
        raise TimeoutError('timeout')

    monkeypatch.setattr('urllib.request.urlopen', fake_timeout)

    with pytest.raises(ProviderHTTPException) as timeout_exc:
        request_json('https://example.com/v1/chat', payload={'text': 'hello'})

    assert timeout_exc.value.error_code == 'ai_provider_timeout'
    assert '超时' in str(timeout_exc.value.detail)

    def fake_unreachable(request, timeout=None):
        raise urllib.error.URLError('unreachable')

    monkeypatch.setattr('urllib.request.urlopen', fake_unreachable)

    with pytest.raises(ProviderHTTPException) as unreachable_exc:
        request_bytes('https://example.com/v1/audio')

    assert unreachable_exc.value.error_code == 'ai_provider_unreachable'
    assert '连接' in str(unreachable_exc.value.detail)


def test_provider_adapters_define_required_methods() -> None:
    assert hasattr(TextGenerationAdapter, 'generate')
    assert hasattr(TTSAdapter, 'synthesize')


def test_dispatch_text_generation_uses_protocol_family_registry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = ProviderRuntimeConfig(
        provider='openai',
        label='OpenAI',
        api_key='test-key',
        base_url='https://api.openai.com/v1/responses',
        secret_source='test',
        requires_secret=True,
        supports_text_generation=True,
        supports_tts=True,
        protocol_family='openai_responses',
    )
    captured: dict[str, object] = {}

    def fake_generate(self, request):
        captured['adapter'] = self.__class__.__name__
        captured['model'] = request.model
        return TextGenerationResponse(text='responses-output', provider='openai', model=request.model)

    monkeypatch.setattr(OpenAIResponsesTextGenerationAdapter, 'generate', fake_generate)

    result = dispatch_text_generation(
        runtime,
        TextGenerationRequest(model='gpt-5', system_prompt='sys', user_prompt='user'),
    )

    assert result.text == 'responses-output'
    assert captured['adapter'] == 'OpenAIResponsesTextGenerationAdapter'
    assert captured['model'] == 'gpt-5'


def test_dispatch_text_generation_routes_openai_compatible_protocol_to_chat(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = ProviderRuntimeConfig(
        provider='openai_compatible',
        label='OpenAI-compatible',
        api_key='test-key',
        base_url='https://example.com/v1',
        secret_source='test',
        requires_secret=True,
        supports_text_generation=True,
        supports_tts=False,
        protocol_family='openai_chat',
    )
    captured: dict[str, object] = {}

    def fake_generate(self, request):
        captured['adapter'] = self.__class__.__name__
        captured['prompt'] = request.user_prompt
        return TextGenerationResponse(text='chat-output', provider='openai_compatible', model=request.model)

    monkeypatch.setattr(OpenAIChatTextGenerationAdapter, 'generate', fake_generate)

    result = dispatch_text_generation(
        runtime,
        TextGenerationRequest(model='custom-model', system_prompt='sys', user_prompt='user'),
    )

    assert result.text == 'chat-output'
    assert captured['adapter'] == 'OpenAIChatTextGenerationAdapter'
    assert captured['prompt'] == 'user'


@pytest.mark.parametrize(
    ('protocol_family', 'adapter_cls', 'provider'),
    [
        ('anthropic_messages', AnthropicMessagesTextGenerationAdapter, 'anthropic'),
        ('gemini_generate', GeminiGenerateTextGenerationAdapter, 'gemini'),
        ('cohere_chat', CohereChatTextGenerationAdapter, 'cohere'),
    ],
)
def test_dispatch_text_generation_routes_new_protocols(
    monkeypatch: pytest.MonkeyPatch,
    protocol_family: str,
    adapter_cls: type[TextGenerationAdapter],
    provider: str,
) -> None:
    runtime = ProviderRuntimeConfig(
        provider=provider,
        label=provider,
        api_key='test-key',
        base_url='https://example.com/v1',
        secret_source='test',
        requires_secret=True,
        supports_text_generation=True,
        supports_tts=False,
        protocol_family=protocol_family,
    )
    captured: dict[str, object] = {}

    def fake_generate(self, request):
        captured['adapter'] = self.__class__.__name__
        return TextGenerationResponse(text=f'{provider}-output', provider=provider, model=request.model)

    monkeypatch.setattr(adapter_cls, 'generate', fake_generate)

    result = dispatch_text_generation(
        runtime,
        TextGenerationRequest(model='model-1', system_prompt='sys', user_prompt='user'),
    )

    assert result.text == f'{provider}-output'
    assert captured['adapter'] == adapter_cls.__name__


def test_dispatch_text_generation_rejects_unknown_protocol_family() -> None:
    runtime = ProviderRuntimeConfig(
        provider='mystery',
        label='Mystery',
        api_key='test-key',
        base_url='https://example.com/v1',
        secret_source='test',
        requires_secret=True,
        supports_text_generation=True,
        supports_tts=False,
        protocol_family='not-a-real-protocol',
    )

    with pytest.raises(ProviderHTTPException) as exc_info:
        dispatch_text_generation(
            runtime,
            TextGenerationRequest(model='model-1', system_prompt='sys', user_prompt='user'),
        )

    assert exc_info.value.error_code == 'ai_provider_unsupported'


def test_dispatch_tts_rejects_openai_provider_adapter() -> None:
    runtime = ProviderRuntimeConfig(
        provider='openai',
        label='OpenAI',
        api_key='test-key',
        base_url='https://api.openai.com/v1/responses',
        secret_source='test',
        requires_secret=True,
        supports_text_generation=True,
        supports_tts=True,
        protocol_family='openai_responses',
    )

    with pytest.raises(ProviderHTTPException) as exc_info:
        dispatch_tts(
            runtime,
            TTSRequest(text='你好', voice_id='alloy', model='gpt-4o-mini-tts'),
        )

    assert exc_info.value.error_code == 'tts_provider_not_available'


def test_dispatch_tts_routes_volcengine_doubao_speech_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = ProviderRuntimeConfig(
        provider='volcengine_tts',
        label='火山豆包语音',
        api_key='sk-test-volcengine',
        base_url='https://openspeech.bytedance.com/api/v1/tts?appid=test-app&cluster=volcano_tts',
        secret_source='test',
        requires_secret=True,
        supports_text_generation=True,
        supports_tts=True,
        protocol_family='volcengine_tts',
    )
    captured: dict[str, object] = {}

    def fake_urlopen(request, timeout=None):
        captured['url'] = request.full_url
        captured['method'] = request.get_method()
        captured['headers'] = {key.lower(): value for key, value in request.header_items()}
        captured['body'] = request.data
        captured['timeout'] = timeout
        response = {
            'reqid': 'req-volc-tts',
            'code': 3000,
            'message': 'Success',
            'operation': 'query',
            'sequence': -1,
            'data': base64.b64encode(b'volcengine-tts-audio').decode('ascii'),
        }
        return _FakeBinaryResponse(json.dumps(response).encode('utf-8'))

    monkeypatch.setattr('urllib.request.urlopen', fake_urlopen)

    result = dispatch_tts(
        runtime,
        TTSRequest(
            text='你好，生成一段豆包配音。',
            voice_id='zh_female_kailangjiejie_moon_bigtts',
            model='doubao-tts',
            speed=1.1,
            request_id='req-volc-tts',
        ),
    )

    assert result.audio_bytes == b'volcengine-tts-audio'
    assert result.content_type == 'audio/mpeg'
    assert result.provider == 'volcengine_tts'
    assert result.model == 'doubao-tts'
    assert captured['url'] == 'https://openspeech.bytedance.com/api/v1/tts'
    assert captured['method'] == 'POST'
    assert captured['headers']['authorization'] == 'Bearer;sk-test-volcengine'
    assert captured['headers']['x-request-id'] == 'req-volc-tts'
    payload = json.loads(captured['body'].decode('utf-8'))
    assert payload['app'] == {
        'appid': 'test-app',
        'token': 'sk-test-volcengine',
        'cluster': 'volcano_tts',
    }
    assert payload['user'] == {'uid': 'tk-ops-runtime'}
    assert payload['audio'] == {
        'voice_type': 'zh_female_kailangjiejie_moon_bigtts',
        'encoding': 'mp3',
        'speed_ratio': 1.1,
        'volume_ratio': 1.0,
        'pitch_ratio': 1.0,
    }
    assert payload['request'] == {
        'reqid': 'req-volc-tts',
        'text': '你好，生成一段豆包配音。',
        'text_type': 'plain',
        'operation': 'query',
        'with_frontend': 1,
        'frontend_type': 'unitTson',
    }


def test_dispatch_tts_routes_volcengine_api_key_sse_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = ProviderRuntimeConfig(
        provider='volcengine_tts',
        label='火山豆包语音',
        api_key='api-key-test-volcengine',
        base_url='https://ark.cn-beijing.volces.com/api/v3',
        secret_source='test',
        requires_secret=True,
        supports_text_generation=True,
        supports_tts=True,
        protocol_family='volcengine_tts',
    )
    captured: dict[str, object] = {}

    def fake_urlopen(request, timeout=None):
        captured['url'] = request.full_url
        captured['method'] = request.get_method()
        captured['headers'] = {key.lower(): value for key, value in request.header_items()}
        captured['body'] = request.data
        audio_1 = base64.b64encode(b'volcengine-').decode('ascii')
        audio_2 = base64.b64encode(b'tts-audio').decode('ascii')
        body = (
            f'data: {{"code":3000,"message":"Success","sequence":1,"data":"{audio_1}"}}\n\n'
            f'data: {{"code":3000,"message":"Success","sequence":-1,"data":"{audio_2}"}}\n\n'
        )
        return _FakeBinaryResponse(body.encode('utf-8'))

    monkeypatch.setattr('urllib.request.urlopen', fake_urlopen)

    result = dispatch_tts(
        runtime,
        TTSRequest(
            text='你好，生成一段豆包配音。',
            voice_id='zh_female_kailangjiejie_moon_bigtts',
            model='doubao-tts',
            speed=1.1,
            request_id='req-volc-tts',
        ),
    )

    assert result.audio_bytes == b'volcengine-tts-audio'
    assert result.provider == 'volcengine_tts'
    assert result.model == 'doubao-tts'
    assert captured['url'] == 'https://openspeech.bytedance.com/api/v3/tts/unidirectional/sse'
    assert captured['method'] == 'POST'
    assert captured['headers']['x-api-key'] == 'api-key-test-volcengine'
    assert captured['headers']['x-api-resource-id'] == 'seed-tts-1.0'
    assert captured['headers']['x-api-request-id'] == 'req-volc-tts'
    assert captured['headers']['x-api-sequence'] == '-1'
    payload = json.loads(captured['body'].decode('utf-8'))
    assert payload == {
        'user': {'uid': 'tk-ops-runtime'},
        'req_params': {
            'text': '你好，生成一段豆包配音。',
            'speaker': 'zh_female_kailangjiejie_moon_bigtts',
            'audio_params': {
                'format': 'mp3',
                'sample_rate': 24000,
                'speech_rate': 10,
            },
        },
    }


def test_has_tts_adapter_reflects_registered_provider_support() -> None:
    assert has_tts_adapter('openai') is False
    assert has_tts_adapter('volcengine_tts') is True
    assert has_tts_adapter('volcengine') is False
    assert has_tts_adapter('localai') is False


def test_openai_tts_adapter_uses_audio_speech_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_request_bytes(url, *, payload=None, timeout=60.0, method='POST', bearer_token=None, headers=None, api_key=None, api_key_header_name=None, api_key_query_name=None):
        captured['url'] = url
        captured['payload'] = payload
        captured['bearer_token'] = bearer_token
        captured['headers'] = dict(headers or {})
        return b'openai-tts-audio'

    monkeypatch.setattr('ai.providers.tts_openai.request_bytes', fake_request_bytes)

    adapter = OpenAITTSAdapter(
        base_url='https://api.openai.com/v1/responses',
        api_key='openai-key',
    )
    result = adapter.synthesize(
        TTSRequest(
            text='你好，生成一段配音。',
            voice_id='alloy',
            model='gpt-4o-mini-tts',
            speed=1.25,
            output_format='mp3',
            request_id='req-tts-1',
        )
    )

    assert result.audio_bytes == b'openai-tts-audio'
    assert result.content_type == 'audio/mpeg'
    assert result.provider == 'openai'
    assert result.model == 'gpt-4o-mini-tts'
    assert captured['url'] == 'https://api.openai.com/v1/audio/speech'
    assert captured['bearer_token'] == 'openai-key'
    assert captured['headers']['X-Request-ID'] == 'req-tts-1'
    assert captured['payload'] == {
        'model': 'gpt-4o-mini-tts',
        'input': '你好，生成一段配音。',
        'voice': 'alloy',
        'speed': 1.25,
        'response_format': 'mp3',
    }


def test_anthropic_adapter_uses_messages_endpoint_and_parses_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_request_json(
        url,
        *,
        payload=None,
        timeout=60.0,
        method='POST',
        bearer_token=None,
        headers=None,
        api_key=None,
        api_key_header_name=None,
        api_key_query_name=None,
    ):
        captured['url'] = url
        captured['payload'] = payload
        captured['headers'] = dict(headers or {})
        captured['api_key'] = api_key
        captured['api_key_header_name'] = api_key_header_name
        return {'content': [{'text': 'anthropic-output'}]}

    monkeypatch.setattr('ai.providers.anthropic_messages.request_json', fake_request_json)

    adapter = AnthropicMessagesTextGenerationAdapter(base_url='https://example.com/v1/messages', api_key='anthropic-key')
    result = adapter.generate(
        TextGenerationRequest(model='claude-sonnet', system_prompt='system', user_prompt='user'),
    )

    assert result.text == 'anthropic-output'
    assert captured['url'] == 'https://example.com/v1/messages'
    assert captured['headers']['anthropic-version'] == '2023-06-01'
    assert captured['api_key'] == 'anthropic-key'
    assert captured['api_key_header_name'] == 'x-api-key'
    assert captured['payload']['system'] == 'system'
    assert captured['payload']['messages'] == [{'role': 'user', 'content': 'user'}]


def test_gemini_adapter_uses_generate_content_endpoint_and_parses_parts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_request_json(
        url,
        *,
        payload=None,
        timeout=60.0,
        method='POST',
        bearer_token=None,
        headers=None,
        api_key=None,
        api_key_header_name=None,
        api_key_query_name=None,
    ):
        captured['url'] = url
        captured['payload'] = payload
        return {
            'candidates': [
                {
                    'content': {
                        'parts': [{'text': 'gemini-output'}],
                    }
                }
            ]
        }

    monkeypatch.setattr('ai.providers.gemini_generate.request_json', fake_request_json)

    adapter = GeminiGenerateTextGenerationAdapter(base_url='https://example.com/v1beta/models', api_key='gemini-key')
    result = adapter.generate(
        TextGenerationRequest(model='gemini 2.5/pro', system_prompt='system', user_prompt='user'),
    )

    assert result.text == 'gemini-output'
    assert captured['url'] == 'https://example.com/v1beta/models/gemini%202.5%2Fpro:generateContent?key=gemini-key'
    assert captured['payload']['systemInstruction'] == {'parts': [{'text': 'system'}]}
    assert captured['payload']['contents'] == [{'role': 'user', 'parts': [{'text': 'user'}]}]


def test_cohere_adapter_uses_chat_endpoint_and_parses_message_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_request_json(
        url,
        *,
        payload=None,
        timeout=60.0,
        method='POST',
        bearer_token=None,
        headers=None,
        api_key=None,
        api_key_header_name=None,
        api_key_query_name=None,
    ):
        captured['url'] = url
        captured['payload'] = payload
        captured['bearer_token'] = bearer_token
        captured['headers'] = dict(headers or {})
        return {'message': {'content': 'cohere-output'}}

    monkeypatch.setattr('ai.providers.cohere_chat.request_json', fake_request_json)

    adapter = CohereChatTextGenerationAdapter(base_url='https://example.com/v2', api_key='cohere-key')
    result = adapter.generate(
        TextGenerationRequest(model='command-r', system_prompt='system', user_prompt='user'),
    )

    assert result.text == 'cohere-output'
    assert captured['url'] == 'https://example.com/v2/chat'
    assert captured['bearer_token'] == 'cohere-key'
    assert captured['payload']['messages'] == [
        {'role': 'system', 'content': 'system'},
        {'role': 'user', 'content': 'user'},
    ]
