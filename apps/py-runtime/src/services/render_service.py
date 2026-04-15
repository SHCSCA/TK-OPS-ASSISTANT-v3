from __future__ import annotations

import logging

from fastapi import HTTPException

from domain.models.render import RenderTask
from repositories.render_repository import RenderRepository
from schemas.renders import (
    CancelRenderResultDto,
    RenderTaskCreateInput,
    RenderTaskDto,
    RenderTaskUpdateInput,
)

log = logging.getLogger(__name__)


class RenderService:
    def __init__(self, repository: RenderRepository) -> None:
        self._repository = repository

    def list_tasks(self, *, status: str | None = None) -> list[RenderTaskDto]:
        try:
            tasks = self._repository.list_tasks(status=status)
        except Exception as exc:
            log.exception("查询渲染任务列表失败")
            raise HTTPException(status_code=500, detail="查询渲染任务列表失败") from exc
        return [self._to_dto(task) for task in tasks]

    def create_task(self, payload: RenderTaskCreateInput) -> RenderTaskDto:
        task = RenderTask(
            project_id=payload.project_id,
            project_name=payload.project_name,
            preset=payload.preset,
            format=payload.format,
        )
        try:
            saved = self._repository.create_task(task)
        except Exception as exc:
            log.exception("创建渲染任务失败")
            raise HTTPException(status_code=500, detail="创建渲染任务失败") from exc
        return self._to_dto(saved)

    def get_task(self, task_id: str) -> RenderTaskDto:
        return self._to_dto(self._get_task_model(task_id))

    def update_task(self, task_id: str, payload: RenderTaskUpdateInput) -> RenderTaskDto:
        try:
            task = self._repository.update_task(
                task_id,
                **payload.model_dump(exclude_unset=True),
            )
        except Exception as exc:
            log.exception("更新渲染任务失败")
            raise HTTPException(status_code=500, detail="更新渲染任务失败") from exc
        if task is None:
            raise HTTPException(status_code=404, detail="渲染任务不存在")
        return self._to_dto(task)

    def delete_task(self, task_id: str) -> None:
        try:
            deleted = self._repository.delete_task(task_id)
        except Exception as exc:
            log.exception("删除渲染任务失败")
            raise HTTPException(status_code=500, detail="删除渲染任务失败") from exc
        if not deleted:
            raise HTTPException(status_code=404, detail="渲染任务不存在")

    def cancel_task(self, task_id: str) -> CancelRenderResultDto:
        task = self._get_task_model(task_id)
        if task.status not in {"queued", "rendering"}:
            raise HTTPException(status_code=409, detail="只有排队中或渲染中的任务可以取消")
        try:
            cancelled = self._repository.cancel_task(task_id)
        except Exception as exc:
            log.exception("取消渲染任务失败")
            raise HTTPException(status_code=500, detail="取消渲染任务失败") from exc
        if cancelled is None:
            raise HTTPException(status_code=404, detail="渲染任务不存在")
        return CancelRenderResultDto(
            task_id=task_id,
            status=cancelled.status,
            message="渲染任务已取消",
        )

    def _get_task_model(self, task_id: str) -> RenderTask:
        try:
            task = self._repository.get_task(task_id)
        except Exception as exc:
            log.exception("查询渲染任务详情失败")
            raise HTTPException(status_code=500, detail="查询渲染任务详情失败") from exc
        if task is None:
            raise HTTPException(status_code=404, detail="渲染任务不存在")
        return task

    def _to_dto(self, task: RenderTask) -> RenderTaskDto:
        return RenderTaskDto(
            id=task.id,
            project_id=task.project_id,
            project_name=task.project_name,
            preset=task.preset,
            format=task.format,
            status=task.status,
            progress=task.progress,
            output_path=task.output_path,
            error_message=task.error_message,
            started_at=task.started_at,
            finished_at=task.finished_at,
            created_at=task.created_at,
            updated_at=task.updated_at,
        )
