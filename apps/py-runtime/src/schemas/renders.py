from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class RenderTaskCreateInput(BaseModel):
    project_id: str | None = None
    project_name: str | None = None
    preset: str = "1080p"
    format: str = "mp4"


class RenderTaskUpdateInput(BaseModel):
    preset: str | None = None
    format: str | None = None
    status: str | None = None
    progress: int | None = None
    output_path: str | None = None
    error_message: str | None = None


class RenderTaskDto(BaseModel):
    id: str
    project_id: str | None = None
    project_name: str | None = None
    preset: str
    format: str
    status: str
    progress: int
    output_path: str | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class CancelRenderResultDto(BaseModel):
    task_id: str
    status: str
    message: str
