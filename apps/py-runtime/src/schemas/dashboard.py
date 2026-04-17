from __future__ import annotations

from pydantic import BaseModel, Field


class CreateProjectInput(BaseModel):
    name: str = Field(min_length=1)
    description: str = ""


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


class SetCurrentProjectInput(BaseModel):
    projectId: str | None = None


class DashboardGreetingDto(BaseModel):
    title: str
    subtitle: str


class DashboardHeroProjectDto(BaseModel):
    id: str
    name: str
    status: str
    lastEditedAt: str


class DashboardHeroActionDto(BaseModel):
    label: str
    action: str
    targetProjectId: str | None


class DashboardHeroContextDto(BaseModel):
    currentProject: DashboardHeroProjectDto | None
    primaryAction: DashboardHeroActionDto
    pendingTasks: int
    blockingIssues: int


class DashboardTodoDto(BaseModel):
    id: str
    title: str
    status: str


class DashboardExceptionDto(BaseModel):
    id: str
    title: str
    level: str
    message: str


class DashboardHealthDto(BaseModel):
    runtimeStatus: str
    aiProviderStatus: str
    taskBusStatus: str


class DashboardSummaryDto(BaseModel):
    recentProjects: list[ProjectSummaryDto]
    currentProject: CurrentProjectContextDto | None
    greeting: DashboardGreetingDto
    heroContext: DashboardHeroContextDto
    todos: list[DashboardTodoDto]
    exceptions: list[DashboardExceptionDto]
    health: DashboardHealthDto
    generatedAt: str
