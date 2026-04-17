from __future__ import annotations

from pathlib import Path

import pytest

from domain.models import Base
from persistence.engine import create_runtime_engine, create_session_factory
from repositories.automation_repository import AutomationRepository
from schemas.automation import AutomationTaskCreateInput, AutomationTaskRuleInput
from services.automation_service import AutomationService


def _make_service(tmp_path: Path) -> AutomationService:
    engine = create_runtime_engine(tmp_path / "runtime.db")
    Base.metadata.create_all(engine)
    return AutomationService(AutomationRepository(session_factory=create_session_factory(engine)))


def test_create_task_serializes_structured_rule_into_config_json(tmp_path: Path) -> None:
    service = _make_service(tmp_path)

    task = service.create_task(
        AutomationTaskCreateInput(
            name="同步素材索引",
            type="sync_index",
            rule=AutomationTaskRuleInput(
                kind="sync",
                config={"projectId": "project-1", "intervalMinutes": 5},
            ),
        )
    )

    assert task.rule is not None
    assert task.rule.kind == "sync"
    assert "project-1" in task.config_json
    assert "intervalMinutes" in task.config_json


def test_pause_and_resume_toggle_enabled_state(tmp_path: Path) -> None:
    service = _make_service(tmp_path)
    created = service.create_task(
        AutomationTaskCreateInput(name="发布检查", type="publish_check")
    )

    paused = service.pause_task(created.id)
    assert paused.enabled is False

    resumed = service.resume_task(created.id)
    assert resumed.enabled is True
