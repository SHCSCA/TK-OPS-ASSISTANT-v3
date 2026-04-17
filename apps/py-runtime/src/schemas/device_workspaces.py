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


class DeviceWorkspaceDto(BaseModel):
    id: str
    name: str
    root_path: str
    status: str
    error_count: int
    last_used_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class HealthCheckResultDto(BaseModel):
    workspace_id: str
    status: str
    checked_at: datetime


class DeviceWorkspaceLogDto(BaseModel):
    id: str
    workspaceId: str
    kind: str
    level: str
    message: str
    contextJson: str | None = None
    createdAt: datetime
