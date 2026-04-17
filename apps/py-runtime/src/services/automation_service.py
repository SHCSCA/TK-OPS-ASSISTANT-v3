from __future__ import annotations

import json
import logging

from fastapi import HTTPException

from common.time import utc_now
from domain.models.automation import AutomationTask, AutomationTaskRun
from repositories.automation_repository import AutomationRepository
from schemas.automation import (
    AutomationTaskCreateInput,
    AutomationTaskDto,
    AutomationTaskRuleDto,
    AutomationTaskRuleInput,
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
            config_json=self._build_config_json(
                rule=payload.rule,
                config_json=payload.config_json,
            ),
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
        rule = changes.pop("rule", None)
        if rule is not None:
            changes["config_json"] = self._build_config_json(
                rule=rule,
                config_json=changes.get("config_json"),
            )
        try:
            task = self._repository.update_task(task_id, **changes)
        except Exception as exc:
            log.exception("更新自动化任务失败")
            raise HTTPException(status_code=500, detail="更新自动化任务失败") from exc
        if task is None:
            raise HTTPException(status_code=404, detail="自动化任务不存在")
        return self._to_task_dto(task)

    def pause_task(self, task_id: str) -> AutomationTaskDto:
        try:
            task = self._repository.set_enabled(task_id, False)
        except Exception as exc:
            log.exception("暂停自动化任务失败")
            raise HTTPException(status_code=500, detail="暂停自动化任务失败") from exc
        if task is None:
            raise HTTPException(status_code=404, detail="自动化任务不存在")
        return self._to_task_dto(task)

    def resume_task(self, task_id: str) -> AutomationTaskDto:
        try:
            task = self._repository.set_enabled(task_id, True)
        except Exception as exc:
            log.exception("恢复自动化任务失败")
            raise HTTPException(status_code=500, detail="恢复自动化任务失败") from exc
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

    def _build_config_json(
        self,
        *,
        rule: AutomationTaskRuleInput | dict[str, object] | None,
        config_json: str | None,
    ) -> str | None:
        if rule is None:
            return config_json
        if isinstance(rule, AutomationTaskRuleInput):
            rule_payload = rule.model_dump(mode="json")
        else:
            rule_payload = rule
        return json.dumps({"rule": rule_payload}, ensure_ascii=False)

    def _parse_rule(self, config_json: str | None) -> AutomationTaskRuleDto | None:
        if not config_json:
            return None
        try:
            payload = json.loads(config_json)
        except json.JSONDecodeError:
            return None
        if isinstance(payload, dict):
            rule_payload = payload.get("rule")
            if isinstance(rule_payload, dict) and "kind" in rule_payload:
                return AutomationTaskRuleDto(**self._normalize_rule(rule_payload))
            if "kind" in payload:
                return AutomationTaskRuleDto(**self._normalize_rule(payload))
        return None

    def _normalize_rule(self, payload: dict[str, object]) -> dict[str, object]:
        config = payload.get("config")
        if not isinstance(config, dict):
            config = {}
        return {
            "kind": str(payload.get("kind", "")),
            "config": config,
        }

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
            rule=self._parse_rule(task.config_json),
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
