from __future__ import annotations

import logging

from ai.providers._http import request_json
from ai.providers.base import TextGenerationAdapter, TextGenerationRequest, TextGenerationResponse
from ai.providers.errors import ProviderHTTPException

log = logging.getLogger(__name__)


class AnthropicMessagesTextGenerationAdapter(TextGenerationAdapter):
    def __init__(self, *, base_url: str, api_key: str) -> None:
        self._base_url = base_url
        self._api_key = api_key

    def generate(self, request: TextGenerationRequest) -> TextGenerationResponse:
        try:
            payload = request_json(
                self._base_url,
                payload={
                    'model': request.model,
                    'system': request.system_prompt,
                    'messages': [
                        {'role': 'user', 'content': request.user_prompt},
                    ],
                    'max_tokens': request.max_output_tokens or 1024,
                },
                headers={
                    'anthropic-version': '2023-06-01',
                },
                api_key=self._api_key,
                api_key_header_name='x-api-key',
                timeout=request.timeout_seconds,
            )
        except ProviderHTTPException:
            raise
        except Exception as exc:  # pragma: no cover - 防御性兜底
            log.exception('Anthropic 文本生成失败')
            raise ProviderHTTPException(
                status_code=502,
                detail='AI Provider 请求失败，请稍后重试。',
                error_code='ai_provider_server_error',
            ) from exc

        parts: list[str] = []
        for item in payload.get('content', []):
            if not isinstance(item, dict):
                continue
            text = item.get('text')
            if isinstance(text, str) and text.strip():
                parts.append(text.strip())

        text = '\n'.join(parts).strip()
        if not text:
            raise ProviderHTTPException(
                status_code=502,
                detail='Anthropic 返回了空文本。',
                error_code='ai_provider_empty_response',
            )

        return TextGenerationResponse(
            text=text,
            provider='anthropic',
            model=request.model,
            provider_request_id=request.request_id,
        )
