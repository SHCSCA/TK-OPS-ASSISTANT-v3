from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException

from repositories.imported_video_repository import ImportedVideoRepository
from repositories.script_repository import ScriptRepository
from repositories.storyboard_repository import StoryboardRepository
from repositories.video_deconstruction_repository import (
    StoredVideoStageRun,
    VideoDeconstructionRepository,
)
from schemas.video_deconstruction import (
    ApplyVideoExtractionResultDto,
    VideoSegmentDto,
    VideoStageDto,
    VideoStructureExtractionDto,
    VideoTranscriptDto,
)
from services.dashboard_service import DashboardService
from services.task_manager import TaskInfo, TaskManager, task_manager as default_task_manager
from services.ws_manager import ws_manager

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class _StageDefinition:
    stage_id: str
    label: str
    rerunnable: bool


@dataclass(frozen=True, slots=True)
class _ResolvedStageState:
    stage_id: str
    status: str
    progress_pct: int
    result_summary: str | None
    error_message: str | None
    updated_at: str | None
    error_code: str | None
    next_action: str | None
    blocked_by_stage_id: str | None
    active_task: TaskInfo | None


_IMPORT_STAGE_ID = "import"
_TRANSCRIPT_STAGE_ID = "transcribe"
_SEGMENT_STAGE_ID = "segment"
_STRUCTURE_STAGE_ID = "extract_structure"
_PROVIDER_REQUIRED_STATUS = "provider_required"
_BLOCKED_STATUS = "blocked"
_ACTIVE_TASK_STATUSES = {"queued", "running"}
_RETRYABLE_STAGE_STATUSES = {"failed", _BLOCKED_STATUS, _PROVIDER_REQUIRED_STATUS, "cancelled"}

_PROVIDER_REQUIRED_MESSAGE = "当前未接入可用转录 Provider，转录已阻塞；接入 Provider 后可重试。"
_SEGMENT_BLOCKED_MESSAGE = "视频转录尚未成功，分段已阻塞；请先完成转录后重试。"
_STRUCTURE_BLOCKED_MESSAGE = "视频分段尚未成功，结构提取已阻塞；请先完成分段后重试。"
_APPLY_BLOCKED_MESSAGE = "视频结构提取尚未成功，无法应用到项目；请先完成结构提取后重试。"

