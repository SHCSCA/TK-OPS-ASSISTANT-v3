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


class SetCurrentProjectInput(BaseModel):
    projectId: str = Field(min_length=1)


class DashboardSummaryDto(BaseModel):
    recentProjects: list[ProjectSummaryDto]
    currentProject: CurrentProjectContextDto | None
