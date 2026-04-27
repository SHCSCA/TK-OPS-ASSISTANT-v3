from __future__ import annotations

import base64
import binascii
import json
import logging
import os
import urllib.parse
from dataclasses import dataclass
from uuid import uuid4

from ai.providers._http import request_bytes, request_json
from ai.providers.base import TTSAdapter, TTSRequest, TTSResponse
from ai.providers.errors import ProviderHTTPException

log = logging.getLogger(__name__)

_ARK_DEFAULT_BASE_URL = 'https://ark.cn-beijing.volces.com/api/v3'
_DOUBAO_TTS_V1_ENDPOINT = 'https://openspeech.bytedance.com/api/v1/tts'
_DOUBAO_TTS_V3_SSE_ENDPOINT = 'https://openspeech.bytedance.com/api/v3/tts/unidirectional/sse'
_DEFAULT_CLUSTER = 'volcano_tts'
_DEFAULT_RESOURCE_ID = 'seed-tts-2.0'
_DEFAULT_UID = 'tk-ops-runtime'


@dataclass(frozen=True, slots=True)
class _VolcengineTTSCredentials:
    token: str
    app_id: str | None
    cluster: str
    uid: str


class VolcengineTTSAdapter(TTSAdapter):
    def __init__(self, *, base_url: str, api_key: str) -> None:
        self._base_url = base_url
        self._api_key = api_key

    def synthesize(self, request: TTSRequest) -> TTSResponse:
        endpoint, options = _resolve_endpoint_and_options(self._base_url)
        credentials = _resolve_credentials(self._api_key, options)
        request_id = request.request_id or str(uuid4())

        if _should_use_legacy_v1(endpoint, credentials):
            audio_bytes, provider_request_id = self._synthesize_legacy_v1(
                endpoint=endpoint,
                credentials=credentials,
                request=request,
                request_id=request_id,
            )
        else:
            audio_bytes, provider_request_id = self._synthesize_api_key_v3(
                endpoint=endpoint,
                options=options,
                credentials=credentials,
                request=request,
                request_id=request_id,
            )

        return TTSResponse(
            audio_bytes=audio_bytes,
            content_type=_content_type_for_format(request.output_format),
            provider='volcengine_tts',
            model=request.model,
            provider_request_id=provider_request_id,
        )

    def _synthesize_legacy_v1(
        self,
        *,
        endpoint: str,
        credentials: _VolcengineTTSCredentials,
        request: TTSRequest,
        request_id: str,
    ) -> tuple[bytes, str]:
        if credentials.app_id is None:
            raise ProviderHTTPException(
                status_code=400,
                detail='火山豆包语音旧版合成接口缺少 AppID，请改用新版 API Key 接口或补充 AppID。',
                error_code='volcengine_tts_missing_appid',
            )

        headers = dict(request.headers)
        headers.update(
            {
                'Authorization': f'Bearer;{credentials.token}',
                'X-Request-ID': request_id,
            }
        )

        payload = {
            'app': {
                'appid': credentials.app_id,
                'token': credentials.token,
                'cluster': credentials.cluster,
            },
            'user': {
                'uid': credentials.uid,
            },
            'audio': {
                'voice_type': request.voice_id,
                'encoding': _normalize_output_format(request.output_format),
                'speed_ratio': request.speed,
                'volume_ratio': 1.0,
                'pitch_ratio': 1.0,
            },
            'request': {
                'reqid': request_id,
                'text': request.text,
                'text_type': 'plain',
                'operation': 'query',
                'with_frontend': 1,
                'frontend_type': 'unitTson',
            },
        }

        try:
            response = request_json(
                endpoint,
                headers=headers,
                payload=payload,
                timeout=request.timeout_seconds,
            )
        except ProviderHTTPException:
            raise
        except Exception as exc:  # pragma: no cover - 防御性兜底
            log.exception('火山豆包语音合成调用失败')
            raise ProviderHTTPException(
                status_code=502,
                detail='火山豆包语音合成请求失败，请稍后重试。',
                error_code='ai_provider_server_error',
            ) from exc

        audio_bytes = _decode_audio_response(response)
        return audio_bytes, _response_request_id(response, fallback=request_id)

    def _synthesize_api_key_v3(
        self,
        *,
        endpoint: str,
        options: dict[str, str],
        credentials: _VolcengineTTSCredentials,
        request: TTSRequest,
        request_id: str,
    ) -> tuple[bytes, str]:
        headers = dict(request.headers)
        if credentials.app_id is not None:
            headers.update(
                {
                    'X-Api-App-Id': credentials.app_id,
                    'X-Api-Access-Key': credentials.token,
                }
            )
        else:
            headers['X-Api-Key'] = credentials.token

        headers.update(
            {
                'Accept': 'text/event-stream',
                'X-Api-Resource-Id': _resolve_resource_id(request, options),
                'X-Api-Request-Id': request_id,
                'X-Api-Sequence': '-1',
            }
        )
        payload = {
            'user': {'uid': credentials.uid},
            'req_params': {
                'text': request.text,
                'speaker': request.voice_id,
                'audio_params': {
                    'format': _normalize_output_format(request.output_format),
                    'sample_rate': 24000,
                    'speech_rate': _speech_rate_from_speed(request.speed),
                },
            },
        }

        try:
            response_body = request_bytes(
                _resolve_v3_sse_endpoint(endpoint),
                headers=headers,
                payload=payload,
                timeout=request.timeout_seconds,
            )
        except ProviderHTTPException:
            raise
        except Exception as exc:  # pragma: no cover - 防御性兜底
            log.exception('火山豆包语音 V3 合成调用失败')
            raise ProviderHTTPException(
                status_code=502,
                detail='火山豆包语音合成请求失败，请稍后重试。',
                error_code='ai_provider_server_error',
            ) from exc

        audio_bytes = _decode_streaming_audio_response(response_body)
        return audio_bytes, request_id


