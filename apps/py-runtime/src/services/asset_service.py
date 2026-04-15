from __future__ import annotations

import logging
from datetime import datetime
from uuid import uuid4

from fastapi import HTTPException

from domain.models.asset import Asset, AssetReference
from repositories.asset_repository import AssetRepository
from schemas.assets import (
    AssetCreateInput,
    AssetDto,
    AssetReferenceCreateInput,
    AssetReferenceDto,
    AssetUpdateInput,
)

log = logging.getLogger(__name__)


class AssetService:
    def __init__(self, repository: AssetRepository) -> None:
        self._repository = repository

    def list_assets(
        self,
        *,
        asset_type: str | None = None,
        source: str | None = None,
        project_id: str | None = None,
        q: str | None = None,
    ) -> list[AssetDto]:
        try:
            assets = self._repository.list_assets(
                asset_type=asset_type,
                source=source,
                project_id=project_id,
                q=q,
            )
        except Exception as exc:
            log.exception("查询资产列表失败")
            raise HTTPException(status_code=500, detail="查询资产列表失败") from exc
        return [self._to_dto(a) for a in assets]

    def create_asset(self, payload: AssetCreateInput) -> AssetDto:
        now = _utc_now()
        asset = Asset(
            id=str(uuid4()),
            name=payload.name.strip(),
            type=payload.type,
            source=payload.source,
            file_path=payload.filePath,
            file_size_bytes=payload.fileSizeBytes,
            duration_ms=payload.durationMs,
            thumbnail_path=payload.thumbnailPath,
            tags=payload.tags,
            project_id=payload.projectId,
            metadata_json=payload.metadataJson,
            created_at=now,
            updated_at=now,
        )
        try:
            saved = self._repository.create_asset(asset)
        except Exception as exc:
            log.exception("创建资产失败")
            raise HTTPException(status_code=500, detail="创建资产失败") from exc
        return self._to_dto(saved)

    def get_asset(self, asset_id: str) -> AssetDto:
        try:
            asset = self._repository.get_asset(asset_id)
        except Exception as exc:
            log.exception("查询资产详情失败")
            raise HTTPException(status_code=500, detail="查询资产详情失败") from exc
        if asset is None:
            raise HTTPException(status_code=404, detail="资产不存在")
        return self._to_dto(asset)

    def update_asset(self, asset_id: str, payload: AssetUpdateInput) -> AssetDto:
        changes: dict[str, object] = {}
        if payload.name is not None:
            changes["name"] = payload.name.strip()
        if "tags" in payload.model_fields_set:
            changes["tags"] = payload.tags
        if "metadataJson" in payload.model_fields_set:
            changes["metadata_json"] = payload.metadataJson
        try:
            asset = self._repository.update_asset(asset_id, changes=changes)
        except Exception as exc:
            log.exception("更新资产失败")
            raise HTTPException(status_code=500, detail="更新资产失败") from exc
        if asset is None:
            raise HTTPException(status_code=404, detail="资产不存在")
        return self._to_dto(asset)

    def delete_asset(self, asset_id: str) -> dict[str, bool]:
        try:
            deleted = self._repository.delete_asset(asset_id)
        except Exception as exc:
            log.exception("删除资产失败")
            raise HTTPException(status_code=500, detail="删除资产失败") from exc
        if not deleted:
            raise HTTPException(status_code=404, detail="资产不存在")
        return {"deleted": True}

    def list_references(self, asset_id: str) -> list[AssetReferenceDto]:
        self.get_asset(asset_id)  # validates existence
        try:
            refs = self._repository.list_references(asset_id)
        except Exception as exc:
            log.exception("查询资产引用失败")
            raise HTTPException(status_code=500, detail="查询资产引用失败") from exc
        return [self._to_ref_dto(r) for r in refs]

    def add_reference(self, asset_id: str, payload: AssetReferenceCreateInput) -> AssetReferenceDto:
        self.get_asset(asset_id)
        ref = AssetReference(
            id=str(uuid4()),
            asset_id=asset_id,
            reference_type=payload.referenceType,
            reference_id=payload.referenceId,
            created_at=_utc_now(),
        )
        try:
            saved = self._repository.create_reference(ref)
        except Exception as exc:
            log.exception("添加资产引用失败")
            raise HTTPException(status_code=500, detail="添加资产引用失败") from exc
        return self._to_ref_dto(saved)

    def delete_reference(self, reference_id: str) -> dict[str, bool]:
        try:
            deleted = self._repository.delete_reference(reference_id)
        except Exception as exc:
            log.exception("删除资产引用失败")
            raise HTTPException(status_code=500, detail="删除资产引用失败") from exc
        if not deleted:
            raise HTTPException(status_code=404, detail="资产引用不存在")
        return {"deleted": True}

    def _to_dto(self, asset: Asset) -> AssetDto:
        return AssetDto(
            id=asset.id,
            name=asset.name,
            type=asset.type,
            source=asset.source,
            filePath=asset.file_path,
            fileSizeBytes=asset.file_size_bytes,
            durationMs=asset.duration_ms,
            thumbnailPath=asset.thumbnail_path,
            tags=asset.tags,
            projectId=asset.project_id,
            metadataJson=asset.metadata_json,
            createdAt=asset.created_at,
            updatedAt=asset.updated_at,
        )

    def _to_ref_dto(self, ref: AssetReference) -> AssetReferenceDto:
        return AssetReferenceDto(
            id=ref.id,
            assetId=ref.asset_id,
            referenceType=ref.reference_type,
            referenceId=ref.reference_id,
            createdAt=ref.created_at,
        )


def _utc_now() -> str:
    return datetime.utcnow().isoformat()
