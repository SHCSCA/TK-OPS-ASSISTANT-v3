from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import HTTPException

from domain.models import Base
from persistence.engine import create_runtime_engine, create_session_factory
from repositories.asset_repository import AssetRepository
from schemas.assets import AssetCreateInput, AssetImportInput, AssetReferenceCreateInput
from services.asset_service import AssetService


def _make_asset_service(tmp_path: Path) -> AssetService:
    engine = create_runtime_engine(tmp_path / "runtime.db")
    Base.metadata.create_all(engine)
    repository = AssetRepository(session_factory=create_session_factory(engine))
    return AssetService(repository)


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
