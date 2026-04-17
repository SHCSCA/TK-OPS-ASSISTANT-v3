from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


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


class VideoTranscriptDto(BaseModel):
    id: str
    videoId: str
    language: str | None = None
    text: str | None = None
    status: str
    createdAt: datetime
    updatedAt: datetime


class VideoSegmentDto(BaseModel):
    id: str
    videoId: str
    segmentIndex: int
    startMs: int
    endMs: int
    label: str | None = None
    transcriptText: str | None = None
    metadataJson: str | None = None
    createdAt: datetime


class VideoStructureExtractionDto(BaseModel):
    id: str
    videoId: str
    status: str
    scriptJson: str | None = None
    storyboardJson: str | None = None
    createdAt: datetime
    updatedAt: datetime


class ApplyVideoExtractionResultDto(BaseModel):
    projectId: str
    extractionId: str
    scriptRevision: int
    status: str
    message: str
