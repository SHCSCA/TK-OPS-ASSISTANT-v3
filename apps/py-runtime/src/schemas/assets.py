from __future__ import annotations

from pydantic import BaseModel


class AssetCreateInput(BaseModel):
    name: str
    type: str                       # video / audio / image / document / other
    source: str                     # local / generated / imported
    filePath: str | None = None
    fileSizeBytes: int | None = None
    durationMs: int | None = None
    thumbnailPath: str | None = None
    tags: str | None = None         # JSON array string
    projectId: str | None = None
    metadataJson: str | None = None


class AssetUpdateInput(BaseModel):
    name: str | None = None
    tags: str | None = None
    metadataJson: str | None = None


class AssetDto(BaseModel):
    id: str
    name: str
    type: str
    source: str
    filePath: str | None = None
    fileSizeBytes: int | None = None
    durationMs: int | None = None
    thumbnailPath: str | None = None
    tags: str | None = None
    projectId: str | None = None
    metadataJson: str | None = None
    createdAt: str
    updatedAt: str


class AssetReferenceCreateInput(BaseModel):
    referenceType: str   # script / storyboard / render / timeline
    referenceId: str


class AssetReferenceDto(BaseModel):
    id: str
    assetId: str
    referenceType: str
    referenceId: str
    createdAt: str
