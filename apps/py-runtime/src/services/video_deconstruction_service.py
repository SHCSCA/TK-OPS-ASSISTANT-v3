from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from pathlib import Path

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


_TRANSCRIPT_STAGE_ID = "transcribe"
_SEGMENT_STAGE_ID = "segment"
_STRUCTURE_STAGE_ID = "extract_structure"
_PROVIDER_REQUIRED_STATUS = "provider_required"
_BLOCKED_STATUS = "blocked"

_PROVIDER_REQUIRED_MESSAGE = "\u5f53\u524d\u672a\u63a5\u5165\u53ef\u7528\u8f6c\u5f55 Provider\uff0c\u8f6c\u5f55\u5df2\u963b\u585e\uff1b\u63a5\u5165 Provider \u540e\u53ef\u91cd\u8bd5\u3002"
_SEGMENT_BLOCKED_MESSAGE = "\u89c6\u9891\u8f6c\u5f55\u5c1a\u672a\u6210\u529f\uff0c\u5206\u6bb5\u5df2\u963b\u585e\uff1b\u8bf7\u5148\u5b8c\u6210\u8f6c\u5f55\u540e\u91cd\u8bd5\u3002"
_STRUCTURE_BLOCKED_MESSAGE = "\u89c6\u9891\u5206\u6bb5\u5c1a\u672a\u6210\u529f\uff0c\u7ed3\u6784\u63d0\u53d6\u5df2\u963b\u585e\uff1b\u8bf7\u5148\u5b8c\u6210\u5206\u6bb5\u540e\u91cd\u8bd5\u3002"
_APPLY_BLOCKED_MESSAGE = "\u89c6\u9891\u7ed3\u6784\u63d0\u53d6\u5c1a\u672a\u6210\u529f\uff0c\u65e0\u6cd5\u5e94\u7528\u5230\u9879\u76ee\uff1b\u8bf7\u5148\u5b8c\u6210\u7ed3\u6784\u63d0\u53d6\u540e\u91cd\u8bd5\u3002"

_STAGES = (
    _StageDefinition("import", "\u5bfc\u5165", False),
    _StageDefinition(_TRANSCRIPT_STAGE_ID, "\u8f6c\u5f55", True),
    _StageDefinition(_SEGMENT_STAGE_ID, "\u5206\u6bb5", True),
    _StageDefinition(_STRUCTURE_STAGE_ID, "\u7ed3\u6784\u63d0\u53d6", True),
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

        async def _run_stage(progress_callback):
            await self._emit_stage_event(
                "video.import.stage.started",
                video_id,
                stage_id,
                started_at=_utc_now(),
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
                        result_summary=_PROVIDER_REQUIRED_MESSAGE,
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
                            result_summary=_SEGMENT_BLOCKED_MESSAGE,
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
                        result_summary=summary,
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
                        result_summary=_STRUCTURE_BLOCKED_MESSAGE,
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
                    result_summary=summary,
                )
            except Exception as exc:
                error_message = str(exc) or "阶段重跑失败"
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
                    error_message=error_message,
                )
                raise

        try:
            task = self._task_manager.submit(
                task_type="video-import-stage",
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

    def _assert_dependency_ready(
        self,
        video_id: str,
        stage_id: str,
        message: str,
    ) -> StoredVideoStageRun:
        stored = self._stage_repository.get_stage_run(video_id, stage_id)
        if stored is None or stored.status != "succeeded":
            raise HTTPException(status_code=409, detail=message)
        return stored

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

    def _build_stage_dto(
        self,
        video,
        stage_definition: _StageDefinition,
        stored: StoredVideoStageRun | None,
    ) -> VideoStageDto:
        if stage_definition.stage_id == "import":
            status, progress_pct, result_summary, error_message, updated_at = _import_stage_state(video)
        elif stored is None:
            status, progress_pct, result_summary, error_message, updated_at = (
                "pending",
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
            "type": event_type,
            "videoId": video_id,
            "stage": stage_id,
            **payload,
        }
        await ws_manager.broadcast(message)


def _import_stage_state(video) -> tuple[str, int, str | None, str | None, str]:
    if video.status == "error":
        return "failed", 0, None, video.error_message, video.created_at
    if video.status in {"ready", "imported"}:
        summary = video.error_message or f"已导入 {video.file_name}"
        return "succeeded", 100, summary, None, video.created_at
    return "running", 50, None, None, video.created_at


def _utc_now() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
