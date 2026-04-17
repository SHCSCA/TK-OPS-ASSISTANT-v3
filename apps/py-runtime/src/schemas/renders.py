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


class ExportProfileCreateInput(BaseModel):
    name: str
    format: str = "mp4"
    resolution: str = "1080x1920"
    fps: int = 30
    video_bitrate: str = "8000k"
    audio_policy: str = "merge_all"
    subtitle_policy: str = "burn_in"
    config_json: str | None = None


class ExportProfileDto(BaseModel):
    id: str
    name: str
    format: str
    resolution: str
    fps: int
    video_bitrate: str
    audio_policy: str
    subtitle_policy: str
    config_json: str | None = None
    is_default: bool
    created_at: datetime
    updated_at: datetime
