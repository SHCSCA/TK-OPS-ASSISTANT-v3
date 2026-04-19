from __future__ import annotations

import logging

from ai.providers._http import request_json
from ai.providers.base import TextGenerationAdapter, TextGenerationRequest, TextGenerationResponse
from ai.providers.errors import ProviderHTTPException

log = logging.getLogger(__name__)


class OpenAIResponsesTextGenerationAdapter(TextGenerationAdapter):
    def __init__(self, *, base_url: str, api_key: str) -> None:
        self._base_url = base_url
        self._api_key = api_key

    def generate(self, request: TextGenerationRequest) -> TextGenerationResponse:
        try:
            payload = request_json(
                self._base_url,
                bearer_token=self._api_key,
                headers={'X-Request-ID': request.request_id or ''},
                payload={
                    'model': request.model,
                    'instructions': request.system_prompt,
                    'input': request.user_prompt,
                },
                timeout=request.timeout_seconds,
            )
        except ProviderHTTPException:
            raise
        except Exception as exc:  # pragma: no cover - 防御性兜底
            log.exception('OpenAI Responses 文本生成失败')
            raise ProviderHTTPException(
                status_code=502,
                detail='AI Provider 请求失败，请稍后重试。',
                error_code='ai_provider_server_error',
            ) from exc

        texts: list[str] = []
        output_text = payload.get('output_text')
        if isinstance(output_text, str):
            texts.append(output_text)

        for item in payload.get('output', []):
            if not isinstance(item, dict) or item.get('type') != 'message':
                continue
            for content in item.get('content', []):
                if not isinstance(content, dict):
                    continue
                if content.get('type') in {'output_text', 'text'} and content.get('text'):
                    texts.append(str(content['text']))

        text = '\n'.join(part.strip() for part in texts if part and part.strip()).strip()
        if not text:
            raise ProviderHTTPException(
                status_code=502,
                detail='OpenAI 返回了空文本。',
                error_code='ai_provider_empty_response',
            )

        return TextGenerationResponse(
            text=text,
            provider='openai',
            model=request.model,
            provider_request_id=request.request_id,
        )
