from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

LicenseState = Literal[
    "missing",
    "active",
    "expired",
    "invalid",
    "machine_mismatch",
]
MachineIdentityState = Literal[
    "verified",
    "degraded",
    "unavailable",
    "mismatch",
]
DirectoryAggregateState = Literal["ready", "attention", "failed"]
DirectoryItemState = Literal["ready", "created", "failed"]
RuntimeState = Literal["starting", "ready", "failed"]
MediaToolsState = Literal["ready", "attention", "failed"]
SelfCheckKey = Literal["database", "directories", "media_tools", "runtime"]


class V1Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LicenseBlockingIssueDto(V1Model):
    code: str
    message: str


class LicenseStatusDto(V1Model):
    status: LicenseState
    machineCode: str
    machineCodeMasked: str
    expiresAt: str | None
    activatedAt: str | None
    blockingIssue: LicenseBlockingIssueDto | None
    revision: int
    machineIdentityStatus: MachineIdentityState = "verified"
    machineIdentityAlgorithm: str = "v2"
    matchedFactorCount: int = 0
    mismatchedFactorCount: int = 0
    unavailableFactorCount: int = 0


class DirectoryItemDto(V1Model):
    key: str
    status: DirectoryItemState
    writable: bool


class DirectoryIssueDto(V1Model):
    code: str
    message: str
    logId: str | None


class DirectoryReportDto(V1Model):
    status: DirectoryAggregateState
    workspaceRootDisplay: str
    directories: list[DirectoryItemDto]
    issues: list[DirectoryIssueDto]
    revision: int


class RuntimeStatusDto(V1Model):
    status: RuntimeState
    version: str


class MediaToolsStatusDto(V1Model):
    status: MediaToolsState
    issues: list[str]


class BootstrapBlockingIssueDto(V1Model):
    code: str
    message: str
    logId: str | None


class BootstrapStatusDto(V1Model):
    license: LicenseStatusDto
    directories: DirectoryReportDto
    runtime: RuntimeStatusDto
    mediaTools: MediaToolsStatusDto
    canContinue: bool
    blockingIssues: list[BootstrapBlockingIssueDto]
    revision: int


class LicenseActivationInput(V1Model):
    licenseKey: Annotated[str, Field(min_length=1, max_length=16384)]
    machineCode: Annotated[str, Field(min_length=1, max_length=128)] | None = None


class DirectoryInitializationInput(V1Model):
    workspaceRootRef: Annotated[str, Field(min_length=1, max_length=512)] | None = None


class SelfCheckInput(V1Model):
    checks: Annotated[list[SelfCheckKey], Field(min_length=1, max_length=4)]


class TaskAcceptedDto(V1Model):
    taskId: str
    scope: Literal["system", "account"]
    accountId: str | None
    taskType: str
    status: Literal["queued"]
    cancellable: bool
    createdAt: str
