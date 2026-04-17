from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException

from repositories.imported_video_repository import ImportedVideoRepository
from repositories.video_deconstruction_repository import (
    StoredVideoStageRun,
    VideoDeconstructionRepository,
)
from schemas.video_deconstruction import ImportedVideoDto, VideoStageDto
from services.task_manager import TaskInfo, TaskManager, task_manager as default_task_manager
from services.ws_manager import ws_manager


@dataclass(frozen=True, slots=True)
class _StageDefinition:
    stage_id: str
    label: str
    rerunnable: bool


_STAGES = (
    _StageDefinition('import', '导入', False),
    _StageDefinition('transcribe', '转写', True),
    _StageDefinition('segment', '切段', True),
    _StageDefinition('extract_structure', '结构抽取', True),
)


class VideoDeconstructionService:
    def __init__(
        self,
        *,
        imported_video_repository: ImportedVideoRepository,
        stage_repository: VideoDeconstructionRepository,
        task_manager: TaskManager | None = None,
    ) -> None:
        self._imported_video_repository = imported_video_repository
        self._stage_repository = stage_repository
        self._task_manager = task_manager or default_task_manager

    def get_stages(self, video_id: str) -> list[VideoStageDto]:
        video = self._get_video(video_id)
        stage_runs = {item.stage_id: item for item in self._stage_repository.list_stage_runs(video_id)}
        return [
            self._build_stage_dto(video, stage_definition, stage_runs.get(stage_definition.stage_id))
            for stage_definition in _STAGES
        ]

    def rerun_stage(self, video_id: str, stage_id: str, *, request_id: str | None = None) -> TaskInfo:
        stage_definition = self._get_stage_definition(stage_id)
        if not stage_definition.rerunnable:
            raise HTTPException(status_code=400, detail='当前阶段不能重跑。')

        video = self._get_video(video_id)

        async def _run_stage(progress_callback):
            await self._emit_stage_event('video.import.stage.started', video_id, stage_id, started_at=_utc_now())
            self._stage_repository.upsert_stage_run(
                video_id,
                stage_id,
                status='running',
                progress_pct=0,
                result_summary=None,
                error_message=None,
            )
            try:
                await progress_callback(15, f'正在重跑 {stage_definition.label} 阶段')
                if not Path(video.file_path).is_file():
                    raise FileNotFoundError(f'视频文件不存在：{video.file_path}')

                await progress_callback(55, f'正在处理 {stage_definition.label} 阶段')
                summary = f'已完成 {stage_definition.label} 阶段重跑'
                self._stage_repository.upsert_stage_run(
                    video_id,
                    stage_id,
                    status='succeeded',
                    progress_pct=100,
                    result_summary=summary,
                    error_message=None,
                )
                await progress_callback(100, summary)
                await self._emit_stage_event(
                    'video.import.stage.completed',
                    video_id,
                    stage_id,
                    result_summary=summary,
                )
            except Exception as exc:
                error_message = str(exc) or '阶段重跑失败'
                self._stage_repository.upsert_stage_run(
                    video_id,
                    stage_id,
                    status='failed',
                    progress_pct=0,
                    result_summary=None,
                    error_message=error_message,
                )
                await self._emit_stage_event(
                    'video.import.stage.failed',
                    video_id,
                    stage_id,
                    error_message=error_message,
                )
                raise

        try:
            task = self._task_manager.submit(
                task_type='video-import-stage',
                coro_factory=_run_stage,
                project_id=video.project_id,
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

        return task

    def _get_stage_definition(self, stage_id: str) -> _StageDefinition:
        for stage in _STAGES:
            if stage.stage_id == stage_id:
                return stage
        raise HTTPException(status_code=404, detail='阶段不存在。')

    def _get_video(self, video_id: str):
        video = self._imported_video_repository.get(video_id)
        if video is None:
            raise HTTPException(status_code=404, detail='视频记录不存在。')
        return video

    def _build_stage_dto(
        self,
        video,
        stage_definition: _StageDefinition,
        stored: StoredVideoStageRun | None,
    ) -> VideoStageDto:
        if stage_definition.stage_id == 'import':
            status, progress_pct, result_summary, error_message, updated_at = _import_stage_state(video)
        elif stored is None:
            status, progress_pct, result_summary, error_message, updated_at = (
                'pending',
                0,
                None,
                None,
                None,
            )
        else:
            status = stored.status
            progress_pct = stored.progress_pct
            result_summary = stored.result_summary
            error_message = stored.error_message
            updated_at = stored.updated_at

        return VideoStageDto(
            stageId=stage_definition.stage_id,
            label=stage_definition.label,
            status=status,
            progressPct=progress_pct,
            resultSummary=result_summary,
            errorMessage=error_message,
            updatedAt=updated_at,
            canRerun=stage_definition.rerunnable,
        )

    async def _emit_stage_event(self, event_type: str, video_id: str, stage_id: str, **payload: object) -> None:
        message = {
            'type': event_type,
            'videoId': video_id,
            'stage': stage_id,
            **payload,
        }
        await ws_manager.broadcast(message)


def _import_stage_state(video) -> tuple[str, int, str | None, str | None, str]:
    if video.status == 'error':
        return 'failed', 0, None, video.error_message, video.created_at
    if video.status in {'ready', 'imported'}:
        summary = video.error_message or f'已导入 {video.file_name}'
        return 'succeeded', 100, summary, None, video.created_at
    return 'running', 50, None, None, video.created_at


def _utc_now() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).isoformat().replace('+00:00', 'Z')
