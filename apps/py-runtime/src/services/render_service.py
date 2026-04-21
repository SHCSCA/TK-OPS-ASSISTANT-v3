from __future__ import annotations

import asyncio
import logging
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path

from fastapi import HTTPException

from common.http_errors import RuntimeHTTPException
from common.time import utc_now
from domain.models.render import ExportProfile, RenderTask
from repositories.render_repository import RenderRepository
from schemas.renders import (
    CancelRenderResultDto,
    DiskUsageSnapshotDto,
    ExportProfileCreateInput,
    ExportProfileDto,
    RenderFailureDto,
    RenderOutputStatusDto,
    RenderResourceUsageDto,
    RenderStageDto,
    RenderSuggestedActionDto,
    RenderTaskCreateInput,
    RenderTaskDto,
    RenderTaskUpdateInput,
    UsageSnapshotDto,
)
from services.ws_manager import ws_manager

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
        if payload.progress is not None:
            self._broadcast_render_progress(task)
        if any(
            field in payload.model_fields_set
            for field in ("status", "output_path", "error_message", "progress")
        ):
            self._broadcast_render_status(task)
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
            raise RuntimeHTTPException(
                status_code=409,
                detail="只有排队中或渲染中的任务可以取消。",
                error_code="render.task_not_cancellable",
            )
        try:
            cancelled = self._repository.cancel_task(task_id)
        except Exception as exc:
            log.exception("取消渲染任务失败")
            raise HTTPException(status_code=500, detail="取消渲染任务失败") from exc
        if cancelled is None:
            raise HTTPException(status_code=404, detail="渲染任务不存在")
        self._broadcast_render_status(cancelled)
        return CancelRenderResultDto(
            task_id=task_id,
            status=cancelled.status,
            message="渲染任务已取消。",
        )

    def retry_task(self, task_id: str) -> RenderTaskDto:
        task = self._get_task_model(task_id)
        if task.status not in {"failed", "cancelled"}:
            raise RuntimeHTTPException(
                status_code=409,
                detail="只有失败或已取消的任务可以重试。",
                error_code="render.task_not_retryable",
            )
        try:
            retried = self._repository.retry_task(task_id)
        except Exception as exc:
            log.exception("重试渲染任务失败")
            raise HTTPException(status_code=500, detail="重试渲染任务失败") from exc
        if retried is None:
            raise HTTPException(status_code=404, detail="渲染任务不存在")
        self._broadcast_render_status(retried)
        return self._to_dto(retried)

    def list_profiles(self) -> list[ExportProfileDto]:
        try:
            profiles = self._repository.list_profiles()
            if not profiles:
                profiles = [self._repository.create_profile(self._build_default_profile())]
        except Exception as exc:
            log.exception("查询导出模板失败")
            raise HTTPException(status_code=500, detail="查询导出模板失败") from exc
        return [self._to_profile_dto(profile) for profile in profiles]

    def list_templates(self) -> list[ExportProfileDto]:
        return self.list_profiles()

    def create_profile(self, payload: ExportProfileCreateInput) -> ExportProfileDto:
        name = payload.name.strip()
        if not name:
            raise HTTPException(status_code=400, detail="模板名称不能为空。")
        profile = ExportProfile(
            name=name,
            format=payload.format,
            resolution=payload.resolution,
            fps=payload.fps,
            video_bitrate=payload.video_bitrate,
            audio_policy=payload.audio_policy,
            subtitle_policy=payload.subtitle_policy,
            config_json=payload.config_json,
            is_default=False,
        )
        try:
            saved = self._repository.create_profile(profile)
        except Exception as exc:
            log.exception("创建导出模板失败")
            raise HTTPException(status_code=500, detail="创建导出模板失败") from exc
        return self._to_profile_dto(saved)

    def fetch_resource_usage(self) -> RenderResourceUsageDto:
        cpu = self._fetch_cpu_usage()
        gpu = UsageSnapshotDto(
            status="unavailable",
            usagePct=None,
            message="当前未接入 GPU 监控能力。",
        )
        disk_usage = shutil.disk_usage(Path.cwd())
        disk = DiskUsageSnapshotDto(
            status="ready",
            path=str(Path.cwd()),
            totalBytes=disk_usage.total,
            usedBytes=disk_usage.used,
            freeBytes=disk_usage.free,
            usagePct=round(disk_usage.used / disk_usage.total * 100, 2)
            if disk_usage.total
            else None,
            message="磁盘占用统计已读取。",
        )
        return RenderResourceUsageDto(
            cpu=cpu,
            gpu=gpu,
            disk=disk,
            collectedAt=datetime.now(UTC),
        )

    def _fetch_cpu_usage(self) -> UsageSnapshotDto:
        try:
            load1, _, _ = os.getloadavg()
            cpu_count = os.cpu_count() or 1
            usage_pct = round(min(100.0, load1 / cpu_count * 100.0), 2)
            return UsageSnapshotDto(
                status="ready",
                usagePct=usage_pct,
                message="CPU 负载已读取。",
            )
        except (AttributeError, OSError):
            return UsageSnapshotDto(
                status="unavailable",
                usagePct=None,
                message="当前未接入 CPU 采样能力。",
            )

    def _broadcast_render_progress(self, task: RenderTask) -> None:
        event = {
            "type": "render.progress",
            "taskId": task.id,
            "progressPct": task.progress,
            "bitrateKbps": None,
            "outputSec": None,
        }
        self._broadcast_event(event)

    def _broadcast_render_status(self, task: RenderTask) -> None:
        dto = self._to_dto(task)
        event = {
            "type": "render.status.changed",
            "taskId": task.id,
            "status": dto.status,
            "stage": dto.stage.model_dump(mode="json"),
            "output": dto.output.model_dump(mode="json"),
            "failure": dto.failure.model_dump(mode="json"),
        }
        self._broadcast_event(event)

    def _broadcast_event(self, event: dict[str, object]) -> None:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(ws_manager.broadcast(event))
        else:
            asyncio.create_task(ws_manager.broadcast(event))

    def _get_task_model(self, task_id: str) -> RenderTask:
        try:
            task = self._repository.get_task(task_id)
        except Exception as exc:
            log.exception("查询渲染任务详情失败")
            raise HTTPException(status_code=500, detail="查询渲染任务详情失败") from exc
        if task is None:
            raise HTTPException(status_code=404, detail="渲染任务不存在")
        return task

    def _build_default_profile(self) -> ExportProfile:
        return ExportProfile(
            name="默认竖屏导出",
            format="mp4",
            resolution="1080x1920",
            fps=30,
            video_bitrate="8000k",
            audio_policy="merge_all",
            subtitle_policy="burn_in",
            config_json=None,
            is_default=True,
        )

    def _to_dto(self, task: RenderTask) -> RenderTaskDto:
        stage = self._build_stage(task)
        output = self._build_output_status(task)
        failure = self._build_failure(task, output)
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
            stage=stage,
            output=output,
            failure=failure,
            started_at=task.started_at,
            finished_at=task.finished_at,
            created_at=task.created_at,
            updated_at=task.updated_at,
        )

    def _build_stage(self, task: RenderTask) -> RenderStageDto:
        if task.status == "queued":
            return RenderStageDto(code="queued", label="排队中")
        if task.status == "rendering":
            if task.progress >= 90 and task.output_path:
                return RenderStageDto(code="exporting", label="导出中")
            return RenderStageDto(code="rendering", label="渲染中")
        if task.status == "completed":
            return RenderStageDto(code="completed", label="已完成")
        if task.status == "failed":
            return RenderStageDto(code="failed", label="失败")
        if task.status == "cancelled":
            return RenderStageDto(code="cancelled", label="已取消")
        return RenderStageDto(code=task.status, label="状态未知")

    def _build_output_status(self, task: RenderTask) -> RenderOutputStatusDto:
        checked_at = datetime.now(UTC)
        if not task.output_path:
            return RenderOutputStatusDto(
                path=None,
                exists=False,
                size_bytes=None,
                last_checked_at=checked_at,
                can_open=False,
            )

        output_path = Path(task.output_path)
        exists = output_path.exists()
        size_bytes = output_path.stat().st_size if exists else None
        return RenderOutputStatusDto(
            path=str(output_path),
            exists=exists,
            size_bytes=size_bytes,
            last_checked_at=checked_at,
            can_open=exists,
        )

    def _build_failure(
        self,
        task: RenderTask,
        output: RenderOutputStatusDto,
    ) -> RenderFailureDto:
        if task.status == "failed":
            return RenderFailureDto(
                error_code="render.task_failed",
                error_message=task.error_message or "渲染任务执行失败。",
                next_action=RenderSuggestedActionDto(
                    key="retry-render",
                    label="重新渲染",
                ),
                retryable=True,
            )
        if task.status == "cancelled":
            return RenderFailureDto(
                error_code="render.task_cancelled",
                error_message="渲染任务已取消。",
                next_action=RenderSuggestedActionDto(
                    key="retry-render",
                    label="重新渲染",
                ),
                retryable=True,
            )
        if task.status == "completed" and output.path and not output.exists:
            return RenderFailureDto(
                error_code="render.output_not_found",
                error_message="渲染任务已完成，但输出文件不存在。",
                next_action=RenderSuggestedActionDto(
                    key="verify-output",
                    label="检查输出目录",
                ),
                retryable=True,
            )
        return RenderFailureDto(
            error_code=None,
            error_message=None,
            next_action=None,
            retryable=False,
        )

    def _to_profile_dto(self, profile: ExportProfile) -> ExportProfileDto:
        return ExportProfileDto(
            id=profile.id,
            name=profile.name,
            format=profile.format,
            resolution=profile.resolution,
            fps=profile.fps,
            video_bitrate=profile.video_bitrate,
            audio_policy=profile.audio_policy,
            subtitle_policy=profile.subtitle_policy,
            config_json=profile.config_json,
            is_default=profile.is_default,
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        )
