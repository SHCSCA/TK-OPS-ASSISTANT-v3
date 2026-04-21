from __future__ import annotations

from pydantic import BaseModel


class RuntimeSubsystemHealthDto(BaseModel):
    status: str
    port: int
    uptimeMs: int | None = None
    version: str


class AIProviderHealthDto(BaseModel):
    status: str
    latencyMs: int | None = None
    providerId: str
    providerName: str
    lastChecked: str | None = None


class RenderQueueHealthDto(BaseModel):
    running: int
    queued: int
    avgWaitMs: int | None = None


class PublishingQueueHealthDto(BaseModel):
    pendingToday: int
    failedToday: int


class TaskBusHealthDto(BaseModel):
    running: int
    queued: int
    blocked: int
    failed24h: int


class LicenseHealthDto(BaseModel):
    status: str
    expiresAt: str | None = None


class RuntimeHealthSnapshotDto(BaseModel):
    runtime: RuntimeSubsystemHealthDto
    aiProvider: AIProviderHealthDto
    renderQueue: RenderQueueHealthDto
    publishingQueue: PublishingQueueHealthDto
    taskBus: TaskBusHealthDto
    license: LicenseHealthDto
    lastSyncAt: str
    service: str
    version: str
    now: str
    mode: str


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


class FfprobeDiagnosticsDto(BaseModel):
    status: str
    path: str | None = None
    version: str | None = None
    errorCode: str | None = None
    errorMessage: str | None = None


class MediaDiagnosticsDto(BaseModel):
    ffprobe: FfprobeDiagnosticsDto
    checkedAt: str


class RuntimeLogItemDto(BaseModel):
    timestamp: str
    level: str
    kind: str
    requestId: str | None = None
    message: str
    context: dict[str, object] | None = None


class RuntimeLogPageDto(BaseModel):
    items: list[RuntimeLogItemDto]
    nextCursor: str | None = None


class DiagnosticsBundleDto(BaseModel):
    bundlePath: str
    createdAt: str
    entries: list[str]
