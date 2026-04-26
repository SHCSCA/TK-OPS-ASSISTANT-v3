from __future__ import annotations

from dataclasses import dataclass

import pytest

from services.ai_capability_service import ProviderRuntimeConfig
from services.video_transcription_service import (
    VideoTranscriptionConfigurationError,
    VideoTranscriptionService,
)


@dataclass(frozen=True, slots=True)
class _Capability:
    enabled: bool
    provider: str
    model: str


class _CapabilityService:
    def __init__(self, capability: _Capability, runtime: ProviderRuntimeConfig) -> None:
        self._capability = capability
        self._runtime = runtime

    def get_capability(self, capability_id: str) -> _Capability:
        assert capability_id == "video_transcription"
        return self._capability

    def get_provider_runtime_config(self, provider_id: str) -> ProviderRuntimeConfig:
        assert provider_id == self._runtime.provider
        return self._runtime

    def resolve_provider_model_id(
        self,
        provider_id: str,
        model_id: str,
        *,
        capability_id: str | None = None,
        required_capability_type: str | None = None,
    ) -> str:
        assert provider_id == self._capability.provider
        assert capability_id == "video_transcription"
        assert required_capability_type == "speech_to_text"
        return model_id


class _UnexpectedSpeechProvider:
    def transcribe(self, **_: object) -> object:
        raise AssertionError("不应调用未接入协议的转录 Provider")


def test_video_transcription_rejects_unimplemented_domestic_asr_protocol(tmp_path) -> None:
    media_file = tmp_path / "clip.mp4"
    media_file.write_bytes(b"fake video")
    runtime = ProviderRuntimeConfig(
        provider="volcengine_asr",
        label="火山语音识别",
        api_key="sk-test",
        base_url="https://example.test/asr",
        secret_source="secure_store",
        requires_secret=True,
        supports_text_generation=False,
        supports_tts=False,
        supports_speech_to_text=True,
        protocol_family="domestic_asr",
    )
    service = VideoTranscriptionService(
        capability_service=_CapabilityService(
            _Capability(enabled=True, provider="volcengine_asr", model="volcengine-asr"),
            runtime,
        ),
        provider=_UnexpectedSpeechProvider(),
    )

    with pytest.raises(VideoTranscriptionConfigurationError) as exc_info:
        service.transcribe_file(str(media_file))

    assert "真实转录协议尚未接入" in str(exc_info.value)
