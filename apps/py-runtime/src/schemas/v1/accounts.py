from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, model_validator

from schemas.v1.account_common import (
    AccountDto,
    AccountReadinessDto,
    AccountV1Model,
    PositiveRevision,
    StableId,
)

CopySection = Literal[
    "positioning",
    "knowledgeRules",
    "brandKit",
    "aiRecipe",
    "publishDefaults",
]
WizardStep = Literal[
    "identity",
    "connection",
    "positioning",
    "knowledge",
    "ai_recipe",
    "health",
]
HealthCheckKey = Literal["connection", "knowledge", "ai"]
AccountWorkspaceRouteId = Literal[
    "account_workspace_home",
    "account_strategy_knowledge",
    "account_script_topic",
    "account_storyboard_planning",
    "account_video_deconstruction",
    "account_batch_production",
    "account_content_library",
    "account_media_toolbox",
    "account_publishing",
    "account_review",
]


class AccountCreateInput(AccountV1Model):
    name: Annotated[str, Field(min_length=1, max_length=128)]
    username: Annotated[str, Field(min_length=1, max_length=64)] | None = None
    platform: Annotated[str, Field(min_length=1, max_length=32)]


class AccountPatchInput(AccountV1Model):
    name: Annotated[str, Field(min_length=1, max_length=128)] | None = None
    username: Annotated[str, Field(min_length=1, max_length=64)] | None = None
    avatarAssetRef: Annotated[str, Field(min_length=1, max_length=512)] | None = None

    @model_validator(mode="after")
    def require_one_field(self) -> AccountPatchInput:
        if not self.model_fields_set:
            raise ValueError("至少需要提交一个账号字段")
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("账号名称不能设为空值")
        return self


class CompleteWizardInput(AccountV1Model):
    completedSteps: Annotated[
        list[WizardStep],
        Field(min_length=1, max_length=6),
    ]

    @model_validator(mode="after")
    def reject_duplicate_steps(self) -> CompleteWizardInput:
        if len(set(self.completedSteps)) != len(self.completedSteps):
            raise ValueError("向导完成步骤不能重复")
        return self


class AccountCopyInput(AccountV1Model):
    sourceAccountId: StableId
    sections: Annotated[
        list[CopySection],
        Field(min_length=1, max_length=5),
    ]

    @model_validator(mode="after")
    def reject_duplicate_sections(self) -> AccountCopyInput:
        if len(set(self.sections)) != len(self.sections):
            raise ValueError("账号配置复制分区不能重复")
        return self


class ArchiveInput(AccountV1Model):
    reason: Annotated[str, Field(min_length=1, max_length=512)] | None = None


class HealthCheckInput(AccountV1Model):
    checks: Annotated[
        list[HealthCheckKey],
        Field(min_length=1, max_length=3),
    ] | None = None


class ConnectionBindingInput(AccountV1Model):
    environmentId: StableId
    eligibilityRevision: PositiveRevision


class AccountNavigationDto(AccountV1Model):
    lastRoute: Annotated[str, Field(min_length=1, max_length=256)]
    availableRoutes: list[AccountWorkspaceRouteId]


class AccountTaskSummaryDto(AccountV1Model):
    running: Annotated[int, Field(ge=0)]
    failed: Annotated[int, Field(ge=0)]


class AccountWorkspaceContextDto(AccountV1Model):
    account: AccountDto
    readiness: AccountReadinessDto
    navigation: AccountNavigationDto
    taskSummary: AccountTaskSummaryDto
    workspaceRevision: PositiveRevision


class AccountCopySkippedSectionDto(AccountV1Model):
    section: CopySection
    reasonCode: Annotated[str, Field(min_length=1, max_length=128)]


class AccountConfigCopyResultDto(AccountV1Model):
    runId: StableId
    sourceAccountId: StableId
    targetAccountId: StableId
    requestedSections: list[CopySection]
    copiedSections: list[CopySection]
    skippedSections: list[AccountCopySkippedSectionDto]
    status: Literal["succeeded"]
    targetRevision: PositiveRevision
    completedAt: str


class DeviceWorkspaceSummaryDto(AccountV1Model):
    id: StableId
    name: str
    status: str


class BrowserInstanceSummaryDto(AccountV1Model):
    id: StableId
    name: str
    status: str
    lastCheckedAt: str | None


class ExecutionBindingSummaryDto(AccountV1Model):
    id: StableId
    status: str
    deviceWorkspaceId: StableId
    browserInstanceId: StableId


class ConnectionCandidateDto(AccountV1Model):
    environmentId: StableId
    eligibilityRevision: PositiveRevision
    deviceWorkspace: DeviceWorkspaceSummaryDto
    browserInstance: BrowserInstanceSummaryDto
    executionBinding: ExecutionBindingSummaryDto


class ConnectionCandidatesDto(AccountV1Model):
    items: list[ConnectionCandidateDto]


class ConnectionCheckSummaryDto(AccountV1Model):
    status: Literal["unknown", "checking", "ready", "attention", "failed"]
    checkedAt: str | None
    errorCode: str | None
    logId: StableId | None


class ConnectionDto(AccountV1Model):
    accountId: StableId
    authStatus: Literal["unknown", "required", "valid", "expired", "failed"]
    healthStatus: Literal["unknown", "checking", "ready", "attention", "failed"]
    deviceWorkspace: DeviceWorkspaceSummaryDto | None
    browserInstance: BrowserInstanceSummaryDto | None
    executionBinding: ExecutionBindingSummaryDto | None
    lastCheck: ConnectionCheckSummaryDto | None
    revision: PositiveRevision
