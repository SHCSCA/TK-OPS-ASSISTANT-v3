from __future__ import annotations

from pydantic import BaseModel


class ImportVideoInput(BaseModel):
    filePath: str


class ImportedVideoDto(BaseModel):
    id: str
    projectId: str
    filePath: str
    fileName: str
    fileSizeBytes: int
    durationSeconds: float | None = None
    width: int | None = None
    height: int | None = None
    frameRate: float | None = None
    codec: str | None = None
    status: str
    errorMessage: str | None = None
    createdAt: str
