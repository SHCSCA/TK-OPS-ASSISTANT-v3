from __future__ import annotations

import logging

from ai.providers._http import request_json
from ai.providers.base import TextGenerationAdapter, TextGenerationRequest, TextGenerationResponse
from ai.providers.errors import ProviderHTTPException

log = logging.getLogger(__name__)


class CohereChatTextGenerationAdapter(TextGenerationAdapter):
    def __init__(self, *, base_url: str, api_key: str) -> None:
        self._base_url = base_url
        self._api_key = api_key

    def generate(self, request: TextGenerationRequest) -> TextGenerationResponse:
        endpoint = self._base_url.rstrip('/') + '/chat'
        try:
            payload = request_json(
                endpoint,
                payload={
                    'model': request.model,
                    'messages': [
                        {'role': 'system', 'content': request.system_prompt},
                        {'role': 'user', 'content': request.user_prompt},
                    ],
                    'max_tokens': request.max_output_tokens or 1024,
                },
                bearer_token=self._api_key,
                timeout=request.timeout_seconds,
            )
        except ProviderHTTPException:
            raise
        except Exception as exc:  # pragma: no cover - 防御性兜底
            log.exception('Cohere 文本生成失败')
            raise ProviderHTTPException(
                status_code=502,
                detail='AI Provider 请求失败，请稍后重试。',
                error_code='ai_provider_server_error',
            ) from exc

        message = payload.get('message', {})
        content = message.get('content', '') if isinstance(message, dict) else ''
        if isinstance(content, list):
            parts = [
                str(item.get('text', '')).strip()
                for item in content
                if isinstance(item, dict) and item.get('text')
            ]
            text = '\n'.join(part for part in parts if part).strip()
        else:
            text = str(content).strip()

        if not text:
            raise ProviderHTTPException(
                status_code=502,
                detail='Cohere 返回了空文本。',
                error_code='ai_provider_empty_response',
            )

        return TextGenerationResponse(
            text=text,
            provider='cohere',
            model=request.model,
            provider_request_id=request.request_id,
        )
