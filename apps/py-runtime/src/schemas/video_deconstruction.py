from __future__ import annotations

from pydantic import BaseModel, Field


class ImportVideoInput(BaseModel):
    filePath: str


class ImportedVideoDto(BaseModel):
    id: str
    projectId: str
    filePath: str
    fileName: str
    fileSizeBytes: int
    durationSeconds: float | None = None
    width: int | None = None
    height: int | None = None
    frameRate: float | None = None
    codec: str | None = None
    status: str
    errorMessage: str | None = None
    createdAt: str


class VideoStageDto(BaseModel):
    stageId: str
    label: str
    status: str
    progressPct: int
    resultSummary: str | None = None
    errorMessage: str | None = None
    errorCode: str | None = None
    nextAction: str | None = None
    blockedByStageId: str | None = None
    updatedAt: str | None = None
    isCurrent: bool = False
    activeTaskId: str | None = None
    activeTaskStatus: str | None = None
    activeTaskProgress: int | None = None
    activeTaskMessage: str | None = None
    canCancel: bool = False
    canRetry: bool = False
    canRerun: bool


class VideoTranscriptDto(BaseModel):
    id: str
    videoId: str
    language: str | None = None
    text: str | None = None
    status: str
    createdAt: str
    updatedAt: str


class VideoSegmentDto(BaseModel):
    id: str
    videoId: str
    segmentIndex: int
    startMs: int
    endMs: int
    label: str | None = None
    transcriptText: str | None = None
    metadataJson: str | None = None
    createdAt: str


class VideoStructureExtractionDto(BaseModel):
    id: str
    videoId: str
    status: str
    scriptJson: str | None = None
    storyboardJson: str | None = None
    createdAt: str
    updatedAt: str


class VideoScriptLineDto(BaseModel):
    startMs: int
    endMs: int
    text: str
    type: str = "speech"


class VideoScriptResultDto(BaseModel):
    title: str
    language: str
    fullText: str
    lines: list[VideoScriptLineDto] = Field(default_factory=list)


class VideoKeyframeDto(BaseModel):
    index: int
    startMs: int
    endMs: int
    visual: str
    speech: str
    onscreenText: str
    shotType: str
    camera: str
    intent: str


class VideoContentStructureDto(BaseModel):
    topic: str
    hook: str
    painPoints: list[str] = Field(default_factory=list)
    sellingPoints: list[str] = Field(default_factory=list)
    rhythm: list[str] = Field(default_factory=list)
    cta: str
    reusableForScript: list[str] = Field(default_factory=list)
    reusableForStoryboard: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)


class VideoResultSourceDto(BaseModel):
    provider: str
    model: str
    promptVersion: str


class VideoDeconstructionResultDto(BaseModel):
    videoId: str
    transcript: VideoTranscriptDto
    segments: list[VideoSegmentDto]
    structure: VideoStructureExtractionDto
    stages: list[VideoStageDto]
    script: VideoScriptResultDto
    keyframes: list[VideoKeyframeDto]
    contentStructure: VideoContentStructureDto
    source: VideoResultSourceDto


class ApplyVideoExtractionResultDto(BaseModel):
    projectId: str
    extractionId: str
    scriptRevision: int
    status: str
    message: str
