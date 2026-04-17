from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


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


class PrecheckResultDto(BaseModel):
    plan_id: str
    items: list[PrecheckItemResult]
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
    external_url: str | None = None
    error_message: str | None = None
    completed_at: datetime | None = None
    created_at: datetime
