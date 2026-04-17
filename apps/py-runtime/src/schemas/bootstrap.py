from __future__ import annotations

from pydantic import BaseModel


class BootstrapDirectoryStatusDto(BaseModel):
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
    directories: list[BootstrapDirectoryStatusDto]
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