def _should_use_legacy_v1(endpoint: str, credentials: _VolcengineTTSCredentials) -> bool:
    return credentials.app_id is not None and endpoint.endswith('/api/v1/tts')


def _resolve_v3_sse_endpoint(endpoint: str) -> str:
    normalized = endpoint.rstrip('/')
    if normalized == _ARK_DEFAULT_BASE_URL or normalized.endswith('/api/v1/tts'):
        return _DOUBAO_TTS_V3_SSE_ENDPOINT
    if normalized.endswith('/api/v3/tts/unidirectional'):
        return f'{normalized}/sse'
    if normalized.endswith('/api/v3/tts/unidirectional/sse'):
        return normalized
    if normalized in {'https://openspeech.bytedance.com', 'http://openspeech.bytedance.com'}:
        return f'{normalized}/api/v3/tts/unidirectional/sse'
    return normalized


def _resolve_resource_id(request: TTSRequest, options: dict[str, str]) -> str:
    configured = (
        _option_value(options, 'resource_id', 'resourceId', 'resource')
        or os.getenv('TK_OPS_VOLCENGINE_TTS_RESOURCE_ID', '').strip()
    )
    if configured:
        return configured

    model = request.model.strip()
    if model.startswith('seed-tts-'):
        return model

    voice_id = request.voice_id.strip().lower()
    if 'uranus' in voice_id:
        return 'seed-tts-2.0'
    if 'moon_bigtts' in voice_id or voice_id.startswith('bv'):
        return 'seed-tts-1.0'
    return _DEFAULT_RESOURCE_ID


def _speech_rate_from_speed(speed: float) -> int:
    return max(-50, min(100, round((speed - 1.0) * 100)))


def _decode_streaming_audio_response(body: bytes) -> bytes:
    if not body:
        raise ProviderHTTPException(
            status_code=502,
            detail='火山豆包语音合成返回了空音频。',
            error_code='ai_provider_empty_response',
        )
    audio_chunks: list[bytes] = []
    for event in _streaming_response_events(body):
        code = event.get('code')
        if code != 3000:
            remote_message = _remote_message(event)
            raise ProviderHTTPException(
                status_code=502,
                detail=f'火山豆包语音合成失败：{remote_message}',
                error_code='volcengine_tts_remote_error',
            )
        data = event.get('data')
        if isinstance(data, str) and data.strip():
            audio_chunks.append(_decode_base64_audio(data))
    audio_bytes = b''.join(audio_chunks)
    if not audio_bytes:
        raise ProviderHTTPException(
            status_code=502,
            detail='火山豆包语音合成返回了空音频。',
            error_code='ai_provider_empty_response',
        )
    return audio_bytes


def _streaming_response_events(body: bytes) -> list[dict[str, object]]:
    try:
        text = body.decode('utf-8')
    except UnicodeDecodeError as exc:
        raise ProviderHTTPException(
            status_code=502,
            detail='火山豆包语音合成返回的流式响应无法解析。',
            error_code='ai_provider_empty_response',
        ) from exc

    stripped = text.strip()
    if not stripped:
        return []
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        payload = None
    if isinstance(payload, dict):
        return [payload]

    events: list[dict[str, object]] = []
    for line in text.splitlines():
        candidate = line.strip()
        if not candidate:
            continue
        if candidate.startswith('data:'):
            candidate = candidate[len('data:') :].strip()
        if candidate in {'[DONE]', 'DONE'} or not candidate.startswith('{'):
            continue
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            events.append(parsed)
    if not events:
        raise ProviderHTTPException(
            status_code=502,
            detail='火山豆包语音合成返回的流式响应无法解析。',
            error_code='ai_provider_empty_response',
        )
    return events


