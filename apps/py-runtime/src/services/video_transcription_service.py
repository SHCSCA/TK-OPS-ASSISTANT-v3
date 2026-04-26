from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from ai.providers.speech_to_text_openai import (
    OpenAICompatibleSpeechToTextProvider,
    SpeechToTextProviderError,
)
from services.ai_capability_service import AICapabilityService

log = logging.getLogger(__name__)

CAPABILITY_ID = "video_transcription"
PROVIDER_REQUIRED_MESSAGE = "当前未配置可用视频解析模型，视频解析已阻塞；请在 AI 与系统设置中配置支持视频输入的多模态模型后重试。"
OPENAI_AUDIO_TRANSCRIPTION_PROVIDERS = frozenset({"openai", "openai_compatible", "custom_transcription_provider"})


@dataclass(frozen=True, slots=True)
class VideoTranscriptionResult:
    text: str
    language: str | None
    provider: str
    model: str


class VideoTranscriptionConfigurationError(RuntimeError):
    pass


class VideoTranscriptionExecutionError(RuntimeError):
    pass


class VideoTranscriptionService:
    def __init__(
        self,
        *,
        capability_service: AICapabilityService,
        provider: OpenAICompatibleSpeechToTextProvider | None = None,
    ) -> None:
        self._capability_service = capability_service
        self._provider = provider or OpenAICompatibleSpeechToTextProvider()

    def transcribe_file(self, file_path: str) -> VideoTranscriptionResult:
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"媒体文件不存在：{file_path}")

        capability = self._capability_service.get_capability(CAPABILITY_ID)
        if not capability.enabled:
            raise VideoTranscriptionConfigurationError(PROVIDER_REQUIRED_MESSAGE)

        runtime = self._capability_service.get_provider_runtime_config(capability.provider)
        if not runtime.supports_speech_to_text:
            raise VideoTranscriptionConfigurationError("当前 Provider 不支持视频转录/语音识别能力，请切换到支持 speech_to_text 的 Provider。")
        if not is_supported_transcription_runtime(runtime.provider, runtime.protocol_family):
            log.warning(
                "视频转录 Provider 协议暂未接入 provider=%s protocol=%s",
                runtime.provider,
                runtime.protocol_family,
            )
            raise VideoTranscriptionConfigurationError(
                "当前视频转录 Provider 已可配置，但该 Provider 的真实转录协议尚未接入；请先使用 OpenAI、OpenAI-compatible 或自定义转录 Provider。"
            )
        if runtime.requires_secret and not runtime.api_key:
            raise VideoTranscriptionConfigurationError("当前视频转录 Provider 尚未配置 API Key。")
        if runtime.base_url.strip() == "":
            raise VideoTranscriptionConfigurationError("当前视频转录 Provider 尚未配置 Base URL。")

        model = self._capability_service.resolve_provider_model_id(
            capability.provider,
            capability.model,
            capability_id=CAPABILITY_ID,
            required_capability_type="speech_to_text",
        )
        if model.strip() == "":
            raise VideoTranscriptionConfigurationError("当前视频转录能力尚未配置模型。")

        try:
            result = self._provider.transcribe(
                file_path=str(path),
                base_url=runtime.base_url,
                api_key=runtime.api_key,
                model=model,
            )
        except SpeechToTextProviderError as exc:
            log.exception("视频转录 Provider 执行失败 file=%s provider=%s model=%s", file_path, capability.provider, model)
            raise VideoTranscriptionExecutionError(str(exc)) from exc

        return VideoTranscriptionResult(
            text=result.text,
            language=result.language,
            provider=capability.provider,
            model=model,
        )


def is_supported_transcription_runtime(provider: str, protocol_family: str) -> bool:
    return provider in OPENAI_AUDIO_TRANSCRIPTION_PROVIDERS or protocol_family == "openai_audio_transcriptions"
