from __future__ import annotations

from pydantic import BaseModel, Field

from schemas.tasks import TaskStatus


class AIJobRecordDto(BaseModel):
    id: str
    capabilityId: str
    provider: str
    model: str
    status: TaskStatus
    error: str | None
    durationMs: int | None
    createdAt: str
    completedAt: str | None


class ScriptSaveInput(BaseModel):
    content: str = Field(min_length=1)


class ScriptGenerateInput(BaseModel):
    topic: str = Field(min_length=1)


class ScriptRewriteInput(BaseModel):
    instructions: str = Field(min_length=1)


class ScriptTitleVariantsInput(BaseModel):
    topic: str = Field(min_length=1)
    count: int = Field(ge=1, le=10)


class ScriptSegmentRewriteInput(BaseModel):
    instructions: str = Field(min_length=1)
    promptTemplateId: str | None = None


class ScriptTitleVariantDto(BaseModel):
    title: str


class ScriptVersionDto(BaseModel):
    revision: int
    source: str
    content: str
    provider: str | None = None
    model: str | None = None
    aiJobId: str | None = None
    createdAt: str


class ScriptLastOperationDto(BaseModel):
    revision: int
    source: str
    createdAt: str
    aiJobId: str | None = None
    aiJobStatus: TaskStatus | None = None


class ScriptDocumentDto(BaseModel):
    projectId: str
    currentVersion: ScriptVersionDto | None
    versions: list[ScriptVersionDto]
    recentJobs: list[AIJobRecordDto]
    isSaved: bool = False
    latestRevision: int | None = None
    saveSource: str | None = None
    latestAiJob: AIJobRecordDto | None = None
    lastOperation: ScriptLastOperationDto | None = None
