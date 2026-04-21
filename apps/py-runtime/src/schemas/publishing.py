from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class PublishSuggestedActionDto(BaseModel):
    key: str
    label: str


class PublishBindingSummaryDto(BaseModel):
    binding_id: str | None = None
    workspace_id: str | None = None
    workspace_name: str | None = None
    workspace_status: str | None = None
    root_path: str | None = None
    updated_at: datetime | None = None


class PublishPlanPrecheckSummaryDto(BaseModel):
    status: str
    checked_at: datetime | None = None
    blocking_count: int = 0


class PublishPlanLatestReceiptDto(BaseModel):
    id: str
    status: str
    stage: str
    summary: str
    error_code: str | None = None
    error_message: str | None = None
    next_action: PublishSuggestedActionDto | None = None
    received_at: datetime
    is_final: bool


class PublishPlanReadinessDto(BaseModel):
    can_submit: bool
    status: str
    error_code: str | None = None
    error_message: str | None = None
    next_action: PublishSuggestedActionDto | None = None
    binding: PublishBindingSummaryDto | None = None


class PublishPlanRecoveryDto(BaseModel):
    can_retry: bool
    can_cancel: bool
    next_action: PublishSuggestedActionDto | None = None


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
    precheck_summary: PublishPlanPrecheckSummaryDto
    latest_receipt: PublishPlanLatestReceiptDto | None = None
    publish_readiness: PublishPlanReadinessDto
    recovery: PublishPlanRecoveryDto
    created_at: datetime
    updated_at: datetime


class PrecheckItemResult(BaseModel):
    code: str
    label: str
    result: str
    message: str | None = None
    error_code: str | None = None
    affected_target: str | None = None
    next_action: PublishSuggestedActionDto | None = None


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
    blocking_count: int = 0
    readiness: PublishPlanReadinessDto


class SubmitPlanResultDto(BaseModel):
    plan_id: str
    status: str
    submitted_at: datetime
    message: str
    receipt_status: str
    error_code: str | None = None
    error_message: str | None = None
    next_action: PublishSuggestedActionDto | None = None
    receipt: PublishPlanLatestReceiptDto | None = None


class PublishReceiptDto(BaseModel):
    id: str
    plan_id: str
    status: str
    stage: str
    summary: str
    error_code: str | None = None
    error_message: str | None = None
    next_action: PublishSuggestedActionDto | None = None
    is_final: bool
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
