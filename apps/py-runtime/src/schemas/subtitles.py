from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class SubtitleStyleDto(BaseModel):
    preset: str = "creator-default"
    fontSize: int = Field(default=32, ge=18, le=72)
    position: Literal["bottom", "center", "top"] = "bottom"
    textColor: str = "#FFFFFF"
    background: str = "rgba(0,0,0,0.62)"


class SubtitleSegmentDto(BaseModel):
    segmentIndex: int
    text: str
    startMs: int | None = None
    endMs: int | None = None
    confidence: float | None = None
    locked: bool = False


class SubtitleSourceVoiceDto(BaseModel):
    trackId: str
    revision: int
    updatedAt: str


class SubtitleAlignmentDiffSummaryDto(BaseModel):
    segmentCountChanged: bool
    timingChangedSegments: int
    textChangedSegments: int
    lockedSegments: int


class SubtitleAlignmentDto(BaseModel):
    status: str
    diffSummary: SubtitleAlignmentDiffSummaryDto | None = None
    errorCode: str | None = None
    errorMessage: str | None = None
    nextAction: str | None = None
    updatedAt: str


class SubtitleTrackDto(BaseModel):
    id: str
    projectId: str
    timelineId: str | None = None
    source: str
    language: str
    style: SubtitleStyleDto
    segments: list[SubtitleSegmentDto]
    status: str
    createdAt: str
    updatedAt: str
    sourceVoice: SubtitleSourceVoiceDto | None = None
    alignment: SubtitleAlignmentDto


class SubtitleTrackGenerateInput(BaseModel):
    sourceText: str
    language: str = "zh-CN"
    stylePreset: str = "creator-default"
    sourceVoiceTrackId: str | None = None


class SubtitleTrackUpdateInput(BaseModel):
    segments: list[SubtitleSegmentDto]
    style: SubtitleStyleDto


class SubtitleTrackAlignInput(BaseModel):
    segments: list[SubtitleSegmentDto]


class SubtitleStyleTemplateDto(BaseModel):
    id: str
    name: str
    description: str
    style: SubtitleStyleDto


class SubtitleExportInput(BaseModel):
    format: Literal["srt", "vtt", "ass"] = "srt"


class SubtitleExportDto(BaseModel):
    trackId: str
    format: Literal["srt", "vtt", "ass"]
    fileName: str
    content: str
    lineCount: int
    status: str
    message: str


class SubtitleTrackGenerateResultDto(BaseModel):
    track: SubtitleTrackDto
    task: dict[str, object] | None = None
    message: str
