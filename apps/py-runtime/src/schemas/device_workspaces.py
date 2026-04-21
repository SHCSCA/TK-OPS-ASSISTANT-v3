from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class DeviceWorkspaceCreateInput(BaseModel):
    name: str
    root_path: str


class DeviceWorkspaceUpdateInput(BaseModel):
    name: str | None = None
    root_path: str | None = None
    status: str | None = None


class DeviceWorkspaceEnvironmentStatusDto(BaseModel):
    status: str
    rootPathExists: bool
    isDirectory: bool
    browserInstanceCount: int
    runningBrowserInstanceCount: int
    errorCode: str | None = None
    errorMessage: str | None = None
    nextAction: str | None = None


class DeviceWorkspaceBindingSummaryDto(BaseModel):
    totalBindings: int
    activeBindings: int
    accountIds: list[str]


class DeviceWorkspaceHealthSummaryDto(BaseModel):
    status: str
    checkedAt: datetime | None = None
    errorCode: str | None = None
    errorMessage: str | None = None
    nextAction: str | None = None


class DeviceWorkspaceDto(BaseModel):
    id: str
    name: str
    root_path: str
    status: str
    error_count: int
    last_used_at: datetime | None = None
    environmentStatus: DeviceWorkspaceEnvironmentStatusDto
    bindingSummary: DeviceWorkspaceBindingSummaryDto
    healthSummary: DeviceWorkspaceHealthSummaryDto
    created_at: datetime
    updated_at: datetime


class HealthCheckResultDto(BaseModel):
    workspace_id: str
    status: str
    checked_at: datetime
    errorCode: str | None = None
    errorMessage: str | None = None
    nextAction: str | None = None
    environmentStatus: DeviceWorkspaceEnvironmentStatusDto
    bindingSummary: DeviceWorkspaceBindingSummaryDto


class DeviceWorkspaceLogDto(BaseModel):
    id: str
    workspaceId: str
    kind: str
    level: str
    message: str
    contextJson: str | None = None
    createdAt: datetime


class BrowserInstanceCreateInput(BaseModel):
    name: str
    profilePath: str


class BrowserInstanceDto(BaseModel):
    id: str
    workspaceId: str
    name: str
    profilePath: str
    status: str
    lastCheckedAt: datetime | None = None
    lastStartedAt: datetime | None = None
    lastStoppedAt: datetime | None = None
    errorCode: str | None = None
    errorMessage: str | None = None
    createdAt: datetime
    updatedAt: datetime


class BrowserInstanceWriteResultDto(BaseModel):
    saved: bool
    updatedAt: str
    versionOrRevision: str
    objectSummary: dict[str, str]
    browserInstance: BrowserInstanceDto
