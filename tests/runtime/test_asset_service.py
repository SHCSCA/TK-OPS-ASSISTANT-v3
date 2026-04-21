from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest
from fastapi import HTTPException

from domain.models import Base
from domain.models.project import Project
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


@dataclass
class _FakeTaskInfo:
    id: str
    task_type: str
    status: str
    progress: int = 0
    message: str = "缩略图任务已排队"


class RecordingTaskManager:
    def __init__(self) -> None:
        self.submissions: list[dict[str, object]] = []
        self.active_tasks: list[_FakeTaskInfo] = []

    def submit(self, **kwargs: object) -> object:
        self.submissions.append(kwargs)
        task = _FakeTaskInfo(
            id=str(kwargs.get("task_id")),
            task_type=str(kwargs.get("task_type")),
            status="queued",
        )
        self.active_tasks.append(task)
        return task

    def list_active(self) -> list[_FakeTaskInfo]:
        return list(self.active_tasks)


def _seed_project(session_factory, project_id: str) -> None:  # type: ignore[no-untyped-def]
    with session_factory() as session:
        session.add(
            Project(
                id=project_id,
                name="资产测试项目",
                description="用于资产服务测试",
                status="active",
                current_script_version=0,
                current_storyboard_version=0,
                created_at="2026-04-21T00:00:00Z",
                updated_at="2026-04-21T00:00:00Z",
                last_accessed_at="2026-04-21T00:00:00Z",
                deleted_at=None,
            )
        )
        session.commit()


def _make_asset_service(
    tmp_path: Path,
    *,
    task_manager: RecordingTaskManager | None = None,
    seed_project_id: str | None = None,
) -> AssetService:
    engine = create_runtime_engine(tmp_path / "runtime.db")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    if seed_project_id is not None:
        _seed_project(session_factory, seed_project_id)
    repository = AssetRepository(session_factory=session_factory)
    return AssetService(repository, task_manager=task_manager or RecordingTaskManager())


def test_import_asset_records_real_file_metadata_and_runtime_summaries(
    tmp_path: Path,
) -> None:
    service = _make_asset_service(tmp_path, seed_project_id="project-asset")
    source_file = tmp_path / "opening.mp4"
    source_file.write_bytes(b"real-video-bytes")

    asset = service.import_asset(
        AssetImportInput(
            filePath=str(source_file),
            type="video",
            source="local",
            projectId="project-asset",
            tags='["开场"]',
            metadataJson='{"width":1080,"height":1920}',
        )
    )

    assert asset.name == "opening.mp4"
    assert asset.filePath == str(source_file)
    assert asset.fileSizeBytes == len(b"real-video-bytes")
    assert asset.sourceInfo.source == "local"
    assert asset.sourceInfo.projectId == "project-asset"
    assert asset.sourceInfo.filePath == str(source_file)
    assert asset.sourceInfo.metadataSummary == {"width": 1080, "height": 1920}
    assert asset.availability.status == "ready"
    assert asset.referenceSummary.total == 0
    assert asset.referenceSummary.blockingDelete is False
    assert asset.thumbnailStatus.status == "none"


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


def test_get_asset_reports_reference_summary_before_delete(tmp_path: Path) -> None:
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

    reloaded = service.get_asset(asset.id)

    assert reloaded.referenceSummary.total == 1
    assert reloaded.referenceSummary.referenceTypes == ["storyboard"]
    assert reloaded.referenceSummary.blockingDelete is True


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
    assert reloaded_a.sourceInfo.groupId == group.id
    assert reloaded_b.sourceInfo.groupId == group.id

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
async def test_create_asset_schedules_thumbnail_task_for_visual_assets(
    tmp_path: Path,
) -> None:
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
    assert asset.thumbnailStatus.status == "queued"


def test_get_asset_reports_missing_source_when_file_path_is_empty(tmp_path: Path) -> None:
    service = _make_asset_service(tmp_path)

    asset = service.create_asset(
        AssetCreateInput(
            name="generated-cover",
            type="image",
            source="generated",
            filePath=None,
        )
    )

    assert asset.availability.status == "missing_source"
    assert asset.availability.errorCode == "asset.file_path_missing"
    assert asset.thumbnailStatus.status == "missing_source"
