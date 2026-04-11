from __future__ import annotations

from pydantic import BaseModel, Field

from schemas.scripts import AIJobRecordDto


class StoryboardSceneDto(BaseModel):
    sceneId: str
    title: str
    summary: str
    visualPrompt: str


class StoryboardSaveInput(BaseModel):
    basedOnScriptRevision: int = Field(ge=1)
    scenes: list[StoryboardSceneDto] = Field(min_length=1)


class StoryboardVersionDto(BaseModel):
    revision: int
    basedOnScriptRevision: int
    source: str
    scenes: list[StoryboardSceneDto]
    provider: str | None = None
    model: str | None = None
    aiJobId: str | None = None
    createdAt: str


class StoryboardDocumentDto(BaseModel):
    projectId: str
    basedOnScriptRevision: int
    currentVersion: StoryboardVersionDto | None
    versions: list[StoryboardVersionDto]
    recentJobs: list[AIJobRecordDto]
