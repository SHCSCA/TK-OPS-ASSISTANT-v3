from __future__ import annotations

from pydantic import BaseModel, Field


class VoiceProfileDto(BaseModel):
    id: str
    provider: str
    voiceId: str
    displayName: str
    locale: str
    tags: list[str]
    enabled: bool


class VoiceProfileCreateInput(BaseModel):
    provider: str
    voiceId: str
    displayName: str
    locale: str
    tags: list[str] = Field(default_factory=list)
    enabled: bool = True


class VoiceSegmentRegenerateInput(BaseModel):
    profileId: str | None = None
    speed: float = Field(default=1.0, ge=0.5, le=2.0)
    pitch: int = Field(default=0, ge=-50, le=50)
    emotion: str = "calm"


class VoiceWaveformPointDto(BaseModel):
    timeMs: int
    amplitude: float


class VoiceWaveformDto(BaseModel):
    status: str
    message: str
    durationMs: int | None = None
    sampleRate: int | None = None
    channels: int | None = None
    points: list[VoiceWaveformPointDto] = Field(default_factory=list)


class VoiceTrackSegmentDto(BaseModel):
    segmentIndex: int
    text: str
    startMs: int | None = None
    endMs: int | None = None
    audioAssetId: str | None = None
    regeneration: dict[str, object] | None = None


class VoiceTrackDto(BaseModel):
    id: str
    projectId: str
    timelineId: str | None = None
    source: str
    provider: str | None = None
    voiceName: str
    filePath: str | None = None
    segments: list[VoiceTrackSegmentDto]
    status: str
    createdAt: str


class VoiceTrackGenerateInput(BaseModel):
    profileId: str
    sourceText: str
    speed: float = Field(default=1.0, ge=0.5, le=2.0)
    pitch: int = Field(default=0, ge=-50, le=50)
    emotion: str = "calm"


class VoiceTrackGenerateResultDto(BaseModel):
    track: VoiceTrackDto
    task: dict[str, object] | None = None
    message: str


class VoiceTrackRegenerateResultDto(BaseModel):
    track: VoiceTrackDto
    task: dict[str, object] | None = None
    message: str
