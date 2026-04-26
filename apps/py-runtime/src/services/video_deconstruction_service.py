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
    StoredVideoDeconstructionArtifact,
    StoredVideoStageRun,
    VideoDeconstructionRepository,
)
from schemas.video_deconstruction import (
    ApplyVideoExtractionResultDto,
    VideoDeconstructionResultDto,
    VideoSegmentDto,
    VideoStageDto,
    VideoStructureExtractionDto,
    VideoTranscriptDto,
)
from services.dashboard_service import DashboardService
from services.task_manager import TaskInfo, TaskManager, task_manager as default_task_manager
from services.video_deconstruction_result_builder import build_standard_video_result
from services.video_multimodal_analysis_service import VideoMultimodalAnalysisService
from services.video_transcription_service import (
    PROVIDER_REQUIRED_MESSAGE as TRANSCRIPTION_PROVIDER_REQUIRED_MESSAGE,
    VideoTranscriptionConfigurationError,
    VideoTranscriptionExecutionError,
    VideoTranscriptionService,
)
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
_COMPLETED_STAGE_STATUSES = {"succeeded", "skipped"}

_PROVIDER_REQUIRED_MESSAGE = TRANSCRIPTION_PROVIDER_REQUIRED_MESSAGE
_SEGMENT_WITHOUT_TRANSCRIPT_MESSAGE = "未配置可用视频解析模型，已使用基础元数据生成画面分段。"
_STRUCTURE_BLOCKED_MESSAGE = "视频分段尚未成功，结构提取已阻塞；请先完成分段后重试。"
_APPLY_BLOCKED_MESSAGE = "视频结构提取尚未成功，无法应用到项目；请先完成结构提取后重试。"
_MULTIMODAL_ARTIFACT_TYPE = "multimodal_timeline"
_TRANSCRIPT_SKIPPED_BY_MULTIMODAL_MESSAGE = "多模态视频拆解已生成语音与画面时间轴，未单独执行转录。"
_MULTIMODAL_STRUCTURE_SUMMARY = "已通过多模态模型生成画面与语音时间轴。"

