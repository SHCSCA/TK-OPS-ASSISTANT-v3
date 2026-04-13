from __future__ import annotations

from pathlib import Path

from domain.models import Base
from persistence.engine import create_runtime_engine, create_session_factory
from repositories.ai_capability_repository import (
    AICapabilityRepository,
    StoredAICapabilityConfig,
)
from repositories.ai_job_repository import AIJobRepository
from repositories.dashboard_repository import DashboardRepository
from repositories.license_repository import LicenseRepository, StoredLicenseGrant
from repositories.script_repository import ScriptRepository
from repositories.storyboard_repository import StoryboardRepository
from repositories.system_config_repository import SystemConfigRepository


def _make_dashboard_repository(tmp_path: Path) -> DashboardRepository:
    engine = create_runtime_engine(tmp_path / "runtime.db")
    Base.metadata.create_all(engine)
    return DashboardRepository(session_factory=create_session_factory(engine))


def _make_session_factory(tmp_path: Path):
    engine = create_runtime_engine(tmp_path / "runtime.db")
    Base.metadata.create_all(engine)
    return create_session_factory(engine)


def test_dashboard_repository_uses_sqlalchemy_session_factory(tmp_path: Path) -> None:
    repository = _make_dashboard_repository(tmp_path)

    project = repository.create_project(name="测试项目", description="描述")
    context = repository.set_current_project(project.id)
    summary = repository.list_recent_projects()

    assert project.name == "测试项目"
    assert context.project_id == project.id
    assert summary[0].id == project.id


def test_dashboard_repository_updates_project_versions(tmp_path: Path) -> None:
    repository = _make_dashboard_repository(tmp_path)
    project = repository.create_project(name="版本项目", description="")

    updated = repository.update_project_versions(
        project.id,
        current_script_version=2,
        current_storyboard_version=1,
    )

    assert updated.current_script_version == 2
    assert updated.current_storyboard_version == 1


def test_script_and_storyboard_repositories_use_sqlalchemy_session_factory(
    tmp_path: Path,
) -> None:
    session_factory = _make_session_factory(tmp_path)
    dashboard = DashboardRepository(session_factory=session_factory)
    script_repository = ScriptRepository(session_factory=session_factory)
    storyboard_repository = StoryboardRepository(session_factory=session_factory)
    project = dashboard.create_project(name="创作链项目", description="")

    script = script_repository.save_version(
        project.id,
        source="manual",
        content="脚本文本",
    )
    storyboard = storyboard_repository.save_version(
        project.id,
        based_on_script_revision=script.revision,
        source="manual",
        scenes=[{"sceneId": "s1", "title": "镜头", "summary": "摘要"}],
    )

    assert script_repository.list_versions(project.id)[0].content == "脚本文本"
    assert storyboard_repository.list_versions(project.id)[0].scenes[0]["title"] == "镜头"
    assert storyboard.based_on_script_revision == 1


def test_ai_repositories_use_sqlalchemy_session_factory(tmp_path: Path) -> None:
    session_factory = _make_session_factory(tmp_path)
    dashboard = DashboardRepository(session_factory=session_factory)
    ai_jobs = AIJobRepository(session_factory=session_factory)
    ai_capabilities = AICapabilityRepository(session_factory=session_factory)
    project = dashboard.create_project(name="AI 项目", description="")

    saved = ai_capabilities.save_capabilities(
        [
            StoredAICapabilityConfig(
                capability_id="script_generation",
                enabled=True,
                provider="openai",
                model="gpt-5.4",
                agent_role="脚本专家",
                system_prompt="生成脚本",
                user_prompt_template="{{topic}}",
                updated_at="2026-04-13T00:00:00Z",
            )
        ]
    )
    provider = ai_capabilities.save_provider_setting("openai", "https://api.openai.com/v1")
    job = ai_jobs.create_running(
        project_id=project.id,
        capability_id="script_generation",
        provider="openai",
        model="gpt-5.4",
    )
    ai_jobs.mark_succeeded(job.id, duration_ms=42)

    assert saved[0].capability_id == "script_generation"
    assert provider.base_url == "https://api.openai.com/v1"
    assert ai_jobs.list_recent(
        project_id=project.id,
        capability_ids=("script_generation",),
    )[0].status == "succeeded"


def test_license_and_system_config_repositories_use_sqlalchemy_session_factory(
    tmp_path: Path,
) -> None:
    session_factory = _make_session_factory(tmp_path)
    licenses = LicenseRepository(session_factory=session_factory)
    settings = SystemConfigRepository(session_factory=session_factory)

    license_grant = licenses.save(
        StoredLicenseGrant(
            active=True,
            restricted_mode=False,
            machine_code="TKOPS-TEST",
            machine_bound=True,
            license_type="perpetual",
            signed_payload="payload.signature",
            masked_code="TKOP...TEST",
            activated_at="2026-04-13T00:00:00Z",
        )
    )
    config = settings.save({"runtime": {"mode": "test"}})

    assert license_grant.active is True
    assert licenses.load() is not None
    assert config.revision == 1
    assert settings.load().document["runtime"]["mode"] == "test"  # type: ignore[union-attr]
