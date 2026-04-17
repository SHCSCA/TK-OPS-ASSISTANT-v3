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


class BrowserInstanceCreateInput(BaseModel):
    workspace_id: str
    name: str
    profile_path: str
    browser_type: str


class BrowserInstanceDto(BaseModel):
    id: str
    workspace_id: str
    name: str
    profile_path: str
    browser_type: str
    status: str
    last_seen_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ExecutionBindingCreateInput(BaseModel):
    account_id: str
    device_workspace_id: str
    browser_instance_id: str | None = None
    source: str | None = None
    metadata_json: str | None = None


class ExecutionBindingDto(BaseModel):
    id: str
    account_id: str
    device_workspace_id: str
    browser_instance_id: str | None = None
    status: str
    source: str | None = None
    metadata_json: str | None = None
    created_at: datetime
    updated_at: datetime
