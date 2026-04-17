from __future__ import annotations

from pydantic import BaseModel


class AssetCreateInput(BaseModel):
    name: str
    type: str
    source: str
    groupId: str | None = None
    filePath: str | None = None
    fileSizeBytes: int | None = None
    durationMs: int | None = None
    thumbnailPath: str | None = None
    tags: str | None = None
    projectId: str | None = None
    metadataJson: str | None = None


class AssetImportInput(BaseModel):
    filePath: str
    type: str
    source: str = "local"
    groupId: str | None = None
    projectId: str | None = None
    tags: str | None = None
    metadataJson: str | None = None


class AssetUpdateInput(BaseModel):
    name: str | None = None
    groupId: str | None = None
    tags: str | None = None
    metadataJson: str | None = None


class AssetDto(BaseModel):
    id: str
    name: str
    type: str
    source: str
    groupId: str | None = None
    filePath: str | None = None
    fileSizeBytes: int | None = None
    durationMs: int | None = None
    thumbnailPath: str | None = None
    thumbnailGeneratedAt: str | None = None
    tags: str | None = None
    projectId: str | None = None
    metadataJson: str | None = None
    createdAt: str
    updatedAt: str


class AssetReferenceCreateInput(BaseModel):
    referenceType: str
    referenceId: str


class AssetReferenceDto(BaseModel):
    id: str
    assetId: str
    referenceType: str
    referenceId: str
    createdAt: str


class AssetGroupCreateInput(BaseModel):
    name: str
    parentId: str | None = None


class AssetGroupUpdateInput(BaseModel):
    name: str | None = None
    parentId: str | None = None


class AssetGroupDto(BaseModel):
    id: str
    name: str
    parentId: str | None = None
    createdAt: str


class BatchDeleteAssetsInput(BaseModel):
    assetIds: list[str]


class BatchMoveGroupInput(BaseModel):
    assetIds: list[str]
    groupId: str | None = None
