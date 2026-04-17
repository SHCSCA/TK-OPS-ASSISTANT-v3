from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class AutomationTaskRuleInput(BaseModel):
    kind: str
    config: dict[str, object] = Field(default_factory=dict)


class AutomationTaskRuleDto(BaseModel):
    kind: str
    config: dict[str, object] = Field(default_factory=dict)


class AutomationTaskCreateInput(BaseModel):
    name: str
    type: str
    cron_expr: str | None = None
    rule: AutomationTaskRuleInput | None = None
    config_json: str | None = None


class AutomationTaskUpdateInput(BaseModel):
    name: str | None = None
    type: str | None = None
    enabled: bool | None = None
    cron_expr: str | None = None
    rule: AutomationTaskRuleInput | None = None
    config_json: str | None = None


class AutomationTaskDto(BaseModel):
    id: str
    name: str
    type: str
    enabled: bool
    cron_expr: str | None = None
    last_run_at: datetime | None = None
    last_run_status: str | None = None
    run_count: int
    rule: AutomationTaskRuleDto | None = None
    config_json: str | None = None
    created_at: datetime
    updated_at: datetime


class AutomationTaskRunDto(BaseModel):
    id: str
    task_id: str
    status: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    log_text: str | None = None
    created_at: datetime


class TriggerTaskResultDto(BaseModel):
    task_id: str
    run_id: str
    status: str
    message: str
