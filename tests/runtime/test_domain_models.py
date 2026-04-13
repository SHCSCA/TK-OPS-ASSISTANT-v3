from __future__ import annotations

from pathlib import Path

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from domain.models import (
    AICapabilityConfig,
    AIJobRecord,
    AIProviderSetting,
    Base,
    LicenseGrant,
    ImportedVideo,
    Project,
    ScriptVersion,
    SessionContext,
    StoryboardVersion,
    SystemConfig,
    generate_uuid,
)
from persistence.engine import create_runtime_engine, create_session_factory


def test_base_registry_exists() -> None:
    assert hasattr(Base, "metadata")
    assert Base.metadata is not None


def test_generate_uuid_returns_32_char_hex() -> None:
    uid = generate_uuid()

    assert isinstance(uid, str)
    assert len(uid) == 32
    assert uid.isalnum()


def test_domain_models_match_existing_table_names() -> None:
    assert Project.__tablename__ == "projects"
    assert ScriptVersion.__tablename__ == "script_versions"
    assert StoryboardVersion.__tablename__ == "storyboard_versions"
    assert AIJobRecord.__tablename__ == "ai_job_records"
    assert AICapabilityConfig.__tablename__ == "ai_capability_configs"
    assert AIProviderSetting.__tablename__ == "ai_provider_settings"
    assert LicenseGrant.__tablename__ == "license_grant"
    assert ImportedVideo.__tablename__ == "imported_videos"
    assert SystemConfig.__tablename__ == "system_config"
    assert SessionContext.__tablename__ == "session_context"


def test_project_columns_match_existing_schema(tmp_path: Path) -> None:
    engine = create_runtime_engine(tmp_path / "runtime.db")
    Base.metadata.create_all(engine)

    inspector = inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("projects")}

    assert columns == {
        "id",
        "name",
        "description",
        "status",
        "current_script_version",
        "current_storyboard_version",
        "created_at",
        "updated_at",
        "last_accessed_at",
    }


def test_script_and_storyboard_versions_use_composite_primary_keys() -> None:
    assert [col.name for col in ScriptVersion.__table__.primary_key.columns] == [
        "project_id",
        "revision",
    ]
    assert [col.name for col in StoryboardVersion.__table__.primary_key.columns] == [
        "project_id",
        "revision",
    ]


def test_license_grant_columns_match_existing_schema(tmp_path: Path) -> None:
    engine = create_runtime_engine(tmp_path / "runtime.db")
    Base.metadata.create_all(engine)

    inspector = inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("license_grant")}

    assert columns == {
        "id",
        "active",
        "restricted_mode",
        "machine_id",
        "machine_bound",
        "activation_mode",
        "masked_code",
        "activated_at",
        "machine_code",
        "license_type",
        "signed_payload",
    }


def test_imported_video_columns_match_target_schema(tmp_path: Path) -> None:
    engine = create_runtime_engine(tmp_path / "runtime.db")
    Base.metadata.create_all(engine)

    inspector = inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("imported_videos")}

    assert columns == {
        "id",
        "project_id",
        "file_path",
        "file_name",
        "file_size_bytes",
        "duration_seconds",
        "width",
        "height",
        "frame_rate",
        "codec",
        "status",
        "error_message",
        "created_at",
    }


def test_engine_and_session_factory_create_usable_sqlite_session(tmp_path: Path) -> None:
    engine = create_runtime_engine(tmp_path / "runtime.db")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)

    with session_factory() as session:
        assert session.execute(text("SELECT 1")).scalar_one() == 1


def test_project_and_script_roundtrip_with_orm_session(tmp_path: Path) -> None:
    engine = create_runtime_engine(tmp_path / "runtime.db")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        project = Project(
            id="project-1",
            name="测试项目",
            description="描述",
            status="active",
            current_script_version=0,
            current_storyboard_version=0,
            created_at="2026-04-13T00:00:00Z",
            updated_at="2026-04-13T00:00:00Z",
            last_accessed_at="2026-04-13T00:00:00Z",
        )
        script = ScriptVersion(
            project_id="project-1",
            revision=1,
            source="manual",
            content="脚本内容",
            provider=None,
            model=None,
            ai_job_id=None,
            created_at="2026-04-13T00:00:00Z",
        )
        session.add_all([project, script])
        session.commit()

        loaded = session.get(ScriptVersion, {"project_id": "project-1", "revision": 1})

    assert loaded is not None
    assert loaded.content == "脚本内容"
