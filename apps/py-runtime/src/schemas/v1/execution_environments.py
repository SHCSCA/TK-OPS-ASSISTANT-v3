from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from schemas.v1.account_common import AccountV1Model, PositiveRevision, StableId


class ExecutionEnvironmentBrowserInput(AccountV1Model):
    kind: Literal["chrome", "edge"] = "chrome"
    selection: Literal["auto"] = "auto"


class ExecutionEnvironmentCreateInput(AccountV1Model):
    name: Annotated[str, Field(min_length=1, max_length=128)]
    rootRef: Annotated[str, Field(pattern=r"^wr_[0-9a-f]{32}$")]
    browser: ExecutionEnvironmentBrowserInput
    activateWhenReady: bool = False


class ExecutionEnvironmentWorkspaceDto(AccountV1Model):
    id: StableId
    rootRef: str
    displayName: str
    status: str
    ownershipState: str


class ExecutionEnvironmentBrowserDto(AccountV1Model):
    id: StableId
    kind: Literal["chrome", "edge"]
    displayName: str
    status: str
    ownershipVerified: bool
    lastCheckedAt: str | None


class EligibilityIssueDto(AccountV1Model):
    code: str
    message: str
    recoveryAction: str


class ExecutionEnvironmentEligibilityDto(AccountV1Model):
    eligible: bool
    blockingIssues: list[EligibilityIssueDto]
    checkedAt: str
    evidenceRevision: Annotated[int, Field(ge=1)]


class ExecutionEnvironmentDto(AccountV1Model):
    id: StableId
    accountId: StableId
    name: str
    status: str
    workspace: ExecutionEnvironmentWorkspaceDto
    browser: ExecutionEnvironmentBrowserDto
    eligibility: ExecutionEnvironmentEligibilityDto
    revision: PositiveRevision
    errorCode: str | None
    errorLogId: str | None
    errorMessage: str | None
    lastTaskId: str | None
    lastRetryOfTaskId: str | None
    recoveryActions: list[
        Literal[
            "retry_provision",
            "check",
            "reauthorize_root",
            "view_log",
            "delete_preserving_files",
        ]
    ]


class ExecutionEnvironmentListDto(AccountV1Model):
    items: list[ExecutionEnvironmentDto]


class ExecutionEnvironmentAcceptedDto(AccountV1Model):
    environmentId: StableId
    taskId: StableId


class ExecutionEnvironmentRetryAcceptedDto(ExecutionEnvironmentAcceptedDto):
    retryOfTaskId: StableId
