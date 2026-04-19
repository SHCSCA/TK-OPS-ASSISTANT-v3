from __future__ import annotations

from ai.providers.anthropic_messages import AnthropicMessagesTextGenerationAdapter
from ai.providers.base import (
    TTSAdapter,
    TTSRequest,
    TTSResponse,
    TextGenerationAdapter,
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

_TEXT_ADAPTERS: dict[str, type[TextGenerationAdapter]] = {
    'openai_responses': OpenAIResponsesTextGenerationAdapter,
    'openai_chat': OpenAIChatTextGenerationAdapter,
    'anthropic_messages': AnthropicMessagesTextGenerationAdapter,
    'gemini_generate': GeminiGenerateTextGenerationAdapter,
    'cohere_chat': CohereChatTextGenerationAdapter,
}

_TTS_ADAPTERS: dict[str, type[TTSAdapter]] = {
    'openai': OpenAITTSAdapter,
}


def has_tts_adapter(provider_id: str) -> bool:
    return provider_id in _TTS_ADAPTERS


def dispatch_text_generation(
    runtime_config: ProviderRuntimeConfig,
    request: TextGenerationRequest,
) -> TextGenerationResponse:
    adapter_cls = _TEXT_ADAPTERS.get(runtime_config.protocol_family)
    if adapter_cls is None:
        raise ProviderHTTPException(
            status_code=400,
            detail='当前 Provider 暂不支持文本生成。',
            error_code='ai_provider_unsupported',
        )

    adapter = adapter_cls(base_url=runtime_config.base_url, api_key=runtime_config.api_key or '')
    return adapter.generate(request)


def dispatch_tts(
    runtime_config: ProviderRuntimeConfig,
    request: TTSRequest,
) -> TTSResponse:
    adapter_cls = _TTS_ADAPTERS.get(runtime_config.provider)
    if adapter_cls is None:
        raise ProviderHTTPException(
            status_code=400,
            detail='当前 Provider 暂不支持 TTS。',
            error_code='tts_provider_not_available',
        )

    adapter = adapter_cls(base_url=runtime_config.base_url, api_key=runtime_config.api_key or '')
    return adapter.synthesize(request)


__all__ = [
    'ProviderHTTPException',
    'TTSAdapter',
    'TTSRequest',
    'TTSResponse',
    'TextGenerationAdapter',
    'TextGenerationRequest',
    'TextGenerationResponse',
    'dispatch_text_generation',
    'dispatch_tts',
    'has_tts_adapter',
]
