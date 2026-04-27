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


class VoiceProfileRefreshResultDto(BaseModel):
    provider: str
    status: str
    message: str
    savedCount: int
    profiles: list[VoiceProfileDto]


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


class VoiceTrackVoiceConfigDto(BaseModel):
    parameterSource: str
    profileId: str | None = None
    provider: str | None = None
    voiceId: str | None = None
    voiceName: str | None = None
    locale: str | None = None
    model: str | None = None
    speed: float | None = None
    pitch: int | None = None
    emotion: str | None = None
    sourceText: str | None = None
    sourceLineCount: int | None = None
    lastOperation: dict[str, object] | None = None


class VoiceTrackTaskDto(BaseModel):
    id: str
    kind: str
    taskType: str
    projectId: str | None = None
    ownerRef: dict[str, object] | None = None
    label: str | None = None
    message: str
    status: str
    progress: int
    createdAt: str
    updatedAt: str


class VoiceTrackVersionDto(BaseModel):
    revision: int
    updatedAt: str


class VoiceTrackPreviewDto(BaseModel):
    status: str
    resourceId: str | None = None
    filePath: str | None = None
    message: str


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
    version: VoiceTrackVersionDto
    config: VoiceTrackVoiceConfigDto
    preview: VoiceTrackPreviewDto
    activeTask: VoiceTrackTaskDto | None = None
    createdAt: str
    updatedAt: str


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
