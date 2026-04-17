from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ReviewSuggestion(BaseModel):
    id: str
    code: str
    category: str
    title: str
    description: str
    priority: str
    status: str
    actionLabel: str
    sourceType: str | None = None
    sourceId: str | None = None
    createdAt: datetime


class ReviewSummaryUpdateInput(BaseModel):
    project_name: str | None = None
    total_views: int | None = None
    total_likes: int | None = None
    total_comments: int | None = None
    avg_watch_time_sec: float | None = None
    completion_rate: float | None = None


class ReviewSummaryDto(BaseModel):
    id: str
    project_id: str
    project_name: str | None = None
    total_views: int
    total_likes: int
    total_comments: int
    avg_watch_time_sec: float
    completion_rate: float
    suggestions: list[ReviewSuggestion]
    last_analyzed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class AnalyzeProjectResultDto(BaseModel):
    project_id: str
    status: str
    message: str
    analyzed_at: datetime


class ReviewSuggestionUpdateInput(BaseModel):
    status: str


class GenerateReviewSuggestionsResultDto(BaseModel):
    project_id: str
    status: str
    message: str
    generated_count: int
    generated_at: datetime


class ApplyReviewSuggestionResultDto(BaseModel):
    project_id: str
    suggestion_id: str
    script_revision: int
    status: str
    message: str
