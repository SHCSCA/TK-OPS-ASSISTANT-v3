from __future__ import annotations

from sqlalchemy import text

from persistence.engine import (
    create_runtime_engine,
    create_session_factory,
    initialize_domain_schema,
)
from repositories.asset_repository import AssetRepository
from schemas.assets import AssetImportInput
from services.asset_service import AssetService


def test_initialize_domain_schema_repairs_legacy_asset_table(tmp_path) -> None:  # type: ignore[no-untyped-def]
    engine = create_runtime_engine(tmp_path / "runtime.db")

    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE projects (id TEXT PRIMARY KEY)"))
        connection.execute(
            text(
                """
                CREATE TABLE assets (
                    id VARCHAR PRIMARY KEY,
                    project_id VARCHAR,
                    kind VARCHAR NOT NULL,
                    file_path TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    file_size_bytes INTEGER NOT NULL,
                    mime_type VARCHAR,
                    source VARCHAR NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO assets (
                    id, project_id, kind, file_path, file_name, file_size_bytes,
                    mime_type, source, metadata_json, created_at
                )
                VALUES (
                    'legacy-asset', NULL, 'video', 'D:/tkops/assets/legacy.mp4',
                    'legacy.mp4', 2048, 'video/mp4', 'local', '{}',
                    '2026-04-16T10:00:00'
                )
                """
            )
        )

    initialize_domain_schema(engine)

    columns = _table_columns(engine, "assets")
    assert {"name", "type", "updated_at", "tags", "duration_ms", "thumbnail_path"} <= columns

    repository = AssetRepository(session_factory=create_session_factory(engine))
    assets = repository.list_assets()

    assert len(assets) == 1
    assert assets[0].id == "legacy-asset"
    assert assets[0].name == "legacy.mp4"
    assert assets[0].type == "video"
    assert assets[0].updated_at == "2026-04-16T10:00:00"


def test_import_asset_after_legacy_kind_schema_repair(tmp_path) -> None:  # type: ignore[no-untyped-def]
    engine = create_runtime_engine(tmp_path / "runtime.db")

    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE projects (id TEXT PRIMARY KEY)"))
        connection.execute(
            text(
                """
                CREATE TABLE assets (
                    id VARCHAR PRIMARY KEY,
                    project_id VARCHAR,
                    kind VARCHAR NOT NULL,
                    file_path TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    file_size_bytes INTEGER NOT NULL,
                    mime_type VARCHAR,
                    source VARCHAR NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
        )

    initialize_domain_schema(engine)

    source_file = tmp_path / "Snipaste_2026-02-27_13-52-01.png"
    source_file.write_bytes(b"real-image-bytes")

    service = AssetService(
        AssetRepository(session_factory=create_session_factory(engine))
    )
    imported = service.import_asset(
        AssetImportInput(
            filePath=str(source_file),
            type="image",
            source="local",
        )
    )

    assert imported.name == "Snipaste_2026-02-27_13-52-01.png"
    assert imported.type == "image"
    assert imported.fileSizeBytes == len(b"real-image-bytes")


def test_initialize_domain_schema_creates_asset_group_tables(tmp_path) -> None:  # type: ignore[no-untyped-def]
    engine = create_runtime_engine(tmp_path / "runtime.db")

    initialize_domain_schema(engine)

    columns = _table_columns(engine, "assets")
    assert {"group_id", "thumbnail_generated_at"} <= columns
    assert _table_columns(engine, "asset_groups") >= {"id", "name", "created_at"}


def _table_columns(engine, table_name: str) -> set[str]:  # type: ignore[no-untyped-def]
    with engine.connect() as connection:
        rows = connection.execute(text(f"PRAGMA table_info({table_name})")).mappings().all()
    return {str(row["name"]) for row in rows}