_STAGES = (
    _StageDefinition(_IMPORT_STAGE_ID, "导入", False),
    _StageDefinition(_TRANSCRIPT_STAGE_ID, "转录", True),
    _StageDefinition(_SEGMENT_STAGE_ID, "分段", True),
    _StageDefinition(_STRUCTURE_STAGE_ID, "结构提取", True),
)
_STAGE_ORDER = {item.stage_id: index for index, item in enumerate(_STAGES)}


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
        active_tasks = self._list_active_stage_tasks(video_id)

        resolved_states = [
            self._resolve_stage_state(
                video,
                stage_definition,
                stage_runs.get(stage_definition.stage_id),
                active_tasks.get(stage_definition.stage_id),
            )
            for stage_definition in _STAGES
        ]
        current_stage_id = self._resolve_current_stage_id(resolved_states)

        return [
            self._build_stage_dto(
                stage_definition,
                resolved_state,
                is_current=stage_definition.stage_id == current_stage_id,
            )
            for stage_definition, resolved_state in zip(_STAGES, resolved_states, strict=True)
        ]

    def start_transcription(self, video_id: str) -> VideoTranscriptDto:
        try:
            video = self._get_video(video_id)
            stored = self._resolve_transcription_stage(video_id)
            return self._build_transcript_dto(video, stored)
        except HTTPException:
            raise
        except Exception as exc:
            log.exception("启动视频转录失败: %s", video_id)
            raise HTTPException(status_code=500, detail="启动视频转录失败") from exc

    def get_transcript(self, video_id: str) -> VideoTranscriptDto:
        try:
            video = self._get_video(video_id)
            stored = self._resolve_transcription_stage(video_id)
            return self._build_transcript_dto(video, stored)
        except HTTPException:
            raise
        except Exception as exc:
            log.exception("查询视频转录状态失败: %s", video_id)
            raise HTTPException(status_code=500, detail="查询视频转录状态失败") from exc

    def run_segmentation(self, video_id: str) -> list[VideoSegmentDto]:
        try:
            video = self._get_video(video_id)
            self._require_stage_succeeded(
                video_id,
                _TRANSCRIPT_STAGE_ID,
                _SEGMENT_BLOCKED_MESSAGE,
                blocked_stage_id=_SEGMENT_STAGE_ID,
                blocked_message=_SEGMENT_BLOCKED_MESSAGE,
            )
            segments = self._build_segments(video)
            self._upsert_stage_run(
                video_id,
                _SEGMENT_STAGE_ID,
                status="succeeded",
                progress_pct=100,
                result_summary=f"已生成 {len(segments)} 个基础切段",
                error_message=None,
            )
            return segments
        except HTTPException:
            raise
        except Exception as exc:
            log.exception("执行视频分段失败: %s", video_id)
            raise HTTPException(status_code=500, detail="执行视频分段失败") from exc

    def get_segments(self, video_id: str) -> list[VideoSegmentDto]:
        video = self._get_video(video_id)
        stored = self._stage_repository.get_stage_run(video_id, _SEGMENT_STAGE_ID)
        if stored is None or stored.status != "succeeded":
            return []
        return self._build_segments(video)

    def extract_structure(self, video_id: str) -> VideoStructureExtractionDto:
        try:
            video = self._get_video(video_id)
            self._require_stage_succeeded(
                video_id,
                _SEGMENT_STAGE_ID,
                _STRUCTURE_BLOCKED_MESSAGE,
                blocked_stage_id=_STRUCTURE_STAGE_ID,
                blocked_message=_STRUCTURE_BLOCKED_MESSAGE,
            )
            stored = self._upsert_stage_run(
                video_id,
                _STRUCTURE_STAGE_ID,
                status="succeeded",
                progress_pct=100,
                result_summary="已生成脚本和分镜结构草稿",
                error_message=None,
            )
            return self._build_structure_dto(video, stored)
        except HTTPException:
            raise
        except Exception as exc:
            log.exception("执行视频结构提取失败: %s", video_id)
            raise HTTPException(status_code=500, detail="执行视频结构提取失败") from exc

    def get_structure(self, video_id: str) -> VideoStructureExtractionDto:
        video = self._get_video(video_id)
        stored = self._stage_repository.get_stage_run(video_id, _STRUCTURE_STAGE_ID)
        return self._build_structure_dto(video, stored)

    def apply_extraction_to_project(
        self,
        extraction_id: str,
        *,
        dashboard_service: DashboardService,
        script_repository: ScriptRepository,
        storyboard_repository: StoryboardRepository,
    ) -> ApplyVideoExtractionResultDto:
        try:
            video_id = self._parse_extraction_id(extraction_id)
            video = self._get_video(video_id)
            self._require_stage_succeeded(video_id, _STRUCTURE_STAGE_ID, _APPLY_BLOCKED_MESSAGE)

            project = dashboard_service.require_project(video.project_id)
            script_version = script_repository.save_version(
                project.id,
                source="video_extraction",
                content=self._build_script_content(video),
            )
            storyboard_version = storyboard_repository.save_version(
                project.id,
                based_on_script_revision=script_version.revision,
                source="video_extraction",
                scenes=self._build_storyboard_scenes(video),
            )
            dashboard_service.update_project_versions(
                project.id,
                current_script_version=script_version.revision,
                current_storyboard_version=storyboard_version.revision,
            )
            return ApplyVideoExtractionResultDto(
                projectId=project.id,
                extractionId=extraction_id,
                scriptRevision=script_version.revision,
                status="applied",
                message="已将视频拆解结构写回项目。",
            )
        except HTTPException:
            raise
        except Exception as exc:
            log.exception("应用视频结构到项目失败: %s", extraction_id)
            raise HTTPException(status_code=500, detail="应用视频结构到项目失败") from exc

    def rerun_stage(self, video_id: str, stage_id: str, *, request_id: str | None = None) -> TaskInfo:
        stage_definition = self._get_stage_definition(stage_id)
        if not stage_definition.rerunnable:
            raise HTTPException(status_code=400, detail="当前阶段不能重跑。")

        video = self._get_video(video_id)
        task_id = f"video-stage-{uuid4()}"
        owner_ref = _stage_owner_ref(video_id, stage_id)

        async def _run_stage(progress_callback):
            await self._emit_stage_event(
                "video.import.stage.started",
                video_id,
                stage_id,
                taskId=task_id,
                ownerRef=owner_ref,
                startedAt=_utc_now(),
            )
            self._upsert_stage_run(
                video_id,
                stage_id,
                status="running",
                progress_pct=0,
                result_summary=None,
                error_message=None,
            )
            try:
                await progress_callback(15, f"正在重跑 {stage_definition.label} 阶段")
                if not Path(video.file_path).is_file():
                    raise FileNotFoundError(f"视频文件不存在：{video.file_path}")

                if stage_id == _TRANSCRIPT_STAGE_ID:
                    await progress_callback(70, "当前未接入可用转录 Provider，已写入阻塞状态")
                    self._upsert_stage_run(
                        video_id,
                        stage_id,
                        status=_PROVIDER_REQUIRED_STATUS,
                        progress_pct=0,
                        result_summary=_PROVIDER_REQUIRED_MESSAGE,
                        error_message=_PROVIDER_REQUIRED_MESSAGE,
                    )
                    await progress_callback(100, _PROVIDER_REQUIRED_MESSAGE)
                    await self._emit_stage_event(
                        "video.import.stage.completed",
                        video_id,
                        stage_id,
                        taskId=task_id,
                        ownerRef=owner_ref,
                        resultSummary=_PROVIDER_REQUIRED_MESSAGE,
                    )
                    return

                if stage_id == _SEGMENT_STAGE_ID:
                    transcript_stage = self._stage_repository.get_stage_run(video_id, _TRANSCRIPT_STAGE_ID)
                    if transcript_stage is None or transcript_stage.status != "succeeded":
                        await progress_callback(100, _SEGMENT_BLOCKED_MESSAGE)
                        self._mark_stage_blocked(video_id, _SEGMENT_STAGE_ID, _SEGMENT_BLOCKED_MESSAGE)
                        await self._emit_stage_event(
                            "video.import.stage.completed",
                            video_id,
                            stage_id,
                            taskId=task_id,
                            ownerRef=owner_ref,
                            resultSummary=_SEGMENT_BLOCKED_MESSAGE,
                        )
                        return

                    await progress_callback(55, f"正在处理 {stage_definition.label} 阶段")
                    segments = self._build_segments(video)
                    summary = f"已完成 {stage_definition.label} 阶段重跑，生成 {len(segments)} 个切段"
                    self._upsert_stage_run(
                        video_id,
                        stage_id,
                        status="succeeded",
                        progress_pct=100,
                        result_summary=summary,
                        error_message=None,
                    )
                    await progress_callback(100, summary)
                    await self._emit_stage_event(
                        "video.import.stage.completed",
                        video_id,
                        stage_id,
                        taskId=task_id,
                        ownerRef=owner_ref,
                        resultSummary=summary,
                    )
                    return

                segment_stage = self._stage_repository.get_stage_run(video_id, _SEGMENT_STAGE_ID)
                if segment_stage is None or segment_stage.status != "succeeded":
                    await progress_callback(100, _STRUCTURE_BLOCKED_MESSAGE)
                    self._mark_stage_blocked(video_id, _STRUCTURE_STAGE_ID, _STRUCTURE_BLOCKED_MESSAGE)
                    await self._emit_stage_event(
                        "video.import.stage.completed",
                        video_id,
                        stage_id,
                        taskId=task_id,
                        ownerRef=owner_ref,
                        resultSummary=_STRUCTURE_BLOCKED_MESSAGE,
                    )
                    return

                await progress_callback(55, f"正在处理 {stage_definition.label} 阶段")
                summary = f"已完成 {stage_definition.label} 阶段重跑"
                self._upsert_stage_run(
                    video_id,
                    stage_id,
                    status="succeeded",
                    progress_pct=100,
                    result_summary=summary,
                    error_message=None,
                )
                await progress_callback(100, summary)
                await self._emit_stage_event(
                    "video.import.stage.completed",
                    video_id,
                    stage_id,
                    taskId=task_id,
                    ownerRef=owner_ref,
                    resultSummary=summary,
                )
            except asyncio.CancelledError:
                error_code = f"video.{stage_id}.cancelled"
                error_message = f"{stage_definition.label} 阶段已取消。"
                self._upsert_stage_run(
                    video_id,
                    stage_id,
                    status="cancelled",
                    progress_pct=0,
                    result_summary=None,
                    error_message=error_message,
                )
                await self._emit_stage_event(
                    "video.import.stage.failed",
                    video_id,
                    stage_id,
                    taskId=task_id,
                    ownerRef=owner_ref,
                    errorCode=error_code,
                    errorMessage=error_message,
                    nextAction=self._build_failed_stage_next_action(stage_id, error_code),
                )
                raise
            except Exception as exc:
                error_message = str(exc) or "阶段重跑失败"
                error_code = self._build_failed_stage_error_code(stage_id, error_message)
                self._upsert_stage_run(
                    video_id,
                    stage_id,
                    status="failed",
                    progress_pct=0,
                    result_summary=None,
                    error_message=error_message,
                )
                await self._emit_stage_event(
                    "video.import.stage.failed",
                    video_id,
                    stage_id,
                    taskId=task_id,
                    ownerRef=owner_ref,
                    errorCode=error_code,
                    errorMessage=error_message,
                    nextAction=self._build_failed_stage_next_action(stage_id, error_code),
                )
                raise

        try:
            task = self._task_manager.submit(
                task_type="video-import-stage",
                coro_factory=_run_stage,
                project_id=video.project_id,
                task_id=task_id,
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

        task.owner_ref = owner_ref
        task.label = f"视频拆解：{stage_definition.label}"
        if request_id is not None:
            task.request_id = request_id
        return task

    def _get_stage_definition(self, stage_id: str) -> _StageDefinition:
        for stage in _STAGES:
            if stage.stage_id == stage_id:
                return stage
        raise HTTPException(status_code=404, detail="阶段不存在。")

    def _get_video(self, video_id: str):
        video = self._imported_video_repository.get(video_id)
        if video is None:
            raise HTTPException(status_code=404, detail="视频记录不存在。")
        return video

    def _resolve_transcription_stage(self, video_id: str) -> StoredVideoStageRun:
        stored = self._stage_repository.get_stage_run(video_id, _TRANSCRIPT_STAGE_ID)
        if stored is not None and stored.status == "succeeded":
            return stored
        if stored is not None and stored.status in {_PROVIDER_REQUIRED_STATUS, _BLOCKED_STATUS}:
            return stored
        return self._upsert_stage_run(
            video_id,
            _TRANSCRIPT_STAGE_ID,
            status=_PROVIDER_REQUIRED_STATUS,
            progress_pct=0,
            result_summary=_PROVIDER_REQUIRED_MESSAGE,
            error_message=_PROVIDER_REQUIRED_MESSAGE,
        )

    def _require_stage_succeeded(
        self,
        video_id: str,
        stage_id: str,
        message: str,
        *,
        blocked_stage_id: str | None = None,
        blocked_message: str | None = None,
    ) -> StoredVideoStageRun:
        stored = self._stage_repository.get_stage_run(video_id, stage_id)
        if stored is None or stored.status != "succeeded":
            if blocked_stage_id is not None and blocked_message is not None:
                self._mark_stage_blocked(video_id, blocked_stage_id, blocked_message)
            raise HTTPException(status_code=409, detail=message)
        return stored

    def _mark_stage_blocked(self, video_id: str, stage_id: str, message: str) -> StoredVideoStageRun:
        return self._upsert_stage_run(
            video_id,
            stage_id,
            status=_BLOCKED_STATUS,
            progress_pct=0,
            result_summary=message,
            error_message=message,
        )

    def _upsert_stage_run(
        self,
        video_id: str,
        stage_id: str,
        *,
        status: str,
        progress_pct: int,
        result_summary: str | None = None,
        error_message: str | None = None,
    ) -> StoredVideoStageRun:
        try:
            return self._stage_repository.upsert_stage_run(
                video_id,
                stage_id,
                status=status,
                progress_pct=progress_pct,
                result_summary=result_summary,
                error_message=error_message,
            )
        except Exception as exc:
            log.exception("写入视频阶段状态失败: %s/%s", video_id, stage_id)
            raise HTTPException(status_code=500, detail="写入视频阶段状态失败") from exc

    def _build_transcript_dto(
        self,
        video,
        stored: StoredVideoStageRun | None,
    ) -> VideoTranscriptDto:
        status = stored.status if stored is not None else _PROVIDER_REQUIRED_STATUS
        created_at = stored.created_at if stored is not None else video.created_at
        updated_at = stored.updated_at if stored is not None else video.created_at
        return VideoTranscriptDto(
            id=f"transcript-{video.id}",
            videoId=video.id,
            language="zh-CN",
            text=None,
            status=status,
            createdAt=created_at,
            updatedAt=updated_at,
        )

    def _build_segments(self, video) -> list[VideoSegmentDto]:
        end_ms = int((video.duration_seconds or 0) * 1000)
        metadata = json.dumps(
            {
                "width": video.width,
                "height": video.height,
                "frameRate": video.frame_rate,
                "codec": video.codec,
            },
            ensure_ascii=False,
        )
        return [
            VideoSegmentDto(
                id=f"segment-{video.id}-1",
                videoId=video.id,
                segmentIndex=1,
                startMs=0,
                endMs=end_ms,
                label=video.file_name,
                transcriptText=None,
                metadataJson=metadata,
                createdAt=video.created_at,
            )
        ]

    def _build_structure_dto(
        self,
        video,
        stored: StoredVideoStageRun | None,
    ) -> VideoStructureExtractionDto:
        ready = stored is not None and stored.status == "succeeded"
        script_json, storyboard_json = self._build_structure_payload(video) if ready else (None, None)
        created_at = stored.created_at if stored is not None else video.created_at
        updated_at = stored.updated_at if stored is not None else video.created_at
        status = stored.status if stored is not None else "pending"
        return VideoStructureExtractionDto(
            id=self._structure_extraction_id(video.id),
            videoId=video.id,
            status=status,
            scriptJson=script_json,
            storyboardJson=storyboard_json,
            createdAt=created_at,
            updatedAt=updated_at,
        )

    def _build_structure_payload(self, video) -> tuple[str, str]:
        segments = self._build_segments(video)
        script_payload = {
            "videoId": video.id,
            "projectId": video.project_id,
            "segments": [item.model_dump(mode="json") for item in segments],
            "summary": {
                "fileName": video.file_name,
                "durationSeconds": video.duration_seconds,
                "width": video.width,
                "height": video.height,
            },
        }
        storyboard_payload = {
            "videoId": video.id,
            "projectId": video.project_id,
            "shots": self._build_storyboard_scenes(video),
        }
        return (
            json.dumps(script_payload, ensure_ascii=False),
            json.dumps(storyboard_payload, ensure_ascii=False),
        )

    def _build_script_content(self, video) -> str:
        end_ms = int((video.duration_seconds or 0) * 1000)
        return "\n".join(
            [
                f"来源视频：{video.file_name}",
                f"视频 ID：{video.id}",
                f"项目 ID：{video.project_id}",
                f"片段 1：0ms - {end_ms}ms",
                "转写文本：待接入 Provider 后回填。",
            ]
        )

    def _build_storyboard_scenes(self, video) -> list[dict[str, str]]:
        return [
            {
                "sceneId": "scene-1",
                "title": f"{video.file_name} - 片段 1",
                "summary": "来自导入视频的基础切段结构。",
                "visualPrompt": f"参考原视频 {video.file_name} 的开场画面和构图。",
            }
        ]

    def _parse_extraction_id(self, extraction_id: str) -> str:
        prefix = "extraction-"
        if not extraction_id.startswith(prefix) or len(extraction_id) <= len(prefix):
            raise HTTPException(status_code=404, detail="视频结构提取记录不存在。")
        return extraction_id[len(prefix) :]

    def _structure_extraction_id(self, video_id: str) -> str:
        return f"extraction-{video_id}"

    def _resolve_stage_state(
        self,
        video,
        stage_definition: _StageDefinition,
        stored: StoredVideoStageRun | None,
        active_task: TaskInfo | None,
    ) -> _ResolvedStageState:
        if stage_definition.stage_id == _IMPORT_STAGE_ID:
            base_state = self._resolve_import_stage_state(video)
        elif stored is None:
            error_code, next_action = self._derive_stage_feedback(stage_definition.stage_id, "pending", None)
            base_state = _ResolvedStageState(
                stage_id=stage_definition.stage_id,
                status="pending",
                progress_pct=0,
                result_summary=None,
                error_message=None,
                updated_at=None,
                error_code=error_code,
                next_action=next_action,
                blocked_by_stage_id=self._blocked_by_stage_id(stage_definition.stage_id, "pending"),
                active_task=None,
            )
        else:
            error_code, next_action = self._derive_stage_feedback(
                stage_definition.stage_id,
                stored.status,
                stored.error_message,
            )
            base_state = _ResolvedStageState(
                stage_id=stage_definition.stage_id,
                status=stored.status,
                progress_pct=stored.progress_pct,
                result_summary=stored.result_summary,
                error_message=stored.error_message,
                updated_at=stored.updated_at,
                error_code=error_code,
                next_action=next_action,
                blocked_by_stage_id=self._blocked_by_stage_id(stage_definition.stage_id, stored.status),
                active_task=None,
            )

        if active_task is None:
            return base_state

        return _ResolvedStageState(
            stage_id=stage_definition.stage_id,
            status=active_task.status,
            progress_pct=active_task.progress,
            result_summary=active_task.message or base_state.result_summary,
            error_message=None,
            updated_at=active_task.updated_at,
            error_code=None,
            next_action=self._active_task_next_action(active_task.status),
            blocked_by_stage_id=None,
            active_task=active_task,
        )

    def _resolve_import_stage_state(self, video) -> _ResolvedStageState:
        status, progress_pct, result_summary, error_message, updated_at = _import_stage_state(video)
        error_code, next_action = self._derive_stage_feedback(_IMPORT_STAGE_ID, status, error_message)
        return _ResolvedStageState(
            stage_id=_IMPORT_STAGE_ID,
            status=status,
            progress_pct=progress_pct,
            result_summary=result_summary,
            error_message=error_message,
            updated_at=updated_at,
            error_code=error_code,
            next_action=next_action,
            blocked_by_stage_id=None,
            active_task=None,
        )

    def _build_stage_dto(
        self,
        stage_definition: _StageDefinition,
        resolved_state: _ResolvedStageState,
        *,
        is_current: bool,
    ) -> VideoStageDto:
        active_task = resolved_state.active_task
        can_cancel = active_task is not None and active_task.status in _ACTIVE_TASK_STATUSES
        can_retry = (
            stage_definition.rerunnable
            and not can_cancel
            and resolved_state.status in _RETRYABLE_STAGE_STATUSES
        )
        return VideoStageDto(
            stageId=stage_definition.stage_id,
            label=stage_definition.label,
            status=resolved_state.status,
            progressPct=resolved_state.progress_pct,
            resultSummary=resolved_state.result_summary,
            errorMessage=resolved_state.error_message,
            errorCode=resolved_state.error_code,
            nextAction=resolved_state.next_action,
            blockedByStageId=resolved_state.blocked_by_stage_id,
            updatedAt=resolved_state.updated_at,
            isCurrent=is_current,
            activeTaskId=active_task.id if active_task is not None else None,
            activeTaskStatus=active_task.status if active_task is not None else None,
            activeTaskProgress=active_task.progress if active_task is not None else None,
            activeTaskMessage=active_task.message if active_task is not None else None,
            canCancel=can_cancel,
            canRetry=can_retry,
            canRerun=stage_definition.rerunnable,
        )

    def _list_active_stage_tasks(self, video_id: str) -> dict[str, TaskInfo]:
        tasks_by_stage: dict[str, TaskInfo] = {}
        for task in self._task_manager.list_active():
            stage_id = self._match_stage_task(video_id, task)
            if stage_id is None:
                continue
            previous = tasks_by_stage.get(stage_id)
            if previous is None or self._active_task_sort_key(task) > self._active_task_sort_key(previous):
                tasks_by_stage[stage_id] = task
        return tasks_by_stage

    def _match_stage_task(self, video_id: str, task: TaskInfo) -> str | None:
        owner_ref = getattr(task, "owner_ref", None)
        if isinstance(owner_ref, dict):
            owner_kind = str(owner_ref.get("kind") or "")
            owner_video_id = str(owner_ref.get("videoId") or "")
            owner_stage_id = str(owner_ref.get("stageId") or "")
            owner_id = str(owner_ref.get("id") or "")
            if owner_kind == "video-stage":
                if owner_video_id == video_id and owner_stage_id in _STAGE_ORDER:
                    return owner_stage_id
                if owner_id.startswith(f"{video_id}:"):
                    candidate_stage_id = owner_id.split(":", 1)[1]
                    if candidate_stage_id in _STAGE_ORDER:
                        return candidate_stage_id

        if task.task_type == "video_import" and task.id == video_id:
            return _IMPORT_STAGE_ID
        return None

    def _active_task_sort_key(self, task: TaskInfo) -> tuple[int, str, str]:
        return (
            1 if task.status == "running" else 0,
            getattr(task, "updated_at", ""),
            getattr(task, "id", ""),
        )

    def _resolve_current_stage_id(self, states: list[_ResolvedStageState]) -> str:
        active_states = [state for state in states if state.active_task is not None]
        if active_states:
            active_states.sort(
                key=lambda item: (
                    1 if item.active_task is not None and item.active_task.status == "running" else 0,
                    -_STAGE_ORDER.get(item.stage_id, 0),
                    item.updated_at or "",
                ),
                reverse=True,
            )
            return active_states[0].stage_id

        for state in states:
            if state.status != "succeeded":
                return state.stage_id
        return states[-1].stage_id

    def _derive_stage_feedback(
        self,
        stage_id: str,
        status: str,
        error_message: str | None,
    ) -> tuple[str | None, str | None]:
        if stage_id == _IMPORT_STAGE_ID:
            return self._derive_import_stage_feedback(status, error_message)
        if status == "queued":
            return None, "任务已排队，请等待当前阶段开始执行。"
        if status == "running":
            return None, "当前阶段处理中，请等待任务完成或取消当前任务。"
        if stage_id == _TRANSCRIPT_STAGE_ID:
            return self._derive_transcript_stage_feedback(status, error_message)
        if stage_id == _SEGMENT_STAGE_ID:
            return self._derive_segment_stage_feedback(status, error_message)
        if stage_id == _STRUCTURE_STAGE_ID:
            return self._derive_structure_stage_feedback(status, error_message)
        return None, None

    def _derive_import_stage_feedback(
        self,
        status: str,
        error_message: str | None,
    ) -> tuple[str | None, str | None]:
        if status == "queued":
            return None, "导入任务已进入队列，请等待后台解析启动。"
        if status == "running":
            return None, "正在解析视频元数据，请等待导入完成。"
        if status == "succeeded":
            return None, "导入已完成，可以继续执行视频转录。"

        error_code = self._build_import_error_code(error_message)
        if error_code == "media.ffprobe_unavailable":
            return error_code, "请先修复 FFprobe 或媒体诊断配置后，再重新导入视频。"
        if error_code == "video.import.file_missing":
            return error_code, "请确认原始视频文件仍存在于本地路径后，再重新导入视频。"
        return error_code, "请检查视频文件可读性与 Runtime 日志后，再重新导入视频。"

    def _derive_transcript_stage_feedback(
        self,
        status: str,
        error_message: str | None,
    ) -> tuple[str | None, str | None]:
        if status == "pending":
            return None, "可开始视频转录。"
        if status == "succeeded":
            return None, "转录已完成，可以继续执行视频分段。"
        if status == _PROVIDER_REQUIRED_STATUS:
            return "provider.required", "请先配置可用转录 Provider 后重试。"
        if status == _BLOCKED_STATUS:
            return "task.conflict", "请先完成导入阶段后重试。"
        error_code = self._build_failed_stage_error_code(_TRANSCRIPT_STAGE_ID, error_message)
        return error_code, self._build_failed_stage_next_action(_TRANSCRIPT_STAGE_ID, error_code)

    def _derive_segment_stage_feedback(
        self,
        status: str,
        error_message: str | None,
    ) -> tuple[str | None, str | None]:
        if status == "pending":
            return None, "请先完成转录，再执行视频分段。"
        if status == "succeeded":
            return None, "分段已完成，可以继续执行结构提取。"
        if status == _BLOCKED_STATUS:
            return "task.conflict", "请先完成转录阶段后重试。"
        error_code = self._build_failed_stage_error_code(_SEGMENT_STAGE_ID, error_message)
        return error_code, self._build_failed_stage_next_action(_SEGMENT_STAGE_ID, error_code)

    def _derive_structure_stage_feedback(
        self,
        status: str,
        error_message: str | None,
    ) -> tuple[str | None, str | None]:
        if status == "pending":
            return None, "请先完成分段，再执行结构提取。"
        if status == "succeeded":
            return None, "结构提取已完成，可以将结果应用到项目。"
        if status == _BLOCKED_STATUS:
            return "task.conflict", "请先完成分段阶段后重试。"
        error_code = self._build_failed_stage_error_code(_STRUCTURE_STAGE_ID, error_message)
        return error_code, self._build_failed_stage_next_action(_STRUCTURE_STAGE_ID, error_code)

    def _build_import_error_code(self, error_message: str | None) -> str:
        if error_message and "FFprobe" in error_message:
            return "media.ffprobe_unavailable"
        if error_message and "文件不存在" in error_message:
            return "video.import.file_missing"
        return "video.import.failed"

    def _build_failed_stage_error_code(self, stage_id: str, error_message: str | None) -> str:
        if error_message and "文件不存在" in error_message:
            return f"video.{stage_id}.file_missing"
        return f"video.{stage_id}.failed"

    def _build_failed_stage_next_action(self, stage_id: str, error_code: str) -> str:
        if error_code.endswith(".file_missing"):
            return "请确认原始视频文件仍存在于本地路径后，再重试当前阶段。"
        if error_code.endswith(".cancelled"):
            return "当前阶段已取消，如仍需继续可重新发起该阶段。"
        if stage_id == _TRANSCRIPT_STAGE_ID:
            return "请检查 Provider 配置、视频文件与 Runtime 日志后，再重试转录。"
        if stage_id == _SEGMENT_STAGE_ID:
            return "请检查转录结果与视频文件状态后，再重试视频分段。"
        if stage_id == _STRUCTURE_STAGE_ID:
            return "请检查分段结果与视频文件状态后，再重试结构提取。"
        return "请检查当前阶段依赖与 Runtime 日志后，再重试。"

    def _active_task_next_action(self, task_status: str) -> str:
        if task_status == "queued":
            return "当前阶段已排队，请等待任务开始执行。"
        return "当前阶段处理中，可等待完成或取消当前任务。"

    def _blocked_by_stage_id(self, stage_id: str, status: str) -> str | None:
        if status != _BLOCKED_STATUS:
            return None
        if stage_id == _TRANSCRIPT_STAGE_ID:
            return _IMPORT_STAGE_ID
        if stage_id == _SEGMENT_STAGE_ID:
            return _TRANSCRIPT_STAGE_ID
        if stage_id == _STRUCTURE_STAGE_ID:
            return _SEGMENT_STAGE_ID
        return None

    async def _emit_stage_event(self, event_type: str, video_id: str, stage_id: str, **payload: object) -> None:
        message = {
            "type": event_type,
            "videoId": video_id,
            "stage": stage_id,
            **payload,
        }
        await ws_manager.broadcast(message)


def _import_stage_state(video) -> tuple[str, int, str | None, str | None, str]:
    if video.status == "error":
        return "failed", 0, None, video.error_message, video.created_at
    if video.status == "failed_degraded":
        return (
            "failed_degraded",
            80,
            "FFprobe 不可用，导入解析失败，暂缺时长与分辨率等元数据。",
            video.error_message,
            video.created_at,
        )
    if video.status == "ready":
        summary = video.error_message or f"已导入 {video.file_name}"
        return "succeeded", 100, summary, None, video.created_at
    if video.status == "imported":
        return "queued", 0, "已接收导入请求，等待后台解析。", None, video.created_at
    return "running", 50, None, None, video.created_at


def _stage_owner_ref(video_id: str, stage_id: str) -> dict[str, str]:
    return {
        "kind": "video-stage",
        "id": f"{video_id}:{stage_id}",
        "videoId": video_id,
        "stageId": stage_id,
    }


def _utc_now() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
