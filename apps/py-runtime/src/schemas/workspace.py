from __future__ import annotations

from pydantic import BaseModel, Field


class TimelineResolutionDto(BaseModel):
    width: int = Field(ge=1)
    height: int = Field(ge=1)


class TimelineClipDto(BaseModel):
    id: str
    trackId: str
    sourceType: str
    sourceId: str | None = None
    label: str
    startMs: int = Field(ge=0)
    durationMs: int = Field(ge=0)
    inPointMs: int = Field(default=0, ge=0)
    outPointMs: int | None = Field(default=None, ge=0)
    status: str = "ready"
    prompt: str | None = None
    resolution: TimelineResolutionDto | None = None
    editableFields: list[str] = Field(default_factory=list)


class TimelineTrackDto(BaseModel):
    id: str
    kind: str
    name: str
    orderIndex: int
    locked: bool = False
    muted: bool = False
    clips: list[TimelineClipDto] = Field(default_factory=list)


class TimelineVersionDto(BaseModel):
    versionToken: str
    updatedAt: str
    trackCount: int = Field(default=0, ge=0)
    clipCount: int = Field(default=0, ge=0)


class AssetReferenceStatusDto(BaseModel):
    totalClips: int = Field(default=0, ge=0)
    readyClips: int = Field(default=0, ge=0)
    processingClips: int = Field(default=0, ge=0)
    failedClips: int = Field(default=0, ge=0)
    missingReferenceClips: int = Field(default=0, ge=0)
    manualClips: int = Field(default=0, ge=0)
    referencedClips: int = Field(default=0, ge=0)


class WorkspaceActiveTaskDto(BaseModel):
    id: str
    taskType: str
    status: str
    progress: int = Field(ge=0, le=100)
    message: str
    updatedAt: str


class WorkspaceSaveStateDto(BaseModel):
    saved: bool
    updatedAt: str
    source: str
    message: str


class TimelineDto(BaseModel):
    id: str
    projectId: str
    name: str
    status: str
    durationSeconds: float | None = None
    source: str
    tracks: list[TimelineTrackDto]
    createdAt: str
    updatedAt: str
    version: TimelineVersionDto | None = None
    assetReferenceStatus: AssetReferenceStatusDto | None = None


class TimelineCreateInput(BaseModel):
    name: str = "主时间线"


class TimelineUpdateInput(BaseModel):
    name: str | None = None
    durationSeconds: float | None = Field(default=None, ge=0)
    tracks: list[TimelineTrackDto]


class WorkspaceTimelineResultDto(BaseModel):
    timeline: TimelineDto | None = None
    activeTask: WorkspaceActiveTaskDto | None = None
    saveState: WorkspaceSaveStateDto | None = None
    message: str


class WorkspaceClipDetailDto(BaseModel):
    id: str
    timelineId: str
    trackId: str
    trackKind: str
    trackName: str
    sourceType: str
    sourceId: str | None = None
    label: str
    prompt: str | None = None
    resolution: TimelineResolutionDto | None = None
    editableFields: list[str] = Field(default_factory=list)
    startMs: int = Field(ge=0)
    durationMs: int = Field(ge=0)
    inPointMs: int = Field(default=0, ge=0)
    outPointMs: int | None = Field(default=None, ge=0)
    status: str = "ready"


class ClipMoveInput(BaseModel):
    targetTrackId: str
    startMs: int = Field(ge=0)


class ClipTrimInput(BaseModel):
    startMs: int | None = Field(default=None, ge=0)
    durationMs: int | None = Field(default=None, ge=0)
    inPointMs: int | None = Field(default=None, ge=0)
    outPointMs: int | None = Field(default=None, ge=0)


class ClipReplaceInput(BaseModel):
    sourceType: str
    sourceId: str | None = None
    label: str
    prompt: str | None = None
    resolution: TimelineResolutionDto | None = None
    editableFields: list[str] = Field(default_factory=list)


class TimelinePreviewDto(BaseModel):
    timelineId: str
    status: str
    message: str
    previewUrl: str | None = None


class TimelinePrecheckDto(BaseModel):
    timelineId: str
    status: str
    message: str
    issues: list[str] = Field(default_factory=list)


class WorkspaceAICommandInput(BaseModel):
    timelineId: str | None = None
    capabilityId: str
    parameters: dict[str, object] = Field(default_factory=dict)


class WorkspaceAICommandResultDto(BaseModel):
    status: str
    task: dict[str, object] | None = None
    message: str
