from __future__ import annotations

from pydantic import BaseModel


class BootstrapDirectoryItemDto(BaseModel):
    key: str
    label: str
    path: str
    exists: bool
    writable: bool
    status: str
    message: str | None = None


class BootstrapDirectoryReportDto(BaseModel):
    rootDir: str
    databasePath: str
    status: str
    directories: list[BootstrapDirectoryItemDto]
    checkedAt: str


class RuntimeSelfCheckItemDto(BaseModel):
    key: str
    label: str
    status: str
    detail: str
    errorCode: str | None = None
    checkedAt: str


class RuntimeSelfCheckReportDto(BaseModel):
    status: str
    runtimeVersion: str
    checkedAt: str
    items: list[RuntimeSelfCheckItemDto]


class BootstrapActionDto(BaseModel):
    key: str
    label: str


class BootstrapReadinessItemDto(BaseModel):
    key: str
    label: str
    status: str
    detail: str
    errorCode: str | None = None
    blockedReason: str | None = None
    affectedTarget: str | None = None
    nextStep: str | None = None
    action: BootstrapActionDto | None = None
    checkedAt: str


class BootstrapBlockerDto(BaseModel):
    key: str
    errorCode: str
    blockedReason: str
    affectedTarget: str
    nextStep: str
    action: BootstrapActionDto | None = None


class BootstrapReadinessReportDto(BaseModel):
    status: str
    canContinue: bool
    checkedAt: str
    items: list[BootstrapReadinessItemDto]
    blockers: list[BootstrapBlockerDto]