def _resolve_endpoint_and_options(base_url: str) -> tuple[str, dict[str, str]]:
    raw_base_url = (base_url or '').strip()
    if not raw_base_url:
        raw_base_url = _DOUBAO_TTS_V3_SSE_ENDPOINT

    parsed = urllib.parse.urlsplit(raw_base_url)
    options = {key.lower(): value for key, value in urllib.parse.parse_qsl(parsed.query)}
    endpoint = urllib.parse.urlunsplit(parsed._replace(query='', fragment='')).rstrip('/')

    if endpoint == _ARK_DEFAULT_BASE_URL:
        endpoint = _DOUBAO_TTS_V3_SSE_ENDPOINT
    elif endpoint in {'https://openspeech.bytedance.com', 'http://openspeech.bytedance.com'}:
        endpoint = f'{endpoint}/api/v3/tts/unidirectional/sse'

    return endpoint, options


def _resolve_credentials(api_key: str, options: dict[str, str]) -> _VolcengineTTSCredentials:
    secret_options = _parse_secret_options(api_key)
    merged = {**options, **secret_options}
    raw_secret = (api_key or '').strip()
    token_value = _option_value(merged, 'token', 'access_token', 'api_key')
    if not token_value and not raw_secret.startswith('{'):
        token_value = raw_secret
    token = _normalize_token(token_value)
    app_id = (
        _option_value(merged, 'appid', 'app_id', 'appId')
        or os.getenv('TK_OPS_VOLCENGINE_TTS_APP_ID', '').strip()
        or os.getenv('TK_OPS_VOLCENGINE_APP_ID', '').strip()
    )
    cluster = (
        _option_value(merged, 'cluster')
        or os.getenv('TK_OPS_VOLCENGINE_TTS_CLUSTER', '').strip()
        or os.getenv('TK_OPS_VOLCENGINE_CLUSTER', '').strip()
        or _DEFAULT_CLUSTER
    )
    uid = (
        _option_value(merged, 'uid', 'user_id', 'userId')
        or os.getenv('TK_OPS_VOLCENGINE_TTS_UID', '').strip()
        or _DEFAULT_UID
    )

    if not token:
        raise ProviderHTTPException(
            status_code=400,
            detail='火山豆包语音合成缺少 Access Token，请先配置 Provider API Key。',
            error_code='volcengine_tts_missing_token',
        )
    return _VolcengineTTSCredentials(
        token=token,
        app_id=app_id or None,
        cluster=cluster,
        uid=uid,
    )


def _parse_secret_options(api_key: str) -> dict[str, str]:
    raw_secret = (api_key or '').strip()
    if not raw_secret.startswith('{'):
        return {}
    try:
        payload = json.loads(raw_secret)
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, dict):
        return {}
    return {
        str(key).lower(): str(value).strip()
        for key, value in payload.items()
        if value is not None and str(value).strip()
    }


def _option_value(options: dict[str, str], *keys: str) -> str:
    for key in keys:
        value = options.get(key.lower())
        if value is not None and value.strip():
            return value.strip()
    return ''


def _normalize_token(raw_token: str) -> str:
    token = (raw_token or '').strip()
    for prefix in ('Bearer;', 'Bearer；', 'Bearer '):
        if token.startswith(prefix):
            return token[len(prefix) :].strip()
    return token


def _normalize_output_format(output_format: str) -> str:
    normalized = output_format.strip().lower()
    if normalized in {'wav', 'pcm'}:
        return normalized
    return 'mp3'


def _decode_audio_response(response: dict[str, object]) -> bytes:
    code = response.get('code')
    if code != 3000:
        remote_message = _remote_message(response)
        raise ProviderHTTPException(
            status_code=502,
            detail=f'火山豆包语音合成失败：{remote_message}',
            error_code='volcengine_tts_remote_error',
        )

    data = response.get('data')
    if not isinstance(data, str) or not data.strip():
        raise ProviderHTTPException(
            status_code=502,
            detail='火山豆包语音合成返回了空音频。',
            error_code='ai_provider_empty_response',
        )
    audio_bytes = _decode_base64_audio(data)
    if not audio_bytes:
        raise ProviderHTTPException(
            status_code=502,
            detail='火山豆包语音合成返回了空音频。',
            error_code='ai_provider_empty_response',
        )
    return audio_bytes


def _decode_base64_audio(data: str) -> bytes:
    try:
        return base64.b64decode(data)
    except (binascii.Error, ValueError) as exc:
        raise ProviderHTTPException(
            status_code=502,
            detail='火山豆包语音合成返回的音频编码无效。',
            error_code='ai_provider_empty_response',
        ) from exc


def _remote_message(response: dict[str, object]) -> str:
    message = response.get('message')
    if isinstance(message, str) and message.strip():
        return message.strip()
    code = response.get('code')
    if code is not None:
        return f'code={code}'
    return '上游未返回明确错误。'


def _response_request_id(response: dict[str, object], *, fallback: str) -> str:
    request_id = response.get('reqid')
    if isinstance(request_id, str) and request_id.strip():
        return request_id.strip()
    return fallback


def _content_type_for_format(output_format: str) -> str:
    normalized = output_format.strip().lower()
    if normalized == 'wav':
        return 'audio/wav'
    if normalized == 'pcm':
        return 'audio/pcm'
    return 'audio/mpeg'
