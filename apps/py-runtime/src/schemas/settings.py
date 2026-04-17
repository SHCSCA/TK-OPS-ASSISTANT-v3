from __future__ import annotations

from typing import Any

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


class RuntimeLogEntryDto(BaseModel):
    timestamp: str
    level: str
    kind: str
    requestId: str
    message: str
    context: dict[str, Any]


class RuntimeLogPageDto(BaseModel):
    items: list[RuntimeLogEntryDto]
    nextCursor: str | None = None


class DiagnosticsBundleEntryDto(BaseModel):
    name: str
    path: str
    sizeBytes: int


class DiagnosticsBundleDto(BaseModel):
    bundlePath: str
    createdAt: str
    entries: list[DiagnosticsBundleEntryDto]


class RuntimeHealthRuntimeDto(BaseModel):
    status: str
    port: int
    uptimeMs: int
    version: str


class RuntimeHealthAIProviderDto(BaseModel):
    status: str
    latencyMs: int | None
    providerId: str | None
    providerName: str | None
    lastChecked: str | None


class RuntimeHealthRenderQueueDto(BaseModel):
    running: int
    queued: int
    avgWaitMs: int | None


class RuntimeHealthPublishingQueueDto(BaseModel):
    pendingToday: int
    failedToday: int


class RuntimeHealthTaskBusDto(BaseModel):
    running: int
    queued: int
    blocked: int
    failed24h: int


class RuntimeHealthLicenseDto(BaseModel):
    status: str
    expiresAt: str | None


class RuntimeHealthSnapshotDto(BaseModel):
    runtime: RuntimeHealthRuntimeDto
    aiProvider: RuntimeHealthAIProviderDto
    renderQueue: RuntimeHealthRenderQueueDto
    publishingQueue: RuntimeHealthPublishingQueueDto
    taskBus: RuntimeHealthTaskBusDto
    license: RuntimeHealthLicenseDto
    lastSyncAt: str
    service: str
    version: str
    now: str
    mode: str
