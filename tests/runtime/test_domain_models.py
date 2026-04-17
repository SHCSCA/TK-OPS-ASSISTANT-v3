from __future__ import annotations

from pathlib import Path

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from domain.models import (
    AICapabilityConfig,
    AIJobRecord,
    AIProviderSetting,
    Account,
    Asset,
    AutomationTask,
    Base,
    BrowserInstance,
    DeviceWorkspace,
    ExecutionBinding,
    ExportProfile,
    LicenseGrant,
    ImportedVideo,
    Project,
    PublishPlan,
    PublishReceipt,
    RenderTask,
    ScriptVersion,
    SessionContext,
    SubtitleTrack,
    StoryboardVersion,
    SystemConfig,
    Timeline,
    VideoSegment,
    VideoStructureExtraction,
    VideoTranscript,
    VoiceTrack,
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
    assert Timeline.__tablename__ == "timelines"
    assert VoiceTrack.__tablename__ == "voice_tracks"
    assert SubtitleTrack.__tablename__ == "subtitle_tracks"
    assert Asset.__tablename__ == "assets"
    assert Account.__tablename__ == "accounts"
    assert DeviceWorkspace.__tablename__ == "device_workspaces"
    assert BrowserInstance.__tablename__ == "browser_instances"
    assert ExecutionBinding.__tablename__ == "execution_bindings"
    assert AutomationTask.__tablename__ == "automation_tasks"
    assert PublishPlan.__tablename__ == "publish_plans"
    assert PublishReceipt.__tablename__ == "publish_receipts"
    assert RenderTask.__tablename__ == "render_tasks"
    assert ExportProfile.__tablename__ == "export_profiles"
    assert VideoTranscript.__tablename__ == "video_transcripts"
    assert VideoSegment.__tablename__ == "video_segments"
    assert VideoStructureExtraction.__tablename__ == "video_structure_extractions"
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


def test_core_operational_tables_match_target_schema(tmp_path: Path) -> None:
    engine = create_runtime_engine(tmp_path / "runtime.db")
    Base.metadata.create_all(engine)

    inspector = inspect(engine)
    table_columns = {
        table: {col["name"] for col in inspector.get_columns(table)}
        for table in (
            "timelines",
            "voice_tracks",
            "subtitle_tracks",
            "assets",
        "accounts",
        "device_workspaces",
        "browser_instances",
        "execution_bindings",
        "automation_tasks",
        "publish_plans",
        "publish_receipts",
        "render_tasks",
        "export_profiles",
        "video_transcripts",
        "video_segments",
        "video_structure_extractions",
    )
    }

    assert table_columns["timelines"] == {
        "id",
        "project_id",
        "name",
        "status",
        "duration_seconds",
        "tracks_json",
        "source",
        "created_at",
        "updated_at",
    }
    assert table_columns["voice_tracks"] == {
        "id",
        "project_id",
        "timeline_id",
        "source",
        "provider",
        "voice_name",
        "file_path",
        "segments_json",
        "status",
        "created_at",
    }
    assert table_columns["subtitle_tracks"] == {
        "id",
        "project_id",
        "timeline_id",
        "source",
        "language",
        "style_json",
        "segments_json",
        "status",
        "created_at",
    }
    assert table_columns["assets"] == {
        "id",
        "name",
        "type",
        "source",
        "file_path",
        "file_size_bytes",
        "duration_ms",
        "thumbnail_path",
        "tags",
        "project_id",
        "metadata_json",
        "created_at",
        "updated_at",
    }
    assert table_columns["accounts"] == {
        "id",
        "name",
        "platform",
        "username",
        "avatar_url",
        "status",
        "auth_expires_at",
        "follower_count",
        "following_count",
        "video_count",
        "tags",
        "notes",
        "created_at",
        "updated_at",
    }
    assert table_columns["device_workspaces"] == {
        "id",
        "name",
        "root_path",
        "status",
        "error_count",
        "last_used_at",
        "created_at",
        "updated_at",
    }
    assert table_columns["browser_instances"] == {
        "id",
        "workspace_id",
        "name",
        "profile_path",
        "browser_type",
        "status",
        "last_seen_at",
        "created_at",
        "updated_at",
    }
    assert table_columns["execution_bindings"] == {
        "id",
        "account_id",
        "device_workspace_id",
        "browser_instance_id",
        "status",
        "source",
        "metadata_json",
        "created_at",
        "updated_at",
    }
    assert table_columns["automation_tasks"] == {
        "id",
        "name",
        "type",
        "enabled",
        "cron_expr",
        "last_run_at",
        "last_run_status",
        "run_count",
        "config_json",
        "created_at",
        "updated_at",
    }
    assert table_columns["publish_plans"] == {
        "id",
        "title",
        "account_id",
        "account_name",
        "project_id",
        "video_asset_id",
        "status",
        "scheduled_at",
        "submitted_at",
        "published_at",
        "error_message",
        "precheck_result_json",
        "created_at",
        "updated_at",
    }
    assert table_columns["publish_receipts"] == {
        "id",
        "plan_id",
        "status",
        "external_url",
        "error_message",
        "completed_at",
        "created_at",
    }
    assert table_columns["render_tasks"] == {
        "id",
        "project_id",
        "project_name",
        "preset",
        "format",
        "status",
        "progress",
        "output_path",
        "error_message",
        "started_at",
        "finished_at",
        "created_at",
        "updated_at",
    }
    assert table_columns["export_profiles"] == {
        "id",
        "name",
        "format",
        "resolution",
        "fps",
        "video_bitrate",
        "audio_policy",
        "subtitle_policy",
        "config_json",
        "is_default",
        "created_at",
        "updated_at",
    }
    assert table_columns["video_transcripts"] == {
        "id",
        "imported_video_id",
        "language",
        "text",
        "status",
        "created_at",
        "updated_at",
    }
    assert table_columns["video_segments"] == {
        "id",
        "imported_video_id",
        "segment_index",
        "start_ms",
        "end_ms",
        "label",
        "transcript_text",
        "metadata_json",
        "created_at",
    }
    assert table_columns["video_structure_extractions"] == {
        "id",
        "imported_video_id",
        "status",
        "script_json",
        "storyboard_json",
        "created_at",
        "updated_at",
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
