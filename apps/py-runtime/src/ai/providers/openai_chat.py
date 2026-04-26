from __future__ import annotations

import logging

from ai.providers._http import request_json
from ai.providers.base import TextGenerationAdapter, TextGenerationRequest, TextGenerationResponse
from ai.providers.errors import ProviderHTTPException

log = logging.getLogger(__name__)


class OpenAIChatTextGenerationAdapter(TextGenerationAdapter):
    def __init__(self, *, base_url: str, api_key: str) -> None:
        self._base_url = base_url
        self._api_key = api_key

    def generate(self, request: TextGenerationRequest) -> TextGenerationResponse:
        endpoint = self._base_url.rstrip('/') + '/chat/completions'
        try:
            payload = request_json(
                endpoint,
                bearer_token=self._api_key,
                headers={'X-Request-ID': request.request_id or ''},
                payload={
                    'model': request.model,
                    'messages': [
                        {'role': 'system', 'content': request.system_prompt},
                        {'role': 'user', 'content': _build_user_content(request)},
                    ],
                },
                timeout=request.timeout_seconds,
            )
        except ProviderHTTPException:
            raise
        except Exception as exc:  # pragma: no cover - 防御性兜底
            log.exception('OpenAI-compatible 文本生成失败')
            raise ProviderHTTPException(
                status_code=502,
                detail='AI Provider 请求失败，请稍后重试。',
                error_code='ai_provider_server_error',
            ) from exc

        choices = payload.get('choices', [])
        if not choices:
            raise ProviderHTTPException(
                status_code=502,
                detail='OpenAI-compatible Provider 未返回候选结果。',
                error_code='ai_provider_empty_response',
            )

        message = choices[0].get('message', {}) if isinstance(choices[0], dict) else {}
        content = message.get('content', '') if isinstance(message, dict) else ''
        if isinstance(content, list):
            text = '\n'.join(
                str(item.get('text', '')).strip()
                for item in content
                if isinstance(item, dict) and item.get('text')
            ).strip()
        else:
            text = str(content).strip()

        if not text:
            raise ProviderHTTPException(
                status_code=502,
                detail='OpenAI-compatible Provider 返回了空内容。',
                error_code='ai_provider_empty_response',
            )

        return TextGenerationResponse(
            text=text,
            provider='openai_compatible',
            model=request.model,
            provider_request_id=request.request_id,
        )


def _build_user_content(request: TextGenerationRequest) -> str | list[dict[str, object]]:
    if not request.media_inputs:
        return request.user_prompt

    content: list[dict[str, object]] = []
    for media in request.media_inputs:
        if media.kind != 'video':
            log.warning('OpenAI-compatible Chat 暂不支持媒体类型: %s', media.kind)
            continue
        video_url: dict[str, object] = {'url': media.url}
        if media.fps is not None:
            video_url['fps'] = media.fps
        content.append({'type': 'video_url', 'video_url': video_url})

    content.append({'type': 'text', 'text': request.user_prompt})
    return content
