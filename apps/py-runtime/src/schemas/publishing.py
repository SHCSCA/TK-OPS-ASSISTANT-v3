from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class PublishPlanCreateInput(BaseModel):
    title: str
    account_id: str | None = None
    account_name: str | None = None
    project_id: str | None = None
    video_asset_id: str | None = None
    scheduled_at: datetime | None = None


class PublishPlanUpdateInput(BaseModel):
    title: str | None = None
    account_name: str | None = None
    status: str | None = None
    scheduled_at: datetime | None = None


class PublishPlanDto(BaseModel):
    id: str
    title: str
    account_id: str | None = None
    account_name: str | None = None
    project_id: str | None = None
    video_asset_id: str | None = None
    status: str
    scheduled_at: datetime | None = None
    submitted_at: datetime | None = None
    published_at: datetime | None = None
    error_message: str | None = None
    precheck_result_json: str | None = None
    created_at: datetime
    updated_at: datetime


class PrecheckItemResult(BaseModel):
    code: str
    label: str
    result: str
    message: str | None = None


class PrecheckConflictDto(BaseModel):
    conflicting_plan_id: str
    conflicting_title: str
    conflicting_scheduled_at: datetime | None = None
    reason: str


class PrecheckResultDto(BaseModel):
    plan_id: str
    items: list[PrecheckItemResult]
    conflicts: list[PrecheckConflictDto] = Field(default_factory=list)
    has_errors: bool
    checked_at: datetime


class SubmitPlanResultDto(BaseModel):
    plan_id: str
    status: str
    submitted_at: datetime
    message: str


class PublishReceiptDto(BaseModel):
    id: str
    plan_id: str
    status: str
    platform_response_json: str | None = None
    received_at: datetime
    created_at: datetime


class PublishCalendarItemDto(BaseModel):
    plan_id: str
    title: str
    status: str
    scheduled_at: datetime | None = None
    account_name: str | None = None
    conflict_count: int = 0


class PublishCalendarDto(BaseModel):
    items: list[PublishCalendarItemDto]
    generated_at: datetime
