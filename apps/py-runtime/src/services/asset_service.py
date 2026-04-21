from __future__ import annotations

import asyncio
import json
import logging
import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException

from common.time import utc_now_iso
from domain.models.asset import Asset, AssetGroup, AssetReference
from repositories.asset_repository import AssetRepository
from schemas.assets import (
    AssetAvailabilityDto,
    AssetCreateInput,
    AssetDto,
    AssetGroupCreateInput,
    AssetGroupDto,
    AssetGroupUpdateInput,
    AssetImportInput,
    AssetReferenceSummaryDto,
    AssetReferenceCreateInput,
    AssetReferenceDto,
    AssetSourceInfoDto,
    AssetThumbnailStatusDto,
    AssetUpdateInput,
    BatchDeleteAssetsInput,
    BatchMoveGroupInput,
)
from services.task_manager import ProgressCallback, TaskManager, task_manager as default_task_manager

log = logging.getLogger(__name__)


class AssetService:
    def __init__(
        self,
        repository: AssetRepository,
        task_manager: TaskManager | None = None,
    ) -> None:
        self._repository = repository
        self._task_manager = task_manager or default_task_manager

    def list_assets(
        self,
        *,
        asset_type: str | None = None,
        source: str | None = None,
        project_id: str | None = None,
        group_id: str | None = None,
        q: str | None = None,
    ) -> list[AssetDto]:
        try:
            assets = self._repository.list_assets(
                asset_type=asset_type,
                source=source,
                project_id=project_id,
                group_id=group_id,
                q=q,
            )
        except Exception as exc:
            log.exception("查询资产列表失败")
            raise HTTPException(status_code=500, detail="查询资产列表失败") from exc
        return [self._to_dto(asset) for asset in assets]

    def create_asset(self, payload: AssetCreateInput) -> AssetDto:
        name = payload.name.strip()
        if not name:
            raise HTTPException(status_code=400, detail="资产名称不能为空")

        now = _utc_now()
        asset = Asset(
            id=str(uuid4()),
            name=name,
            type=payload.type,
            source=payload.source,
            group_id=payload.groupId,
            file_path=payload.filePath,
            file_size_bytes=payload.fileSizeBytes,
            duration_ms=payload.durationMs,
            thumbnail_path=payload.thumbnailPath,
            thumbnail_generated_at=None,
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

        self._schedule_thumbnail_task(saved)
        return self._to_dto(saved)

    def import_asset(self, payload: AssetImportInput) -> AssetDto:
        file_path = Path(payload.filePath)
        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(status_code=400, detail="文件不存在，请确认本地路径后重试")

        return self.create_asset(
            AssetCreateInput(
                name=file_path.name,
                type=payload.type,
                source=payload.source,
                groupId=payload.groupId,
                filePath=str(file_path),
                fileSizeBytes=file_path.stat().st_size,
                durationMs=None,
                thumbnailPath=None,
                tags=payload.tags,
                projectId=payload.projectId,
                metadataJson=payload.metadataJson,
            )
        )

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
            name = payload.name.strip()
            if not name:
                raise HTTPException(status_code=400, detail="资产名称不能为空")
            changes["name"] = name
        if "groupId" in payload.model_fields_set:
            changes["group_id"] = payload.groupId
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
            reference_count = self._repository.count_references(asset_id)
        except Exception as exc:
            log.exception("检查资产引用失败")
            raise HTTPException(status_code=500, detail="检查资产引用失败") from exc

        if reference_count > 0:
            raise HTTPException(
                status_code=409,
                detail=f"资产存在引用，请先处理 {reference_count} 条引用后再删除",
            )

        try:
            deleted = self._repository.delete_asset(asset_id)
        except Exception as exc:
            log.exception("删除资产失败")
            raise HTTPException(status_code=500, detail="删除资产失败") from exc
        if not deleted:
            raise HTTPException(status_code=404, detail="资产不存在")
        return {"deleted": True}

    def batch_delete_assets(self, payload: BatchDeleteAssetsInput) -> dict[str, int]:
        try:
            deleted_count = self._repository.batch_delete_assets(payload.assetIds)
        except Exception as exc:
            log.exception("批量删除资产失败")
            raise HTTPException(status_code=500, detail="批量删除资产失败") from exc
        return {"deletedCount": deleted_count}

    def batch_move_group(self, payload: BatchMoveGroupInput) -> dict[str, object]:
        if payload.groupId is not None:
            self._require_group(payload.groupId)
        try:
            moved_count = self._repository.batch_move_group(payload.assetIds, payload.groupId)
        except Exception as exc:
            log.exception("批量移动资产分组失败")
            raise HTTPException(status_code=500, detail="批量移动资产分组失败") from exc
        return {"movedCount": moved_count, "groupId": payload.groupId}

    def list_groups(self) -> list[AssetGroupDto]:
        try:
            groups = self._repository.list_groups()
        except Exception as exc:
            log.exception("查询资产分组列表失败")
            raise HTTPException(status_code=500, detail="查询资产分组列表失败") from exc
        return [self._to_group_dto(group) for group in groups]

    def create_group(self, payload: AssetGroupCreateInput) -> AssetGroupDto:
        self._require_parent_group(payload.parentId)
        group = AssetGroup(
            id=str(uuid4()),
            name=payload.name.strip(),
            parent_id=payload.parentId,
            created_at=_utc_now(),
        )
        try:
            saved = self._repository.create_group(group)
        except Exception as exc:
            log.exception("创建资产分组失败")
            raise HTTPException(status_code=500, detail="创建资产分组失败") from exc
        return self._to_group_dto(saved)

    def update_group(self, group_id: str, payload: AssetGroupUpdateInput) -> AssetGroupDto:
        changes: dict[str, object] = {}
        if payload.name is not None:
            name = payload.name.strip()
            if not name:
                raise HTTPException(status_code=400, detail="资产分组名称不能为空")
            changes["name"] = name
        if "parentId" in payload.model_fields_set:
            self._require_parent_group(payload.parentId)
            changes["parent_id"] = payload.parentId
        try:
            group = self._repository.update_group(group_id, changes=changes)
        except Exception as exc:
            log.exception("更新资产分组失败")
            raise HTTPException(status_code=500, detail="更新资产分组失败") from exc
        if group is None:
            raise HTTPException(status_code=404, detail="资产分组不存在")
        return self._to_group_dto(group)

    def delete_group(self, group_id: str) -> dict[str, bool]:
        try:
            deleted = self._repository.delete_group(group_id)
        except Exception as exc:
            log.exception("删除资产分组失败")
            raise HTTPException(status_code=500, detail="删除资产分组失败") from exc
        if not deleted:
            raise HTTPException(status_code=404, detail="资产分组不存在")
        return {"deleted": True}

    def get_reference(self, reference_id: str) -> AssetReferenceDto:
        try:
            reference = self._repository.get_reference(reference_id)
        except Exception as exc:
            log.exception("查询资产引用详情失败")
            raise HTTPException(status_code=500, detail="查询资产引用详情失败") from exc
        if reference is None:
            raise HTTPException(status_code=404, detail="资产引用不存在")
        return self._to_ref_dto(reference)

    def list_references(self, asset_id: str) -> list[AssetReferenceDto]:
        self.get_asset(asset_id)
        try:
            references = self._repository.list_references(asset_id)
        except Exception as exc:
            log.exception("查询资产引用失败")
            raise HTTPException(status_code=500, detail="查询资产引用失败") from exc
        return [self._to_ref_dto(reference) for reference in references]

    def add_reference(self, asset_id: str, payload: AssetReferenceCreateInput) -> AssetReferenceDto:
        self.get_asset(asset_id)
        reference = AssetReference(
            id=str(uuid4()),
            asset_id=asset_id,
            reference_type=payload.referenceType,
            reference_id=payload.referenceId,
            created_at=_utc_now(),
        )
        try:
            saved = self._repository.create_reference(reference)
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
        source_info = self._build_source_info(asset)
        availability = self._build_availability(asset)
        reference_summary = self._build_reference_summary(asset.id)
        thumbnail_status = self._build_thumbnail_status(asset)
        return AssetDto(
            id=asset.id,
            name=asset.name,
            type=asset.type,
            source=asset.source,
            groupId=asset.group_id,
            filePath=asset.file_path,
            fileSizeBytes=asset.file_size_bytes,
            durationMs=asset.duration_ms,
            thumbnailPath=asset.thumbnail_path,
            thumbnailGeneratedAt=asset.thumbnail_generated_at,
            tags=asset.tags,
            projectId=asset.project_id,
            metadataJson=asset.metadata_json,
            sourceInfo=source_info,
            availability=availability,
            referenceSummary=reference_summary,
            thumbnailStatus=thumbnail_status,
            createdAt=asset.created_at,
            updatedAt=asset.updated_at,
        )

    def _build_source_info(self, asset: Asset) -> AssetSourceInfoDto:
        return AssetSourceInfoDto(
            source=asset.source,
            projectId=asset.project_id,
            groupId=asset.group_id,
            filePath=asset.file_path,
            metadataSummary=self._parse_metadata_summary(asset.metadata_json),
        )

    def _build_availability(self, asset: Asset) -> AssetAvailabilityDto:
        file_path = (asset.file_path or "").strip()
        if file_path == "":
            return AssetAvailabilityDto(
                status="missing_source",
                errorCode="asset.file_path_missing",
                errorMessage="资产缺少源文件路径，当前不可直接使用。",
                nextAction="请重新导入文件，或在资产详情里补齐本地路径。",
            )

        source_path = Path(file_path)
        if not source_path.exists() or not source_path.is_file():
            return AssetAvailabilityDto(
                status="missing_file",
                errorCode="asset.file_missing",
                errorMessage="资产源文件不存在，当前无法继续使用。",
                nextAction="请确认源文件仍在本地磁盘，再重新导入或修复路径。",
            )

        return AssetAvailabilityDto(
            status="ready",
            errorCode=None,
            errorMessage=None,
            nextAction=None,
        )

    def _build_reference_summary(self, asset_id: str) -> AssetReferenceSummaryDto:
        try:
            total, reference_types = self._repository.summarize_references(asset_id)
        except Exception as exc:
            log.exception("汇总资产引用摘要失败")
            raise HTTPException(status_code=500, detail="汇总资产引用摘要失败") from exc
        return AssetReferenceSummaryDto(
            total=total,
            referenceTypes=reference_types,
            blockingDelete=total > 0,
        )

    def _build_thumbnail_status(self, asset: Asset) -> AssetThumbnailStatusDto:
        if asset.type not in {"image", "video"}:
            return AssetThumbnailStatusDto(status="none", path=None, generatedAt=None)

        source_path = Path(asset.file_path) if asset.file_path else None
        if source_path is None or not source_path.is_file():
            return AssetThumbnailStatusDto(
                status="missing_source",
                path=asset.thumbnail_path,
                generatedAt=asset.thumbnail_generated_at,
            )

        task_info = self._active_thumbnail_task(asset.id)
        if task_info is not None:
            return AssetThumbnailStatusDto(
                status=task_info.status,
                path=asset.thumbnail_path,
                generatedAt=asset.thumbnail_generated_at,
            )

        thumbnail_path = Path(asset.thumbnail_path) if asset.thumbnail_path else None
        if thumbnail_path is not None and thumbnail_path.is_file():
            return AssetThumbnailStatusDto(
                status="ready",
                path=str(thumbnail_path),
                generatedAt=asset.thumbnail_generated_at,
            )

        if asset.thumbnail_generated_at and asset.thumbnail_path:
            return AssetThumbnailStatusDto(
                status="failed",
                path=asset.thumbnail_path,
                generatedAt=asset.thumbnail_generated_at,
            )

        return AssetThumbnailStatusDto(
            status="none",
            path=asset.thumbnail_path,
            generatedAt=asset.thumbnail_generated_at,
        )

    def _active_thumbnail_task(self, asset_id: str):  # type: ignore[no-untyped-def]
        for task_info in self._task_manager.list_active():
            if task_info.task_type != "asset-thumbnail":
                continue
            if task_info.id != asset_id:
                continue
            return task_info
        return None

    def _parse_metadata_summary(
        self,
        metadata_json: str | None,
    ) -> dict[str, object] | None:
        if metadata_json is None:
            return None
        raw_metadata = metadata_json.strip()
        if raw_metadata == "":
            return None
        try:
            decoded = json.loads(raw_metadata)
        except Exception:
            return None
        if not isinstance(decoded, dict):
            return None
        return {str(key): value for key, value in decoded.items()}

    def _to_ref_dto(self, reference: AssetReference) -> AssetReferenceDto:
        return AssetReferenceDto(
            id=reference.id,
            assetId=reference.asset_id,
            referenceType=reference.reference_type,
            referenceId=reference.reference_id,
            createdAt=reference.created_at,
        )

    def _to_group_dto(self, group: AssetGroup) -> AssetGroupDto:
        return AssetGroupDto(
            id=group.id,
            name=group.name,
            parentId=group.parent_id,
            createdAt=group.created_at,
        )

    def _require_group(self, group_id: str) -> None:
        try:
            group = self._repository.get_group(group_id)
        except Exception as exc:
            log.exception("查询资产分组失败")
            raise HTTPException(status_code=500, detail="查询资产分组失败") from exc
        if group is None:
            raise HTTPException(status_code=404, detail="资产分组不存在")

    def _require_parent_group(self, parent_id: str | None) -> None:
        if parent_id is not None:
            self._require_group(parent_id)

    def _schedule_thumbnail_task(self, asset: Asset) -> None:
        if asset.type not in {"image", "video"}:
            return
        if not asset.file_path:
            return
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return

        try:
            self._task_manager.submit(
                task_type="asset-thumbnail",
                coro_factory=lambda progress_callback: self._run_thumbnail_task(
                    asset_id=asset.id,
                    file_path=asset.file_path or "",
                    progress_callback=progress_callback,
                ),
                project_id=asset.project_id,
                task_id=asset.id,
            )
        except Exception as exc:
            log.exception("资产缩略图任务入队失败")
            raise HTTPException(status_code=500, detail="资产缩略图任务入队失败") from exc

    async def _run_thumbnail_task(
        self,
        *,
        asset_id: str,
        file_path: str,
        progress_callback: ProgressCallback,
    ) -> None:
        await progress_callback(10, "正在检查缩略图源文件")
        source_path = Path(file_path)
        if not source_path.is_file():
            raise FileNotFoundError(f"源文件不存在: {file_path}")

        thumbnail_path = source_path.with_name(f"{source_path.stem}.thumb{source_path.suffix}")
        await progress_callback(60, "正在生成缩略图文件")
        shutil.copyfile(source_path, thumbnail_path)
        await progress_callback(90, "正在写入缩略图结果")
        try:
            self._repository.update_asset(
                asset_id,
                changes={
                    "thumbnail_path": str(thumbnail_path),
                    "thumbnail_generated_at": _utc_now(),
                },
            )
        except Exception as exc:
            log.exception("写入缩略图结果失败")
            raise RuntimeError("写入缩略图结果失败") from exc
        await progress_callback(100, "缩略图任务完成")


def _utc_now() -> str:
    return utc_now_iso()
