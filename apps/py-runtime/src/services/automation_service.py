from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Any

from fastapi import HTTPException

from common.http_errors import RuntimeHTTPException
from common.time import utc_now
from domain.models.automation import AutomationTask, AutomationTaskRun
from repositories.automation_repository import AutomationRepository
from schemas.automation import (
    AutomationTaskCreateInput,
    AutomationTaskDto,
    AutomationTaskLatestResultDto,
    AutomationTaskQueueDto,
    AutomationTaskRetryDto,
    AutomationTaskRuleDto,
    AutomationTaskRuleInput,
    AutomationTaskRunDto,
    AutomationTaskSourceDto,
    AutomationTaskUpdateInput,
    TriggerTaskResultDto,
)
from services.task_manager import ProgressCallback, TaskInfo, TaskManager, task_manager as default_task_manager
from services.ws_manager import ws_manager

log = logging.getLogger(__name__)

_BINDING_REQUIRED_TYPES = {"collect", "reply", "sync", "sync_status", "validate"}
_ACTIVE_STATUSES = {"queued", "running"}
_FAILURE_STATUSES = {"failed", "cancelled", "blocked"}


class AutomationService:
    def __init__(
        self,
        repository: AutomationRepository,
        task_manager: TaskManager | None = None,
    ) -> None:
        self._repository = repository
        self._task_manager = task_manager or default_task_manager

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
        task = self._get_task_model(task_id)
        source = self._build_source(task)
        validation = self._validate_task_dependencies(task, source)
        if validation is not None:
            raise RuntimeHTTPException(
                status_code=409,
                detail=validation["message"],
                error_code=validation["errorCode"],
                details={"nextAction": validation["nextAction"]},
            )

        active_task = self._resolve_active_task(task.id)
        if active_task is not None:
            raise RuntimeHTTPException(
                status_code=409,
                detail="自动化任务正在执行中，请等待当前运行结束。",
                error_code="automation.task_already_running",
                details={"activeRunId": active_task.id},
            )

        try:
            run = self._repository.create_run(
                task.id,
                status="queued",
                log_text="手动触发任务，已进入执行队列。",
            )
        except Exception as exc:
            log.exception("触发自动化任务失败")
            raise HTTPException(status_code=500, detail="触发自动化任务失败") from exc
        if run is None:
            raise HTTPException(status_code=404, detail="自动化任务不存在")

        try:
            task_info = self._task_manager.submit(
                task_type=f"automation.{task.type}",
                project_id=source.projectId,
                task_id=run.id,
                coro_factory=lambda progress: self._execute_run(
                    task_id=task.id,
                    run_id=run.id,
                    progress=progress,
                ),
            )
        except ValueError as exc:
            log.warning("自动化任务已存在活动运行: %s", task.id)
            raise RuntimeHTTPException(
                status_code=409,
                detail="自动化任务正在执行中，请等待当前运行结束。",
                error_code="automation.task_already_running",
            ) from exc
        except Exception as exc:
            log.exception("提交自动化任务到任务总线失败")
            raise HTTPException(status_code=500, detail="提交自动化任务到任务总线失败") from exc

        task_info.owner_ref = {"kind": "automation-task", "id": task.id, "runId": run.id}
        queue_position = self._repository.get_queue_position(run.id)
        self._broadcast_event(
            {
                "type": "automation.task.updated",
                "taskId": task.id,
                "runId": run.id,
                "status": task_info.status,
                "queuePosition": queue_position,
                "source": source.model_dump(mode="json"),
            }
        )
        return TriggerTaskResultDto(
            task_id=task.id,
            run_id=run.id,
            status=task_info.status,
            queueStatus=task_info.status,
            queuePosition=queue_position,
            activeRunId=run.id,
            nextAction="可在运行历史中查看最新状态与执行日志。",
            message="自动化任务已进入执行队列。",
        )

    def list_runs(self, task_id: str, limit: int = 20) -> list[AutomationTaskRunDto]:
        task = self._get_task_model(task_id)
        try:
            runs = self._repository.list_runs(task_id, limit=limit)
        except Exception as exc:
            log.exception("查询自动化任务运行历史失败")
            raise HTTPException(status_code=500, detail="查询自动化任务运行历史失败") from exc
        return [self._to_run_dto(task, run) for run in runs]

    async def _execute_run(
        self,
        *,
        task_id: str,
        run_id: str,
        progress: ProgressCallback,
    ) -> None:
        started_at = utc_now()
        self._repository.update_run(
            run_id,
            status="running",
            started_at=started_at,
            append_log_text="任务开始执行，正在校验自动化配置。",
        )
        self._broadcast_event(
            {
                "type": "automation.task.updated",
                "taskId": task_id,
                "runId": run_id,
                "status": "running",
            }
        )

        await progress(20, "已读取自动化配置。")
        task = self._get_task_model(task_id)
        source = self._build_source(task)
        validation = self._validate_task_dependencies(task, source)
        if validation is not None:
            finished_at = utc_now()
            self._repository.update_run(
                run_id,
                status="failed",
                finished_at=finished_at,
                append_log_text=validation["message"],
            )
            self._broadcast_event(
                {
                    "type": "automation.task.updated",
                    "taskId": task_id,
                    "runId": run_id,
                    "status": "failed",
                    "errorCode": validation["errorCode"],
                    "nextAction": validation["nextAction"],
                }
            )
            raise RuntimeError(validation["message"])

        await progress(60, "已完成执行前检查。")
        await progress(90, "已生成本次执行摘要。")
        finished_at = utc_now()
        self._repository.update_run(
            run_id,
            status="succeeded",
            finished_at=finished_at,
            append_log_text="自动化任务执行完成，本次运行已生成执行回执摘要。",
        )
        self._broadcast_event(
            {
                "type": "automation.task.updated",
                "taskId": task_id,
                "runId": run_id,
                "status": "succeeded",
            }
        )

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
        payload: dict[str, object] = {"rule": rule_payload}
        if config_json:
            parsed = self._parse_json_object(config_json)
            if parsed is not None:
                payload.update(parsed)
        return json.dumps(payload, ensure_ascii=False)

    def _parse_rule(self, config_json: str | None) -> AutomationTaskRuleDto | None:
        if not config_json:
            return None
        payload = self._parse_json_object(config_json)
        if payload is None:
            return None
        if isinstance(payload.get("rule"), dict):
            rule_payload = payload["rule"]
            if "kind" in rule_payload:
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

    def _task_config(self, task: AutomationTask) -> dict[str, object]:
        payload = self._parse_json_object(task.config_json) or {}
        merged: dict[str, object] = {}
        rule_payload = payload.get("rule")
        if isinstance(rule_payload, dict):
            rule_config = rule_payload.get("config")
            if isinstance(rule_config, dict):
                merged.update(rule_config)
        for key, value in payload.items():
            if key == "rule":
                continue
            merged[key] = value
        return merged

    def _parse_json_object(self, raw_value: str | None) -> dict[str, object] | None:
        if not raw_value:
            return None
        try:
            parsed = json.loads(raw_value)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None

    def _to_task_dto(self, task: AutomationTask) -> AutomationTaskDto:
        source = self._build_source(task)
        latest_run = self._repository.get_latest_run(task.id)
        active_task = self._resolve_active_task(task.id)
        queue = self._build_queue(latest_run, active_task)
        latest_result = self._build_latest_result(task, latest_run, active_task)
        retry = self._build_retry(task, source, latest_result, active_task)
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
            source=source,
            queue=queue,
            latestResult=latest_result,
            retry=retry,
            created_at=task.created_at,
            updated_at=task.updated_at,
        )

    def _to_run_dto(self, task: AutomationTask, run: AutomationTaskRun) -> AutomationTaskRunDto:
        source = self._build_source(task)
        validation = self._validate_task_dependencies(task, source)
        error_code = None
        error_message = None
        next_action = None
        retryable = run.status in _FAILURE_STATUSES

        if run.status in _FAILURE_STATUSES and validation is not None:
            error_code = validation["errorCode"]
            error_message = validation["message"]
            next_action = validation["nextAction"]
        elif run.status == "cancelled":
            error_code = "automation.retry_not_supported"
            error_message = "本次自动化任务已取消。"
            next_action = "请重新触发任务，生成新的执行实例。"

        return AutomationTaskRunDto(
            id=run.id,
            task_id=run.task_id,
            status=run.status,
            started_at=run.started_at,
            finished_at=run.finished_at,
            log_text=run.log_text,
            resultSummary=self._summarize_run(run),
            errorCode=error_code,
            errorMessage=error_message,
            retryable=retryable,
            nextAction=next_action,
            created_at=run.created_at,
        )

    def _build_source(self, task: AutomationTask) -> AutomationTaskSourceDto:
        config = self._task_config(task)
        project_id = self._string_or_none(config.get("projectId"))
        account_id = self._string_or_none(config.get("accountId"))
        workspace_id = self._string_or_none(
            config.get("workspaceId") or config.get("browserInstanceId")
        )
        kind = self._string_or_none(config.get("sourceKind"))
        if kind is None:
            rule = self._parse_rule(task.config_json)
            kind = rule.kind if rule is not None else task.type

        object_id = None
        for candidate in (
            "planId",
            "renderTaskId",
            "videoId",
            "timelineId",
            "storyboardId",
            "scriptId",
            "accountId",
            "workspaceId",
            "projectId",
        ):
            object_id = self._string_or_none(config.get(candidate))
            if object_id:
                break

        label = self._string_or_none(config.get("sourceLabel") or config.get("label"))
        if label is None:
            if project_id is not None:
                label = f"项目 {project_id}"
            elif account_id is not None:
                label = f"账号 {account_id}"
            elif workspace_id is not None:
                label = f"工作区 {workspace_id}"
            else:
                label = f"{task.type} 自动化任务"

        return AutomationTaskSourceDto(
            kind=kind,
            objectId=object_id,
            projectId=project_id,
            accountId=account_id,
            workspaceId=workspace_id,
            label=label,
        )

    def _build_queue(
        self,
        latest_run: AutomationTaskRun | None,
        active_task: TaskInfo | None,
    ) -> AutomationTaskQueueDto:
        if active_task is not None:
            position = self._queue_position_from_active_task(active_task)
            return AutomationTaskQueueDto(
                status=active_task.status,
                inQueue=active_task.status in _ACTIVE_STATUSES,
                position=position,
                activeRunId=active_task.id,
                queuedAt=self._parse_datetime(active_task.created_at),
            )
        if latest_run is not None and latest_run.status in _ACTIVE_STATUSES:
            return AutomationTaskQueueDto(
                status=latest_run.status,
                inQueue=True,
                position=self._repository.get_queue_position(latest_run.id),
                activeRunId=latest_run.id,
                queuedAt=latest_run.created_at,
            )
        return AutomationTaskQueueDto(
            status="idle",
            inQueue=False,
            position=None,
            activeRunId=None,
            queuedAt=None,
        )

    def _build_latest_result(
        self,
        task: AutomationTask,
        latest_run: AutomationTaskRun | None,
        active_task: TaskInfo | None,
    ) -> AutomationTaskLatestResultDto:
        if active_task is not None:
            return AutomationTaskLatestResultDto(
                runId=active_task.id,
                status=active_task.status,
                finishedAt=None,
                summary=active_task.message,
                errorCode=None,
                errorMessage=None,
            )
        if latest_run is None:
            return AutomationTaskLatestResultDto(
                runId=None,
                status="idle",
                finishedAt=None,
                summary="尚未触发自动化任务。",
                errorCode=None,
                errorMessage=None,
            )

        validation = self._validate_task_dependencies(task, self._build_source(task))
        error_code = None
        error_message = None
        if latest_run.status in _FAILURE_STATUSES and validation is not None:
            error_code = validation["errorCode"]
            error_message = validation["message"]
        elif latest_run.status == "cancelled":
            error_code = "automation.retry_not_supported"
            error_message = "本次自动化任务已取消。"

        return AutomationTaskLatestResultDto(
            runId=latest_run.id,
            status=latest_run.status,
            finishedAt=latest_run.finished_at,
            summary=self._summarize_run(latest_run),
            errorCode=error_code,
            errorMessage=error_message,
        )

    def _build_retry(
        self,
        task: AutomationTask,
        source: AutomationTaskSourceDto,
        latest_result: AutomationTaskLatestResultDto,
        active_task: TaskInfo | None,
    ) -> AutomationTaskRetryDto:
        if active_task is not None:
            return AutomationTaskRetryDto(
                canRetry=False,
                reason="任务正在排队或执行中，当前不能重复触发。",
                errorCode="automation.task_already_running",
                nextAction="请等待当前运行结束后再重试。",
            )

        validation = self._validate_task_dependencies(task, source)
        if validation is not None:
            return AutomationTaskRetryDto(
                canRetry=False,
                reason=validation["message"],
                errorCode=validation["errorCode"],
                nextAction=validation["nextAction"],
            )

        if latest_result.status in _FAILURE_STATUSES:
            return AutomationTaskRetryDto(
                canRetry=True,
                reason="最近一次运行失败，可在修复问题后重新触发。",
                errorCode=latest_result.errorCode,
                nextAction=self._retry_next_action(latest_result.errorCode),
            )

        if latest_result.status == "succeeded":
            return AutomationTaskRetryDto(
                canRetry=False,
                reason="最近一次运行已成功完成。",
                errorCode=None,
                nextAction="如需再次执行，可手动重新触发任务。",
            )

        return AutomationTaskRetryDto(
            canRetry=False,
            reason="任务尚未进入可重试状态。",
            errorCode=None,
            nextAction="请先触发一次自动化任务。",
        )

    def _validate_task_dependencies(
        self,
        task: AutomationTask,
        source: AutomationTaskSourceDto,
    ) -> dict[str, str] | None:
        if not task.enabled:
            return {
                "errorCode": "automation.task_disabled",
                "message": "自动化任务已停用，当前无法触发。",
                "nextAction": "请先恢复任务开关，再重新触发。",
            }

        rule = self._parse_rule(task.config_json)
        config = self._task_config(task)
        if rule is None and not config:
            return {
                "errorCode": "automation.config_missing",
                "message": "自动化任务缺少执行配置，当前无法触发。",
                "nextAction": "请补齐任务规则或执行参数后再重试。",
            }

        has_binding = bool(source.accountId or source.workspaceId)
        if task.type in _BINDING_REQUIRED_TYPES and not has_binding:
            return {
                "errorCode": "automation.binding_required",
                "message": "自动化任务缺少执行绑定，当前无法触发。",
                "nextAction": "请在配置里补齐账号或工作区绑定后再重试。",
            }

        return None

    def _retry_next_action(self, error_code: str | None) -> str:
        if error_code == "automation.config_missing":
            return "请先补齐任务规则或执行参数，再重新触发。"
        if error_code == "automation.binding_required":
            return "请先补齐账号或工作区绑定，再重新触发。"
        if error_code == "automation.task_disabled":
            return "请先恢复任务开关，再重新触发。"
        return "请检查最近一次运行日志后，再重新触发任务。"

    def _resolve_active_task(self, task_id: str) -> TaskInfo | None:
        for task_info in self._task_manager.list_active():
            owner_ref = getattr(task_info, "owner_ref", None)
            if not isinstance(owner_ref, dict):
                continue
            if owner_ref.get("kind") != "automation-task":
                continue
            if str(owner_ref.get("id")) != task_id:
                continue
            return task_info
        return None

    def _queue_position_from_active_task(self, task_info: TaskInfo) -> int | None:
        if task_info.status != "queued":
            return None
        queued_tasks = [
            task
            for task in self._task_manager.list_active()
            if task.status == "queued"
        ]
        queued_tasks.sort(key=lambda item: item.created_at)
        for index, item in enumerate(queued_tasks, start=1):
            if item.id == task_info.id:
                return index
        return None

    def _parse_datetime(self, value: str | None) -> Any:
        if not value:
            return None
        try:
            normalized = value.replace("Z", "+00:00")
            return datetime.fromisoformat(normalized)
        except ValueError:
            return None

    def _summarize_run(self, run: AutomationTaskRun) -> str:
        if run.log_text:
            lines = [
                line.strip() for line in run.log_text.splitlines() if line.strip()
            ]
            if lines:
                return lines[-1]
        if run.status == "queued":
            return "任务已进入执行队列。"
        if run.status == "running":
            return "任务正在执行中。"
        if run.status == "succeeded":
            return "最近一次运行已成功完成。"
        if run.status == "cancelled":
            return "最近一次运行已取消。"
        return "最近一次运行失败。"

    def _string_or_none(self, value: object) -> str | None:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return None

    def _broadcast_event(self, event: dict[str, object]) -> None:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return
        asyncio.create_task(ws_manager.broadcast(event))
