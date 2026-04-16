from __future__ import annotations

import logging

from fastapi import HTTPException

from domain.models.automation import AutomationTask, AutomationTaskRun
from repositories.automation_repository import AutomationRepository
from schemas.automation import (
    AutomationTaskCreateInput,
    AutomationTaskDto,
    AutomationTaskRunDto,
    AutomationTaskUpdateInput,
    TriggerTaskResultDto,
)

log = logging.getLogger(__name__)


class AutomationService:
    def __init__(self, repository: AutomationRepository) -> None:
        self._repository = repository

    def list_tasks(
        self,
        *,
        status: str | None = None,
        type: str | None = None,
    ) -> list[AutomationTaskDto]:
        try:
            tasks = self._repository.list_tasks(status=status, type=type)
        except Exception as exc:
            log.exception("查询自动化任务列表失败")
            raise HTTPException(status_code=500, detail="查询自动化任务列表失败") from exc
        return [self._to_task_dto(task) for task in tasks]

    def create_task(self, payload: AutomationTaskCreateInput) -> AutomationTaskDto:
        task = AutomationTask(
            name=payload.name.strip(),
            type=payload.type,
            cron_expr=payload.cron_expr,
            config_json=payload.config_json,
        )
        try:
            saved = self._repository.create_task(task)
        except Exception as exc:
            log.exception("创建自动化任务失败")
            raise HTTPException(status_code=500, detail="创建自动化任务失败") from exc
        return self._to_task_dto(saved)

    def get_task(self, task_id: str) -> AutomationTaskDto:
        task = self._get_task_model(task_id)
        return self._to_task_dto(task)

    def update_task(
        self,
        task_id: str,
        payload: AutomationTaskUpdateInput,
    ) -> AutomationTaskDto:
        changes = payload.model_dump(exclude_unset=True)
        if "name" in changes and isinstance(changes["name"], str):
            changes["name"] = changes["name"].strip()
        try:
            task = self._repository.update_task(task_id, **changes)
        except Exception as exc:
            log.exception("更新自动化任务失败")
            raise HTTPException(status_code=500, detail="更新自动化任务失败") from exc
        if task is None:
            raise HTTPException(status_code=404, detail="自动化任务不存在")
        return self._to_task_dto(task)

    def delete_task(self, task_id: str) -> None:
        try:
            deleted = self._repository.delete_task(task_id)
        except Exception as exc:
            log.exception("删除自动化任务失败")
            raise HTTPException(status_code=500, detail="删除自动化任务失败") from exc
        if not deleted:
            raise HTTPException(status_code=404, detail="自动化任务不存在")

    def trigger_task(self, task_id: str) -> TriggerTaskResultDto:
        try:
            run = self._repository.trigger_task(task_id)
        except Exception as exc:
            log.exception("触发自动化任务失败")
            raise HTTPException(status_code=500, detail="触发自动化任务失败") from exc
        if run is None:
            raise HTTPException(status_code=404, detail="自动化任务不存在")
        return TriggerTaskResultDto(
            task_id=task_id,
            run_id=run.id,
            status=run.status,
            message="自动化任务已进入运行队列",
        )

    def list_runs(self, task_id: str, limit: int = 20) -> list[AutomationTaskRunDto]:
        self._get_task_model(task_id)
        try:
            runs = self._repository.list_runs(task_id, limit=limit)
        except Exception as exc:
            log.exception("查询自动化任务运行历史失败")
            raise HTTPException(status_code=500, detail="查询自动化任务运行历史失败") from exc
        return [self._to_run_dto(run) for run in runs]

    def _get_task_model(self, task_id: str) -> AutomationTask:
        try:
            task = self._repository.get_task(task_id)
        except Exception as exc:
            log.exception("查询自动化任务详情失败")
            raise HTTPException(status_code=500, detail="查询自动化任务详情失败") from exc
        if task is None:
            raise HTTPException(status_code=404, detail="自动化任务不存在")
        return task

    def _to_task_dto(self, task: AutomationTask) -> AutomationTaskDto:
        return AutomationTaskDto(
            id=task.id,
            name=task.name,
            type=task.type,
            enabled=task.enabled,
            cron_expr=task.cron_expr,
            last_run_at=task.last_run_at,
            last_run_status=task.last_run_status,
            run_count=task.run_count,
            config_json=task.config_json,
            created_at=task.created_at,
            updated_at=task.updated_at,
        )

    def _to_run_dto(self, run: AutomationTaskRun) -> AutomationTaskRunDto:
        return AutomationTaskRunDto(
            id=run.id,
            task_id=run.task_id,
            status=run.status,
            started_at=run.started_at,
            finished_at=run.finished_at,
            log_text=run.log_text,
            created_at=run.created_at,
        )
