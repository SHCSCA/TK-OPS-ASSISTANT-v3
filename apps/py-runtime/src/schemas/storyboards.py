from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from schemas.scripts import AIJobRecordDto
from schemas.tasks import TaskStatus


class StoryboardShotDto(BaseModel):
    sceneId: str
    title: str
    summary: str
    visualPrompt: str
    action: str | None = None
    audio: str | None = None
    cameraAngle: str | None = None
    cameraMovement: str | None = None
    shootingNote: str | None = None
    shotLabel: str | None = None
    shotSize: str | None = None
    subtitle: str | None = None
    time: str | None = None
    transition: str | None = None
    visualContent: str | None = None
    voiceover: str | None = None


class StoryboardSceneDto(BaseModel):
    sceneId: str
    title: str
    summary: str
    visualPrompt: str
    action: str | None = None
    audio: str | None = None
    cameraAngle: str | None = None
    cameraMovement: str | None = None
    shootingNote: str | None = None
    shotLabel: str | None = None
    shotSize: str | None = None
    subtitle: str | None = None
    time: str | None = None
    transition: str | None = None
    visualContent: str | None = None
    voiceover: str | None = None


class StoryboardShotInput(BaseModel):
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    visualPrompt: str = Field(min_length=1)


class StoryboardShotUpdateInput(BaseModel):
    title: str | None = None
    summary: str | None = None
    visualPrompt: str | None = None


class StoryboardSaveInput(BaseModel):
    basedOnScriptRevision: int = Field(ge=1)
    scenes: list[StoryboardSceneDto] = Field(default_factory=list)
    markdown: str | None = None
    storyboardJson: dict[str, Any] | None = None

    @model_validator(mode='after')
    def require_storyboard_content(self) -> 'StoryboardSaveInput':
        if not self.scenes and not (self.markdown or '').strip() and self.storyboardJson is None:
            raise ValueError('请提供分镜结构化 JSON、原文或至少一个结构化分镜。')
        return self


class StoryboardVersionDto(BaseModel):
    revision: int
    basedOnScriptRevision: int
    source: str
    scenes: list[StoryboardSceneDto]
    markdown: str | None = None
    format: Literal["json_v1", "legacy_markdown"] = "legacy_markdown"
    storyboardJson: dict[str, Any] | None = None
    provider: str | None = None
    model: str | None = None
    aiJobId: str | None = None
    createdAt: str


class StoryboardConflictSummaryDto(BaseModel):
    hasConflict: bool
    reason: str | None = None
    currentScriptRevision: int
    basedOnScriptRevision: int | None = None
    storyboardRevision: int | None = None


class StoryboardLastOperationDto(BaseModel):
    revision: int
    source: str
    createdAt: str
    aiJobId: str | None = None
    aiJobStatus: TaskStatus | None = None


class StoryboardDocumentDto(BaseModel):
    projectId: str
    basedOnScriptRevision: int
    currentScriptRevision: int
    currentVersion: StoryboardVersionDto | None
    versions: list[StoryboardVersionDto]
    recentJobs: list[AIJobRecordDto]
    syncStatus: str
    conflictSummary: StoryboardConflictSummaryDto
    latestAiJob: AIJobRecordDto | None = None
    lastOperation: StoryboardLastOperationDto | None = None


class StoryboardTemplateDto(BaseModel):
    id: str
    name: str
    description: str
    shots: list[StoryboardShotDto]
