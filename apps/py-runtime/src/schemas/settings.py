from __future__ import annotations

from pydantic import BaseModel


class RuntimeSettingsSection(BaseModel):
    mode: str
    workspaceRoot: str


class PathSettingsSection(BaseModel):
    cacheDir: str
    exportDir: str
    logDir: str


class LoggingSettingsSection(BaseModel):
    level: str


class AISettingsSection(BaseModel):
    provider: str
    model: str
    voice: str
    subtitleMode: str


class AppSettingsUpdateInput(BaseModel):
    runtime: RuntimeSettingsSection
    paths: PathSettingsSection
    logging: LoggingSettingsSection
    ai: AISettingsSection


class AppSettingsDto(AppSettingsUpdateInput):
    revision: int


class RuntimeDiagnosticsDto(BaseModel):
    databasePath: str
    logDir: str
    revision: int
    mode: str
    healthStatus: str
