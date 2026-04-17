from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import HTTPException

from domain.models import Base
from persistence.engine import create_runtime_engine, create_session_factory
from repositories.asset_repository import AssetRepository
from schemas.assets import (
    AssetCreateInput,
    AssetGroupCreateInput,
    AssetGroupUpdateInput,
    AssetImportInput,
    AssetReferenceCreateInput,
    BatchDeleteAssetsInput,
    BatchMoveGroupInput,
)
from services.asset_service import AssetService


class RecordingTaskManager:
    def __init__(self) -> None:
        self.submissions: list[dict[str, object]] = []

    def submit(self, **kwargs: object) -> object:
        self.submissions.append(kwargs)
        return type("TaskInfo", (), {"id": kwargs.get("task_id"), "status": "queued"})()


def _make_asset_service(
    tmp_path: Path,
    *,
    task_manager: RecordingTaskManager | None = None,
) -> AssetService:
    engine = create_runtime_engine(tmp_path / "runtime.db")
    Base.metadata.create_all(engine)
    repository = AssetRepository(session_factory=create_session_factory(engine))
    return AssetService(repository, task_manager=task_manager or RecordingTaskManager())


def test_import_asset_records_real_file_metadata(tmp_path: Path) -> None:
    service = _make_asset_service(tmp_path)
    source_file = tmp_path / "opening.mp4"
    source_file.write_bytes(b"real-video-bytes")

    asset = service.import_asset(
        AssetImportInput(
            filePath=str(source_file),
            type="video",
            source="local",
            tags='["开场"]',
        )
    )

    assert asset.name == "opening.mp4"
    assert asset.filePath == str(source_file)
    assert asset.fileSizeBytes == len(b"real-video-bytes")
    assert asset.thumbnailPath is None
    assert asset.durationMs is None


def test_import_asset_rejects_missing_file_with_chinese_error(tmp_path: Path) -> None:
    service = _make_asset_service(tmp_path)

    with pytest.raises(HTTPException) as exc_info:
        service.import_asset(
            AssetImportInput(
                filePath=str(tmp_path / "missing.mp4"),
                type="video",
                source="local",
            )
        )

    assert exc_info.value.status_code == 400
    assert "文件不存在" in str(exc_info.value.detail)


def test_delete_asset_blocks_when_references_exist(tmp_path: Path) -> None:
    service = _make_asset_service(tmp_path)
    asset = service.create_asset(
        AssetCreateInput(
            name="clip.mp4",
            type="video",
            source="local",
            filePath=str(tmp_path / "clip.mp4"),
        )
    )
    service.add_reference(
        asset.id,
        AssetReferenceCreateInput(referenceType="storyboard", referenceId="scene-1"),
    )

    with pytest.raises(HTTPException) as exc_info:
        service.delete_asset(asset.id)

    assert exc_info.value.status_code == 409
    assert "资产存在引用" in str(exc_info.value.detail)


def test_get_reference_returns_existing_reference(tmp_path: Path) -> None:
    service = _make_asset_service(tmp_path)
    asset = service.create_asset(
        AssetCreateInput(
            name="cover.png",
            type="image",
            source="local",
            filePath=str(tmp_path / "cover.png"),
        )
    )
    reference = service.add_reference(
        asset.id,
        AssetReferenceCreateInput(referenceType="timeline", referenceId="clip-1"),
    )

    found = service.get_reference(reference.id)

    assert found.id == reference.id
    assert found.assetId == asset.id


def test_asset_group_crud_and_batch_move_updates_assets(tmp_path: Path) -> None:
    service = _make_asset_service(tmp_path)
    group = service.create_group(AssetGroupCreateInput(name="主素材组"))

    asset_a = service.create_asset(
        AssetCreateInput(name="a.mp4", type="video", source="local")
    )
    asset_b = service.create_asset(
        AssetCreateInput(name="b.png", type="image", source="local")
    )

    updated_group = service.update_group(
        group.id,
        AssetGroupUpdateInput(name="主素材组-已改名"),
    )
    assert updated_group.name == "主素材组-已改名"

    moved = service.batch_move_group(
        BatchMoveGroupInput(assetIds=[asset_a.id, asset_b.id], groupId=group.id)
    )
    assert moved["movedCount"] == 2

    reloaded_a = service.get_asset(asset_a.id)
    reloaded_b = service.get_asset(asset_b.id)
    assert reloaded_a.groupId == group.id
    assert reloaded_b.groupId == group.id

    groups = service.list_groups()
    assert len(groups) == 1


def test_batch_delete_removes_multiple_assets(tmp_path: Path) -> None:
    service = _make_asset_service(tmp_path)
    asset_a = service.create_asset(
        AssetCreateInput(name="delete-a.mp4", type="video", source="local")
    )
    asset_b = service.create_asset(
        AssetCreateInput(name="delete-b.mp4", type="video", source="local")
    )

    result = service.batch_delete_assets(
        BatchDeleteAssetsInput(assetIds=[asset_a.id, asset_b.id])
    )

    assert result["deletedCount"] == 2

    with pytest.raises(HTTPException):
        service.get_asset(asset_a.id)

    with pytest.raises(HTTPException):
        service.get_asset(asset_b.id)


@pytest.mark.asyncio
async def test_create_asset_schedules_thumbnail_task_for_visual_assets(tmp_path: Path) -> None:
    task_manager = RecordingTaskManager()
    service = _make_asset_service(tmp_path, task_manager=task_manager)
    source_file = tmp_path / "visual.png"
    source_file.write_bytes(b"png-bytes")

    asset = service.create_asset(
        AssetCreateInput(
            name="visual.png",
            type="image",
            source="local",
            filePath=str(source_file),
        )
    )

    assert len(task_manager.submissions) == 1
    submission = task_manager.submissions[0]
    assert submission["task_type"] == "asset-thumbnail"
    assert submission["task_id"] == asset.id
