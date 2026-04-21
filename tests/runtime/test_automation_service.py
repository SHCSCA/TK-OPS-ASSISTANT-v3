from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest

from common.http_errors import RuntimeHTTPException
from domain.models import Base
from persistence.engine import create_runtime_engine, create_session_factory
from repositories.automation_repository import AutomationRepository
from schemas.automation import AutomationTaskCreateInput, AutomationTaskRuleInput
from services.automation_service import AutomationService


class DeferredTaskManager:
    def __init__(self) -> None:
        self._tasks: dict[str, SimpleNamespace] = {}
        self._coroutines: dict[str, object] = {}

    def submit(
        self,
        *,
        task_type: str,
        coro_factory,
        project_id: str | None = None,
        task_id: str | None = None,
    ) -> SimpleNamespace:
        if task_id is None:
            raise AssertionError("tests require explicit task_id")
        existing = self._tasks.get(task_id)
        if existing is not None and existing.status in {"queued", "running"}:
            raise ValueError("任务已存在")

        task = SimpleNamespace(
            id=task_id,
            task_type=task_type,
            project_id=project_id,
            status="queued",
            progress=0,
            message="任务已排队。",
            created_at="2026-04-21T00:00:00+00:00",
            updated_at="2026-04-21T00:00:00+00:00",
        )
        self._tasks[task_id] = task
        self._coroutines[task_id] = coro_factory
        return task

    def list_active(self) -> list[SimpleNamespace]:
        return [
            task
            for task in self._tasks.values()
            if task.status in {"queued", "running"}
        ]

    def run(self, task_id: str) -> None:
        task = self._tasks[task_id]
        coro_factory = self._coroutines[task_id]

        async def progress(progress_value: int, message: str) -> None:
            task.status = "running"
            task.progress = progress_value
            task.message = message

        async def runner() -> None:
            task.status = "running"
            task.message = "任务已开始。"
            try:
                await coro_factory(progress)
                task.status = "succeeded"
                task.progress = 100
                task.message = "任务已完成。"
            except Exception as exc:  # pragma: no cover - exercised in tests
                task.status = "failed"
                task.message = str(exc)

        asyncio.run(runner())


def _make_service(
    tmp_path: Path,
    *,
    task_manager: DeferredTaskManager | None = None,
) -> tuple[AutomationService, DeferredTaskManager]:
    engine = create_runtime_engine(tmp_path / "runtime.db")
    Base.metadata.create_all(engine)
    resolved_task_manager = task_manager or DeferredTaskManager()
    service = AutomationService(
        AutomationRepository(session_factory=create_session_factory(engine)),
        task_manager=resolved_task_manager,
    )
    return service, resolved_task_manager


def test_create_task_serializes_structured_rule_into_config_json(tmp_path: Path) -> None:
    service, _ = _make_service(tmp_path)

    task = service.create_task(
        AutomationTaskCreateInput(
            name="同步素材索引",
            type="sync",
            rule=AutomationTaskRuleInput(
                kind="interval",
                config={
                    "projectId": "project-1",
                    "workspaceId": "workspace-1",
                    "intervalMinutes": 5,
                },
            ),
        )
    )

    assert task.rule is not None
    assert task.rule.kind == "interval"
    assert task.source.projectId == "project-1"
    assert task.source.workspaceId == "workspace-1"
    assert task.retry.errorCode is None
    assert "intervalMinutes" in (task.config_json or "")


def test_pause_and_resume_toggle_enabled_state(tmp_path: Path) -> None:
    service, _ = _make_service(tmp_path)
    created = service.create_task(
        AutomationTaskCreateInput(
            name="发布前检查",
            type="publish_check",
            config_json='{"accountId":"account-1"}',
        )
    )

    paused = service.pause_task(created.id)
    assert paused.enabled is False
    assert paused.retry.errorCode == "automation.task_disabled"

    resumed = service.resume_task(created.id)
    assert resumed.enabled is True
    assert resumed.retry.errorCode is None


def test_trigger_task_creates_queued_run_and_completed_result(tmp_path: Path) -> None:
    service, task_manager = _make_service(tmp_path)
    task = service.create_task(
        AutomationTaskCreateInput(
            name="同步发布状态",
            type="sync_status",
            config_json='{"projectId":"project-1","workspaceId":"workspace-1"}',
        )
    )

    trigger_result = service.trigger_task(task.id)

    assert trigger_result.queueStatus == "queued"
    assert trigger_result.activeRunId == trigger_result.run_id

    task_manager.run(trigger_result.run_id)

    fetched = service.get_task(task.id)
    assert fetched.latestResult.status == "succeeded"
    assert fetched.latestResult.summary == "自动化任务执行完成，本次运行已生成执行回执摘要。"
    runs = service.list_runs(task.id)
    assert len(runs) == 1
    assert runs[0].status == "succeeded"
    assert runs[0].resultSummary == "自动化任务执行完成，本次运行已生成执行回执摘要。"


def test_trigger_task_returns_binding_required_when_binding_missing(tmp_path: Path) -> None:
    service, _ = _make_service(tmp_path)
    task = service.create_task(
        AutomationTaskCreateInput(
            name="同步账号状态",
            type="sync_status",
            config_json='{"projectId":"project-1"}',
        )
    )

    with pytest.raises(RuntimeHTTPException) as exc_info:
        service.trigger_task(task.id)

    assert exc_info.value.status_code == 409
    assert exc_info.value.error_code == "automation.binding_required"


def test_trigger_task_returns_conflict_when_active_run_exists(tmp_path: Path) -> None:
    service, _ = _make_service(tmp_path)
    task = service.create_task(
        AutomationTaskCreateInput(
            name="同步工作区任务",
            type="sync",
            config_json='{"workspaceId":"workspace-1"}',
        )
    )

    first = service.trigger_task(task.id)

    with pytest.raises(RuntimeHTTPException) as exc_info:
        service.trigger_task(task.id)

    assert first.queueStatus == "queued"
    assert exc_info.value.status_code == 409
    assert exc_info.value.error_code == "automation.task_already_running"


def test_list_runs_honors_limit_and_returns_latest_first(tmp_path: Path) -> None:
    service, task_manager = _make_service(tmp_path)
    task = service.create_task(
        AutomationTaskCreateInput(
            name="校验账号绑定",
            type="validate",
            config_json='{"workspaceId":"workspace-1"}',
        )
    )

    first = service.trigger_task(task.id)
    task_manager.run(first.run_id)
    second = service.trigger_task(task.id)
    task_manager.run(second.run_id)

    runs = service.list_runs(task.id, limit=1)

    assert len(runs) == 1
    assert runs[0].id == second.run_id
