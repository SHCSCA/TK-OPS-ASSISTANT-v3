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


class SubtitleTrackGenerateInput(BaseModel):
    sourceText: str
    language: str = "zh-CN"
    stylePreset: str = "creator-default"


class SubtitleTrackUpdateInput(BaseModel):
    segments: list[SubtitleSegmentDto]
    style: SubtitleStyleDto


class SubtitleTrackGenerateResultDto(BaseModel):
    track: SubtitleTrackDto
    task: dict[str, object] | None = None
    message: str