_STAGES = (
    _StageDefinition(_IMPORT_STAGE_ID, "导入", True),
    _StageDefinition(_TRANSCRIPT_STAGE_ID, "视频解析", True),
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
        transcription_service: VideoTranscriptionService | None = None,
        multimodal_analysis_service: VideoMultimodalAnalysisService | None = None,
        task_manager: TaskManager | None = None,
    ) -> None:
        self._imported_video_repository = imported_video_repository
        self._stage_repository = stage_repository
        self._transcription_service = transcription_service
        self._multimodal_analysis_service = multimodal_analysis_service
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
            stored = self._execute_transcription(video)
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

    def deconstruct_video(self, video_id: str) -> VideoDeconstructionResultDto:
        try:
            video = self._get_video(video_id)
            if not Path(video.file_path).is_file():
                raise HTTPException(status_code=404, detail="原始视频文件不存在，请重新导入。")

            multimodal_artifact = self._execute_multimodal_deconstruction(video)
            if multimodal_artifact is not None:
                transcript_stage = self._upsert_stage_run(
                    video_id,
                    _TRANSCRIPT_STAGE_ID,
                    status="skipped",
                    progress_pct=100,
                    result_summary=_TRANSCRIPT_SKIPPED_BY_MULTIMODAL_MESSAGE,
                    error_message=None,
                )
                segments = self._build_segments(video)
                self._upsert_stage_run(
                    video_id,
                    _SEGMENT_STAGE_ID,
                    status="succeeded",
                    progress_pct=100,
                    result_summary=f"已生成 {len(segments)} 个画面语音对齐片段",
                    error_message=None,
                )
                stored_structure = self._upsert_stage_run(
                    video_id,
                    _STRUCTURE_STAGE_ID,
                    status="succeeded",
                    progress_pct=100,
                    result_summary=_MULTIMODAL_STRUCTURE_SUMMARY,
                    error_message=None,
                )
                return self._build_result_dto(video, transcript_stage, stored_structure)

            transcript_stage = self._execute_transcription(video)
            segments = self._build_segments(video)
            transcript_missing = transcript_stage.status != "succeeded"
            segment_summary = (
                _SEGMENT_WITHOUT_TRANSCRIPT_MESSAGE
                if transcript_missing
                else f"已生成 {len(segments)} 个基础切段"
            )
            self._upsert_stage_run(
                video_id,
                _SEGMENT_STAGE_ID,
                status="succeeded",
                progress_pct=100,
                result_summary=segment_summary,
                error_message=None,
            )
            stored_structure = self._upsert_stage_run(
                video_id,
                _STRUCTURE_STAGE_ID,
                status="succeeded",
                progress_pct=100,
                result_summary="已生成脚本和分镜结构草稿",
                error_message=None,
            )
            return self._build_result_dto(video, transcript_stage, stored_structure)
        except HTTPException:
            raise
        except Exception as exc:
            log.exception("执行一键视频拆解失败: %s", video_id)
            raise HTTPException(status_code=500, detail="执行一键视频拆解失败") from exc

    def get_result(self, video_id: str) -> VideoDeconstructionResultDto:
        try:
            video = self._get_video(video_id)
            transcript_stage = self._stage_repository.get_stage_run(video_id, _TRANSCRIPT_STAGE_ID)
            structure_stage = self._stage_repository.get_stage_run(video_id, _STRUCTURE_STAGE_ID)
            return self._build_result_dto(video, transcript_stage, structure_stage)
        except HTTPException:
            raise
        except Exception as exc:
            log.exception("查询视频拆解标准结果失败: %s", video_id)
            raise HTTPException(status_code=500, detail="查询视频拆解标准结果失败") from exc

    def run_segmentation(self, video_id: str) -> list[VideoSegmentDto]:
        try:
            video = self._get_video(video_id)
            transcript_stage = self._stage_repository.get_stage_run(video_id, _TRANSCRIPT_STAGE_ID)
            segments = self._build_segments(video)
            transcript_missing = transcript_stage is None or transcript_stage.status != "succeeded"
            self._upsert_stage_run(
                video_id,
                _SEGMENT_STAGE_ID,
                status="succeeded",
                progress_pct=100,
                result_summary=(
                    _SEGMENT_WITHOUT_TRANSCRIPT_MESSAGE
                    if transcript_missing
                    else f"已生成 {len(segments)} 个基础切段"
                ),
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
            if stage_id == _IMPORT_STAGE_ID:
                from runtime_tasks.video_tasks import process_video_import_task

                await process_video_import_task(
                    video_id=video_id,
                    task_id=task_id,
                    file_path=video.file_path,
                    repository=self._imported_video_repository,
                    stage_repository=self._stage_repository,
                    progress_callback=progress_callback,
                )
                return

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
                    await progress_callback(55, "正在调用视频转录 Provider")
                    stored = self._execute_transcription(video)
                    summary = stored.result_summary or "视频转录已完成。"
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

                if stage_id == _SEGMENT_STAGE_ID:
                    transcript_stage = self._stage_repository.get_stage_run(video_id, _TRANSCRIPT_STAGE_ID)
                    await progress_callback(55, f"正在处理 {stage_definition.label} 阶段")
                    segments = self._build_segments(video)
                    summary = (
                        _SEGMENT_WITHOUT_TRANSCRIPT_MESSAGE
                        if transcript_stage is None or transcript_stage.status != "succeeded"
                        else f"已完成 {stage_definition.label} 阶段重跑，生成 {len(segments)} 个切段"
                    )
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

    def _execute_transcription(self, video) -> StoredVideoStageRun:
        if self._transcription_service is None:
            return self._upsert_stage_run(
                video.id,
                _TRANSCRIPT_STAGE_ID,
                status=_PROVIDER_REQUIRED_STATUS,
                progress_pct=0,
                result_summary=_PROVIDER_REQUIRED_MESSAGE,
                error_message=_PROVIDER_REQUIRED_MESSAGE,
            )

        try:
            result = self._transcription_service.transcribe_file(video.file_path)
        except VideoTranscriptionConfigurationError as exc:
            message = str(exc) or _PROVIDER_REQUIRED_MESSAGE
            return self._upsert_stage_run(
                video.id,
                _TRANSCRIPT_STAGE_ID,
                status=_PROVIDER_REQUIRED_STATUS,
                progress_pct=0,
                result_summary=message,
                error_message=message,
            )
        except FileNotFoundError as exc:
            message = str(exc)
            return self._upsert_stage_run(
                video.id,
                _TRANSCRIPT_STAGE_ID,
                status="failed",
                progress_pct=0,
                result_summary=None,
                error_message=message,
            )
        except VideoTranscriptionExecutionError as exc:
            message = str(exc) or "视频转录 Provider 执行失败。"
            return self._upsert_stage_run(
                video.id,
                _TRANSCRIPT_STAGE_ID,
                status="failed",
                progress_pct=0,
                result_summary=None,
                error_message=message,
            )

        transcript = self._stage_repository.upsert_transcript(
            video.id,
            text=result.text,
            language=result.language,
            provider=result.provider,
            model=result.model,
        )
        return self._upsert_stage_run(
            video.id,
            _TRANSCRIPT_STAGE_ID,
            status="succeeded",
            progress_pct=100,
            result_summary=f"已完成视频转录，识别 {len(transcript.text)} 字。",
            error_message=None,
        )

    def _execute_multimodal_deconstruction(self, video) -> StoredVideoDeconstructionArtifact | None:
        if self._multimodal_analysis_service is None:
            return None
        try:
            result = self._multimodal_analysis_service.analyze_video(video)
            if result is None:
                return None
            return self._stage_repository.upsert_artifact(
                video.id,
                _MULTIMODAL_ARTIFACT_TYPE,
                payload_json=json.dumps(result.payload, ensure_ascii=False),
                provider=result.provider,
                model=result.model,
            )
        except Exception as exc:  # pragma: no cover - 防御性兜底
            log.exception("保存多模态视频拆解结果失败: %s", video.id)
            return None

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
        transcript = self._stage_repository.get_transcript(video.id) if status == "succeeded" else None
        return VideoTranscriptDto(
            id=f"transcript-{video.id}",
            videoId=video.id,
            language=transcript.language if transcript is not None else None,
            text=transcript.text if transcript is not None else None,
            status=status,
            createdAt=created_at,
            updatedAt=updated_at,
        )

    def _build_segments(self, video) -> list[VideoSegmentDto]:
        artifact_payload = self._load_multimodal_payload(video.id)
        if artifact_payload is not None:
            return self._build_multimodal_segments(video, artifact_payload)

        end_ms = int((video.duration_seconds or 0) * 1000)
        transcript = self._stage_repository.get_transcript(video.id)
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
                transcriptText=transcript.text if transcript is not None else None,
                metadataJson=metadata,
                createdAt=video.created_at,
            )
        ]

    def _load_multimodal_payload(self, video_id: str) -> dict[str, object] | None:
        artifact = self._stage_repository.get_artifact(video_id, _MULTIMODAL_ARTIFACT_TYPE)
        if artifact is None:
            return None
        try:
            payload = json.loads(artifact.payload_json)
        except json.JSONDecodeError:
            log.warning("多模态视频拆解结果 JSON 损坏: %s", video_id)
            return None
        if not isinstance(payload, dict):
            return None
        segments = payload.get("segments")
        if not isinstance(segments, list) or not segments:
            return None
        return payload

    def _build_multimodal_segments(
        self,
        video,
        payload: dict[str, object],
    ) -> list[VideoSegmentDto]:
        raw_segments = payload.get("segments")
        if not isinstance(raw_segments, list):
            return []
        segments: list[VideoSegmentDto] = []
        for index, item in enumerate(raw_segments, start=1):
            if not isinstance(item, dict):
                continue
            start_ms = _coerce_int(item.get("startMs"), default=(index - 1) * 3000)
            end_ms = _coerce_int(item.get("endMs"), default=start_ms + 3000)
            if end_ms <= start_ms:
                end_ms = start_ms + 3000
            metadata = {
                "source": "multimodal",
                "visual": str(item.get("visual") or ""),
                "speech": str(item.get("speech") or ""),
                "onscreenText": str(item.get("onscreenText") or ""),
                "shotType": str(item.get("shotType") or ""),
                "intent": str(item.get("intent") or ""),
            }
            segments.append(
                VideoSegmentDto(
                    id=f"segment-{video.id}-{index}",
                    videoId=video.id,
                    segmentIndex=index,
                    startMs=start_ms,
                    endMs=end_ms,
                    label=str(item.get("intent") or item.get("shotType") or f"片段 {index}"),
                    transcriptText=str(item.get("speech") or "") or None,
                    metadataJson=json.dumps(metadata, ensure_ascii=False),
                    createdAt=video.created_at,
                )
            )
        return segments

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

    def _build_result_dto(
        self,
        video,
        transcript_stage: StoredVideoStageRun | None,
        structure_stage: StoredVideoStageRun | None,
    ) -> VideoDeconstructionResultDto:
        transcript = self._build_transcript_dto(video, transcript_stage)
        segments = self._build_segments(video)
        structure = self._build_structure_dto(video, structure_stage)
        artifact = self._stage_repository.get_artifact(video.id, _MULTIMODAL_ARTIFACT_TYPE)
        script, keyframes, content_structure, source = build_standard_video_result(
            video,
            transcript=transcript,
            segments=segments,
            structure=structure,
            artifact=artifact,
        )
        return VideoDeconstructionResultDto(
            videoId=video.id,
            transcript=transcript,
            segments=segments,
            structure=structure,
            stages=self.get_stages(video.id),
            script=script,
            keyframes=keyframes,
            contentStructure=content_structure,
            source=source,
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
        artifact_payload = self._load_multimodal_payload(video.id)
        if artifact_payload is not None:
            segments = self._build_multimodal_segments(video, artifact_payload)
            lines = [
                f"来源视频：{video.file_name}",
                f"视频 ID：{video.id}",
                f"项目 ID：{video.project_id}",
                "多模态拆解片段：",
            ]
            for item in segments:
                metadata = json.loads(item.metadataJson or "{}")
                lines.extend(
                    [
                        f"片段 {item.segmentIndex}：{item.startMs}ms - {item.endMs}ms",
                        f"画面：{metadata.get('visual') or '未识别'}",
                        f"语音：{item.transcriptText or '未识别'}",
                    ]
                )
            return "\n".join(lines)

        end_ms = int((video.duration_seconds or 0) * 1000)
        transcript = self._stage_repository.get_transcript(video.id)
        transcript_text = transcript.text if transcript is not None else "待完成视频转录后回填。"
        return "\n".join(
            [
                f"来源视频：{video.file_name}",
                f"视频 ID：{video.id}",
                f"项目 ID：{video.project_id}",
                f"片段 1：0ms - {end_ms}ms",
                f"转写文本：{transcript_text}",
            ]
        )

    def _build_storyboard_scenes(self, video) -> list[dict[str, str]]:
        artifact_payload = self._load_multimodal_payload(video.id)
        if artifact_payload is not None:
            scenes: list[dict[str, str]] = []
            for item in self._build_multimodal_segments(video, artifact_payload):
                metadata = json.loads(item.metadataJson or "{}")
                scenes.append(
                    {
                        "sceneId": f"scene-{item.segmentIndex}",
                        "title": item.label,
                        "summary": item.transcriptText or str(metadata.get("intent") or ""),
                        "visualPrompt": str(metadata.get("visual") or ""),
                    }
                )
            return scenes

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
            if state.status not in _COMPLETED_STAGE_STATUSES:
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
            return None, "可开始视频解析。"
        if status == "succeeded":
            return None, "视频解析已完成，可以继续执行视频分段。"
        if status == "skipped":
            return None, "已由多模态模型完成画面与语音对齐，无需单独转录。"
        if status == _PROVIDER_REQUIRED_STATUS:
            return "provider.required", "请先配置可用视频解析模型后重试。"
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
            return None, "可直接执行视频分段；未完成转录时将生成无逐字稿的结构结果。"
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
            return "请检查视频解析模型配置、视频文件与 Runtime 日志后，再重试。"
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


def _coerce_int(value: object, *, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
