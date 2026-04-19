from __future__ import annotations

import logging
from urllib.parse import quote

from ai.providers._http import request_json
from ai.providers.base import TextGenerationAdapter, TextGenerationRequest, TextGenerationResponse
from ai.providers.errors import ProviderHTTPException

log = logging.getLogger(__name__)


class GeminiGenerateTextGenerationAdapter(TextGenerationAdapter):
    def __init__(self, *, base_url: str, api_key: str) -> None:
        self._base_url = base_url
        self._api_key = api_key

    def generate(self, request: TextGenerationRequest) -> TextGenerationResponse:
        endpoint = (
            f'{self._base_url.rstrip("/")}/{quote(request.model, safe="")}'
            f':generateContent?key={quote(self._api_key, safe="")}'
        )
        try:
            payload = request_json(
                endpoint,
                payload={
                    'systemInstruction': {
                        'parts': [{'text': request.system_prompt}],
                    },
                    'contents': [
                        {
                            'role': 'user',
                            'parts': [{'text': request.user_prompt}],
                        }
                    ],
                    'generationConfig': {
                        'maxOutputTokens': request.max_output_tokens or 1024,
                    },
                },
                timeout=request.timeout_seconds,
            )
        except ProviderHTTPException:
            raise
        except Exception as exc:  # pragma: no cover - 防御性兜底
            log.exception('Gemini 文本生成失败')
            raise ProviderHTTPException(
                status_code=502,
                detail='AI Provider 请求失败，请稍后重试。',
                error_code='ai_provider_server_error',
            ) from exc

        parts: list[str] = []
        candidates = payload.get('candidates', [])
        if candidates and isinstance(candidates[0], dict):
            content = candidates[0].get('content', {})
            if isinstance(content, dict):
                for part in content.get('parts', []):
                    if not isinstance(part, dict):
                        continue
                    text = part.get('text')
                    if isinstance(text, str) and text.strip():
                        parts.append(text.strip())

        text = '\n'.join(parts).strip()
        if not text:
            raise ProviderHTTPException(
                status_code=502,
                detail='Gemini 返回了空文本。',
                error_code='ai_provider_empty_response',
            )

        return TextGenerationResponse(
            text=text,
            provider='gemini',
            model=request.model,
            provider_request_id=request.request_id,
        )
