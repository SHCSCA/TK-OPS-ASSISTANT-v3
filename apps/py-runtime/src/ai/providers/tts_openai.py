from __future__ import annotations

import logging

from ai.providers._http import request_bytes
from ai.providers.base import TTSAdapter, TTSRequest, TTSResponse
from ai.providers.errors import ProviderHTTPException

log = logging.getLogger(__name__)


class OpenAITTSAdapter(TTSAdapter):
    def __init__(self, *, base_url: str, api_key: str) -> None:
        self._base_url = base_url
        self._api_key = api_key

    def synthesize(self, request: TTSRequest) -> TTSResponse:
        endpoint = _speech_endpoint(self._base_url)
        try:
            audio_bytes = request_bytes(
                endpoint,
                bearer_token=self._api_key,
                headers={'X-Request-ID': request.request_id or ''},
                payload={
                    'model': request.model,
                    'input': request.text,
                    'voice': request.voice_id,
                    'speed': request.speed,
                    'response_format': request.output_format,
                },
                timeout=request.timeout_seconds,
            )
        except ProviderHTTPException:
            raise
        except Exception as exc:  # pragma: no cover - 防御性兜底
            log.exception('OpenAI TTS 调用失败')
            raise ProviderHTTPException(
                status_code=502,
                detail='AI Provider 请求失败，请稍后重试。',
                error_code='ai_provider_server_error',
            ) from exc

        if not audio_bytes:
            raise ProviderHTTPException(
                status_code=502,
                detail='OpenAI TTS 返回了空音频。',
                error_code='ai_provider_empty_response',
            )

        return TTSResponse(
            audio_bytes=audio_bytes,
            content_type=_content_type_for_format(request.output_format),
            provider='openai',
            model=request.model,
            provider_request_id=request.request_id,
        )


def _speech_endpoint(base_url: str) -> str:
    normalized = base_url.rstrip('/')
    if normalized.endswith('/audio/speech'):
        return normalized
    if normalized.endswith('/responses'):
        normalized = normalized[: -len('/responses')]
    return normalized + '/audio/speech'


def _content_type_for_format(output_format: str) -> str:
    normalized = output_format.strip().lower()
    if normalized == 'wav':
        return 'audio/wav'
    if normalized == 'pcm':
        return 'audio/pcm'
    return 'audio/mpeg'
