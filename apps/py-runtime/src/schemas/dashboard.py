from __future__ import annotations

from pydantic import BaseModel, Field


class CreateProjectInput(BaseModel):
    name: str = Field(min_length=1)
    description: str = ''


class ProjectSummaryDto(BaseModel):
    id: str
    name: str
    description: str
    status: str
    currentScriptVersion: int
    currentStoryboardVersion: int
    createdAt: str
    updatedAt: str
    lastAccessedAt: str


class CurrentProjectContextDto(BaseModel):
    projectId: str
    projectName: str
    status: str


class DashboardTaskDto(BaseModel):
    taskId: str
    taskType: str
    projectId: str | None = None
    status: str
    progress: int
    message: str
    createdAt: str
    updatedAt: str


class DashboardPendingItemDto(BaseModel):
    id: str
    kind: str
    title: str
    detail: str
    action: str
    targetProjectId: str | None = None
    targetTaskId: str | None = None


class DashboardRiskItemDto(BaseModel):
    id: str
    level: str
    title: str
    detail: str
    targetProjectId: str | None = None
    targetTaskId: str | None = None


class DashboardRiskSummaryDto(BaseModel):
    total: int
    blocking: int
    items: list[DashboardRiskItemDto]


class DashboardCurrentActionDto(BaseModel):
    label: str
    action: str
    targetProjectId: str | None = None
    targetTaskId: str | None = None


class SetCurrentProjectInput(BaseModel):
    projectId: str = Field(min_length=1)


class DashboardSummaryDto(BaseModel):
    recentProjects: list[ProjectSummaryDto]
    currentProject: CurrentProjectContextDto | None
    recentTasks: list[DashboardTaskDto]
    pendingItems: list[DashboardPendingItemDto]
    riskSummary: DashboardRiskSummaryDto
    currentAction: DashboardCurrentActionDto | None = None
    generatedAt: str


class DeleteProjectResultDto(BaseModel):
    deleted: bool
    projectId: str
    clearedCurrentProject: bool
    deletedAt: str
