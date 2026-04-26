from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Mapping


@dataclass(frozen=True, slots=True)
class TextGenerationMediaInput:
    kind: str
    url: str
    mime_type: str | None = None
    fps: float | None = None
    filename: str | None = None


@dataclass(frozen=True, slots=True)
class TextGenerationRequest:
    model: str
    system_prompt: str = ""
    user_prompt: str = ""
    request_id: str | None = None
    temperature: float | None = None
    max_output_tokens: int | None = None
    timeout_seconds: float = 60.0
    headers: Mapping[str, str] = field(default_factory=dict)
    media_inputs: tuple[TextGenerationMediaInput, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class TextGenerationResponse:
    text: str
    provider: str | None = None
    model: str | None = None
    provider_request_id: str | None = None
    response_headers: dict[str, str] = field(default_factory=dict)
    finish_reason: str | None = None
    raw_response: object | None = None
    usage: Mapping[str, int] | None = None


@dataclass(frozen=True, slots=True)
class TTSRequest:
    text: str
    voice_id: str
    model: str
    output_format: str = "mp3"
    speed: float = 1.0
    request_id: str | None = None
    timeout_seconds: float = 60.0
    headers: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class TTSResponse:
    audio_bytes: bytes
    content_type: str = "audio/mpeg"
    duration_ms: int | None = None
    provider: str | None = None
    model: str | None = None
    provider_request_id: str | None = None
    response_headers: dict[str, str] = field(default_factory=dict)


class TextGenerationAdapter(ABC):
    @abstractmethod
    def generate(self, request: TextGenerationRequest) -> TextGenerationResponse:
        raise NotImplementedError


class TTSAdapter(ABC):
    @abstractmethod
    def synthesize(self, request: TTSRequest) -> TTSResponse:
        raise NotImplementedError
