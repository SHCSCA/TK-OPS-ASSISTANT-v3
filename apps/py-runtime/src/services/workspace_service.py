from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any
from urllib.parse import quote

from fastapi import HTTPException
from pydantic import ValidationError

from ai.providers.errors import ProviderHTTPException
from domain.models.asset import Asset
from domain.models.timeline import Timeline
from repositories.asset_repository import AssetRepository
from repositories.magic_cut_repository import MagicCutSuggestionRepository
from repositories.timeline_repository import TimelineRepository
from schemas.workspace import (
    AssetReferenceStatusDto,
    ClipInsertAssetInput,
    ClipMoveInput,
    ClipReplaceInput,
    ClipSplitInput,
    ClipTrimInput,
    MagicCutSuggestionApplyInput,
    MagicCutSuggestionApplyResultDto,
    MagicCutSuggestionDismissResultDto,
    MagicCutSuggestionDraftDto,
    TimelineClipDto,
    TimelineCreateInput,
    TimelineDto,
    TimelinePrecheckIssueDto,
    TimelinePrecheckDto,
    TimelinePreviewDto,
    TimelineTrackDto,
    TimelineUpdateInput,
    TimelineVersionDto,
    WorkspaceAICommandInput,
    WorkspaceAICommandResultDto,
    WorkspaceActiveTaskDto,
    WorkspaceClipDetailDto,
    WorkspaceSaveStateDto,
    WorkspaceTimelineResultDto,
)
from services.ai_text_generation_service import (
    AITextGenerationService,
    normalize_text_generation_readiness_message,
)
from services.magic_cut import (
    parse_magic_cut_operations,
    serialize_timeline_for_ai,
)
from services.magic_cut_suggestion_service import (
    FAILED_PARSE_MESSAGE,
    MagicCutSuggestionService,
)
from services.task_manager import TaskInfo, TaskManager, task_manager as default_task_manager
from services.timeline_preview_media import TimelinePreviewMediaResolver

log = logging.getLogger(__name__)

SUPPORTED_TRACK_KINDS = {"video", "audio", "subtitle"}
PROCESSING_CLIP_STATUSES = {"queued", "running", "pending", "processing"}
FAILED_CLIP_STATUSES = {"failed", "error", "missing", "invalid"}
MIN_TRIMMED_CLIP_DURATION_MS = 500
MIN_ASSET_CLIP_DURATION_MS = 500
DEFAULT_ASSET_CLIP_DURATION_MS = 3000
ASSET_TRACK_KIND_BY_TYPE = {"video": "video", "image": "video", "audio": "audio"}
MAGIC_CUT_RUNTIME_FAILURE_MESSAGE = "智能粗剪 AI 调用失败，请检查 Provider 配置或稍后重试。"
MAGIC_CUT_OPERATION_FAILURE_MESSAGE = "智能粗剪执行失败，请查看日志后重试。"


def _build_magic_cut_instruction(parameters: dict[str, object]) -> str:
    """从前端提交的 parameters 中构建用户可读的剪辑指令。"""
    if not isinstance(parameters, dict):
        return "请根据时间线片段结构给出智能剪辑建议。"

    parts: list[str] = []
    selected_track_id = parameters.get("selectedTrackId")
    if isinstance(selected_track_id, str) and selected_track_id.strip():
        parts.append(f"用户当前选中的轨道 ID 为 {selected_track_id}")
    selected_clip_id = parameters.get("selectedClipId")
    if isinstance(selected_clip_id, str) and selected_clip_id.strip():
        parts.append(f"用户当前选中的片段 ID 为 {selected_clip_id}")
    raw_instruction = parameters.get("instruction")
    if isinstance(raw_instruction, str) and raw_instruction.strip():
        parts.append(f"用户补充指令：{raw_instruction.strip()}")

    if not parts:
        return "请根据时间线片段结构给出智能剪辑建议，使视频更紧凑、节奏更好。"
    return "。".join(parts) + "。请据此调整剪辑策略。"


class WorkspaceService:
    def __init__(
        self,
        repository: TimelineRepository,
        *,
        asset_repository: AssetRepository | None = None,
        task_manager: TaskManager | None = None,
        ai_text_generation_service: AITextGenerationService | None = None,
        magic_cut_suggestion_service: MagicCutSuggestionService | None = None,
    ) -> None:
        self._repository = repository
        self._asset_repository = asset_repository
        self._preview_media_resolver = TimelinePreviewMediaResolver(asset_repository)
        self._task_manager = task_manager or default_task_manager
        self._ai_text_generation_service = ai_text_generation_service
        self._magic_cut_suggestion_service = magic_cut_suggestion_service or MagicCutSuggestionService(
            MagicCutSuggestionRepository(session_factory=repository.session_factory),
            repository,
        )

    def get_project_timeline(self, project_id: str) -> WorkspaceTimelineResultDto:
        try:
            timeline = self._repository.get_current_for_project(project_id)
        except Exception as exc:
            log.exception("读取项目时间线失败")
            raise HTTPException(status_code=500, detail="读取项目时间线失败。") from exc

        if timeline is None:
            return WorkspaceTimelineResultDto(
                timeline=None,
                activeTask=None,
                saveState=None,
                message="当前项目还没有时间线草稿。",
            )

        return self._build_timeline_result(
            timeline,
            message="已读取时间线草稿。",
            save_source="load",
            save_message="已从本地存储读取最新时间线版本。",
        )

    def create_project_timeline(
        self,
        project_id: str,
        payload: TimelineCreateInput,
    ) -> WorkspaceTimelineResultDto:
        name = payload.name.strip() or "主时间线"
        try:
            timeline = self._repository.create_empty(project_id, name)
        except Exception as exc:
            log.exception("创建时间线草稿失败")
            raise HTTPException(status_code=500, detail="创建时间线草稿失败。") from exc

        return self._build_timeline_result(
            timeline,
            message="已创建时间线草稿。",
            save_source="create",
            save_message="已确认创建并保存时间线草稿。",
        )

    def update_timeline(
        self,
        timeline_id: str,
        payload: TimelineUpdateInput,
    ) -> WorkspaceTimelineResultDto:
        tracks = self._validate_and_normalize_tracks(payload.tracks)
        tracks_json = json.dumps(tracks, ensure_ascii=False)
        name = payload.name.strip() if payload.name is not None else None
        if name == "":
            name = "主时间线"

        try:
            timeline = self._repository.update_timeline(
                timeline_id,
                name=name,
                duration_seconds=payload.durationSeconds,
                tracks_json=tracks_json,
            )
        except Exception as exc:
            log.exception("保存时间线失败")
            raise HTTPException(status_code=500, detail="保存时间线失败。") from exc

        if timeline is None:
            raise HTTPException(status_code=404, detail="时间线不存在。")

        return self._build_timeline_result(
            timeline,
            message="已保存时间线草稿。",
            save_source="save",
            save_message="已确认保存时间线草稿。",
        )

    def fetch_clip(self, clip_id: str) -> WorkspaceClipDetailDto:
        timeline, track_index, _, clip = self._find_clip_context(clip_id)
        track = self._parse_tracks(timeline.tracks_json)[track_index]
        return WorkspaceClipDetailDto(
            id=clip.id,
            timelineId=timeline.id,
            trackId=str(track["id"]),
            trackKind=str(track["kind"]),
            trackName=str(track["name"]),
            sourceType=clip.sourceType,
            sourceId=clip.sourceId,
            label=clip.label,
            prompt=clip.prompt,
            resolution=clip.resolution,
            editableFields=clip.editableFields,
            startMs=clip.startMs,
            durationMs=clip.durationMs,
            inPointMs=clip.inPointMs,
            outPointMs=clip.outPointMs,
            status=clip.status,
        )

    def move_clip(
        self,
        clip_id: str,
        payload: ClipMoveInput | dict[str, object],
        *,
        timeline_id: str | None = None,
    ) -> WorkspaceTimelineResultDto:
        input_data = self._normalize_payload(payload)
        timeline, tracks, track_index, clip_index, clip = self._locate_clip_for_operation(clip_id, timeline_id)
        target_track_index = self._find_track_index(tracks, str(input_data["targetTrackId"]))
        if target_track_index is None:
            raise HTTPException(status_code=404, detail="目标轨道不存在。")

        source_track = tracks[track_index]
        target_track = tracks[target_track_index]
        if bool(source_track.get("locked")) or bool(target_track.get("locked")):
            raise HTTPException(status_code=400, detail="锁定轨道不能移动片段。")

        target_start_ms = int(input_data["startMs"])
        if target_start_ms < 0:
            raise HTTPException(status_code=400, detail="片段起点不能小于 0。")

        moved_clip = dict(clip)
        moved_clip["trackId"] = target_track["id"]
        moved_clip["startMs"] = target_start_ms
        if self._clip_overlaps_track(moved_clip, target_track, exclude_clip_id=clip_id):
            raise HTTPException(status_code=400, detail="片段移动后会与同轨片段重叠。")

        if track_index == target_track_index:
            source_track["clips"][clip_index] = moved_clip
        else:
            source_track["clips"].pop(clip_index)
            target_track["clips"].append(moved_clip)
        target_track["clips"] = sorted(
            target_track["clips"],
            key=lambda item: int(item.get("startMs") or 0),
        )

        return self._save_tracks(
            timeline,
            tracks,
            "片段已移动。",
            "clip_move",
            "已确认保存片段位置变更。",
        )

    def trim_clip(
        self,
        clip_id: str,
        payload: ClipTrimInput | dict[str, object],
        *,
        timeline_id: str | None = None,
    ) -> WorkspaceTimelineResultDto:
        input_data = self._normalize_payload(payload)
        timeline, tracks, track_index, clip_index, clip = self._locate_clip_for_operation(clip_id, timeline_id)
        trimmed_clip = dict(clip)
        for field in ("startMs", "durationMs", "inPointMs", "outPointMs"):
            if input_data.get(field) is not None:
                trimmed_clip[field] = input_data[field]
        start_ms = int(trimmed_clip.get("startMs") or 0)
        duration_ms = int(trimmed_clip.get("durationMs") or 0)
        if start_ms < 0:
            raise HTTPException(status_code=400, detail="片段起点不能小于 0。")
        if duration_ms < MIN_TRIMMED_CLIP_DURATION_MS:
            raise HTTPException(status_code=400, detail="片段裁剪后至少需要保留 500ms。")
        if self._clip_overlaps_track(trimmed_clip, tracks[track_index], exclude_clip_id=clip_id):
            raise HTTPException(status_code=400, detail="片段裁剪后会与同轨片段重叠。")
        tracks[track_index]["clips"][clip_index] = trimmed_clip
        return self._save_tracks(
            timeline,
            tracks,
            "片段已裁剪。",
            "clip_trim",
            "已确认保存片段裁剪结果。",
        )

    def replace_clip(
        self,
        clip_id: str,
        payload: ClipReplaceInput | dict[str, object],
    ) -> WorkspaceTimelineResultDto:
        input_data = self._normalize_payload(payload)
        timeline, tracks, track_index, clip_index, clip = self._locate_clip(clip_id)
        source_type = str(input_data.get("sourceType") or "asset")
        if source_type == "asset":
            asset_id = str(input_data.get("assetId") or input_data.get("sourceId") or "")
            replaced_clip = self._build_asset_replacement_clip(
                tracks[track_index],
                clip,
                asset_id,
            )
            tracks[track_index]["clips"][clip_index] = replaced_clip
            return self._save_tracks(
                timeline,
                tracks,
                "片段已替换。",
                "clip_replace",
                "已确认保存片段素材替换。",
            )

        replaced_clip = dict(clip)
        replaced_clip["sourceType"] = source_type
        replaced_clip["sourceId"] = input_data.get("sourceId")
        replaced_clip["label"] = str(input_data.get("label") or clip.get("label") or "未命名片段")
        replaced_clip["prompt"] = input_data.get("prompt")
        replaced_clip["resolution"] = input_data.get("resolution")
        editable_fields = input_data.get("editableFields")
        replaced_clip["editableFields"] = editable_fields if editable_fields is not None else []
        replaced_clip["status"] = "ready"
        tracks[track_index]["clips"][clip_index] = replaced_clip
        return self._save_tracks(
            timeline,
            tracks,
            "片段已替换。",
            "clip_replace",
            "已确认保存片段素材替换。",
        )

    def insert_asset_clip(
        self,
        timeline_id: str,
        payload: ClipInsertAssetInput | dict[str, object],
    ) -> WorkspaceTimelineResultDto:
        input_data = self._normalize_payload(payload)
        timeline = self._load_timeline(timeline_id)
        tracks = self._parse_tracks(timeline.tracks_json)
        asset = self._load_asset(str(input_data["assetId"]))
        target_kind = self._track_kind_for_asset(asset)
        self._require_asset_file(asset)

        target_track_index = self._resolve_asset_target_track_index(
            tracks,
            target_kind,
            input_data.get("targetTrackId"),
        )
        target_track = tracks[target_track_index]
        if bool(target_track.get("locked")):
            raise HTTPException(status_code=400, detail="锁定轨道不能加入资产。")

        start_ms = self._asset_insert_start(input_data, target_track)
        duration_ms = self._resolve_asset_duration_ms(asset)
        clip_id = self._build_asset_clip_id(tracks, asset.id, start_ms)
        new_clip = self._build_asset_clip(
            asset,
            clip_id=clip_id,
            track_id=str(target_track["id"]),
            start_ms=start_ms,
            duration_ms=duration_ms,
        )
        if self._clip_overlaps_track(new_clip, target_track, exclude_clip_id=clip_id):
            raise HTTPException(status_code=400, detail="资产入轨后会与同轨片段重叠。")

        clips = target_track.get("clips")
        if not isinstance(clips, list):
            clips = []
        clips.append(new_clip)
        target_track["clips"] = sorted(clips, key=lambda item: int(item.get("startMs") or 0))

        return self._save_tracks(
            timeline,
            tracks,
            "资产已加入时间线。",
            "clip_insert_asset",
            "已确认保存资产入轨结果。",
        )

    def delete_clip(self, clip_id: str, *, timeline_id: str | None = None) -> WorkspaceTimelineResultDto:
        timeline, tracks, track_index, clip_index, _ = self._locate_clip_for_operation(clip_id, timeline_id)
        track = tracks[track_index]
        if bool(track.get("locked")):
            raise HTTPException(status_code=400, detail="锁定轨道不能删除片段。")

        track["clips"].pop(clip_index)
        return self._save_tracks(
            timeline,
            tracks,
            "片段已删除。",
            "clip_delete",
            "已确认删除选中片段。",
        )

    def split_clip(
        self,
        clip_id: str,
        payload: ClipSplitInput | dict[str, object],
        *,
        timeline_id: str | None = None,
    ) -> WorkspaceTimelineResultDto:
        input_data = self._normalize_payload(payload)
        timeline, tracks, track_index, clip_index, clip = self._locate_clip_for_operation(clip_id, timeline_id)
        track = tracks[track_index]
        if bool(track.get("locked")):
            raise HTTPException(status_code=400, detail="锁定轨道不能分割片段。")

        split_at_ms = int(input_data["splitAtMs"])
        start_ms = int(clip.get("startMs") or 0)
        duration_ms = int(clip.get("durationMs") or 0)
        end_ms = start_ms + duration_ms
        if split_at_ms <= start_ms or split_at_ms >= end_ms:
            raise HTTPException(status_code=400, detail="分割点必须位于片段内部。")

        in_point_ms = int(clip.get("inPointMs") or 0)
        original_out_point = clip.get("outPointMs")
        out_point_ms = int(original_out_point) if original_out_point is not None else in_point_ms + duration_ms
        left_duration_ms = split_at_ms - start_ms
        right_duration_ms = end_ms - split_at_ms
        split_media_point_ms = in_point_ms + left_duration_ms

        left_clip = dict(clip)
        left_clip["durationMs"] = left_duration_ms
        left_clip["outPointMs"] = split_media_point_ms

        right_clip = dict(clip)
        right_clip["id"] = self._build_split_clip_id(tracks, clip_id, split_at_ms)
        right_clip["startMs"] = split_at_ms
        right_clip["durationMs"] = right_duration_ms
        right_clip["inPointMs"] = split_media_point_ms
        right_clip["outPointMs"] = out_point_ms

        track_clips = track["clips"]
        track_clips[clip_index : clip_index + 1] = [left_clip, right_clip]
        track["clips"] = sorted(track_clips, key=lambda item: int(item.get("startMs") or 0))

        return self._save_tracks(
            timeline,
            tracks,
            "片段已分割。",
            "clip_split",
            "已确认保存片段分割结果。",
        )

    def fetch_timeline_preview(self, timeline_id: str, clip_id: str | None = None) -> TimelinePreviewDto:
        timeline = self._load_timeline(timeline_id)
        try:
            tracks = self._parse_tracks(timeline.tracks_json)
            preview_payload = self._build_timeline_preview_payload(timeline, tracks)
            preview_url = self._encode_data_url(preview_payload)
            media, preview_error = self._preview_media_resolver.resolve(tracks, preferred_clip_id=clip_id)
        except HTTPException:
            raise
        except Exception as exc:
            log.exception("生成时间线本地预览失败")
            raise HTTPException(status_code=500, detail="生成时间线本地预览失败。") from exc

        preview_mode = "media" if media else "unavailable" if preview_error else "manifest"
        status = "ready" if media else "unavailable" if preview_error else "structure_only"
        if media:
            message = "时间线真实媒体预览已准备。"
        elif preview_error:
            message = preview_error.message
        else:
            message = "时间线本地预览已生成，当前没有可播放媒体，仅展示轨道与片段摘要。"

        return TimelinePreviewDto(
            timelineId=timeline_id,
            status=status,
            message=message,
            previewUrl=preview_url,
            previewMode=preview_mode,
            media=media,
            error=preview_error,
        )

    def precheck_timeline(self, timeline_id: str) -> TimelinePrecheckDto:
        timeline = self._load_timeline(timeline_id)
        try:
            tracks = self._parse_precheck_tracks(timeline.tracks_json)
            issue_details = self._build_timeline_precheck_issue_details(timeline.id, tracks)
        except HTTPException:
            raise
        except Exception as exc:
            log.exception("执行时间线本地预检失败")
            raise HTTPException(status_code=500, detail="执行时间线本地预检失败。") from exc

        issues = [issue.message for issue in issue_details]
        if issues:
            status = "warning"
            message = f"时间线本地预检发现 {len(issues)} 个问题。"
        else:
            status = "ready"
            message = "时间线本地预检通过。"

        return TimelinePrecheckDto(
            timelineId=timeline_id,
            status=status,
            message=message,
            issues=issues,
            issueDetails=issue_details,
        )

    def run_ai_command(
        self,
        project_id: str,
        payload: WorkspaceAICommandInput,
    ) -> WorkspaceAICommandResultDto:
        timeline = self._resolve_command_timeline(project_id, payload.timelineId)
        if payload.capabilityId == "magic_cut":
            if self._ai_text_generation_service is None:
                log.warning("智能粗剪配置预检失败 code=%s", "ai_provider_unsupported")
                return WorkspaceAICommandResultDto(
                    status="blocked",
                    task=None,
                    message=normalize_text_generation_readiness_message(
                        "magic_cut",
                        "ai_provider_unsupported",
                        "智能粗剪 Provider 未配置，请先选择可用文本模型。",
                    ),
                )
            try:
                self._ai_text_generation_service.validate_text_generation_ready("magic_cut")
            except ProviderHTTPException as exc:
                log.warning(
                    "智能粗剪配置预检失败 code=%s status=%s",
                    exc.error_code,
                    exc.status_code,
                )
                return WorkspaceAICommandResultDto(
                    status="blocked",
                    task=None,
                    message=normalize_text_generation_readiness_message(
                        "magic_cut",
                        exc.error_code,
                        str(exc.detail),
                    ),
                )

        async def _command_task(progress_callback):
            if payload.capabilityId == "magic_cut" and self._ai_text_generation_service:
                await progress_callback(10, "正在序列化时间线上下文...")
                timeline_context = serialize_timeline_for_ai(timeline.tracks_json)

                await progress_callback(20, "正在调用 AI 剪辑分析师...")
                instruction = _build_magic_cut_instruction(payload.parameters)
                try:
                    result = await asyncio.to_thread(
                        self._ai_text_generation_service.generate_text,
                        "magic_cut",
                        {"timeline_context": timeline_context, "instruction": instruction},
                        project_id=project_id,
                    )
                except ProviderHTTPException as exc:
                    log.warning(
                        "智能粗剪 AI 调用被 Provider 阻断 code=%s status=%s",
                        exc.error_code,
                        exc.status_code,
                    )
                    safe_message = normalize_text_generation_readiness_message(
                        "magic_cut",
                        exc.error_code,
                        MAGIC_CUT_RUNTIME_FAILURE_MESSAGE,
                    )
                    await progress_callback(0, safe_message)
                    raise ProviderHTTPException(
                        status_code=exc.status_code,
                        detail=safe_message,
                        error_code=exc.error_code,
                    ) from None
                except Exception:
                    log.exception("智能粗剪 AI 调用失败")
                    await progress_callback(0, MAGIC_CUT_OPERATION_FAILURE_MESSAGE)
                    raise RuntimeError(MAGIC_CUT_OPERATION_FAILURE_MESSAGE)

                await progress_callback(60, "正在解析 AI 响应...")
                operations, summary = parse_magic_cut_operations(result.text)

                if not operations:
                    try:
                        self._magic_cut_suggestion_service.create_failed_parse(
                            project_id,
                            timeline,
                            summary,
                            None,
                        )
                    except Exception as exc:
                        log.exception("智能粗剪建议生成失败")
                        await progress_callback(0, MAGIC_CUT_OPERATION_FAILURE_MESSAGE)
                        raise RuntimeError(MAGIC_CUT_OPERATION_FAILURE_MESSAGE) from exc
                    await progress_callback(100, FAILED_PARSE_MESSAGE)
                    return FAILED_PARSE_MESSAGE

                await progress_callback(75, f"正在保存 {len(operations)} 条智能粗剪建议...")
                try:
                    suggestion = self._magic_cut_suggestion_service.create_from_operations(
                        project_id,
                        timeline,
                        operations,
                        summary,
                        None,
                    )
                    if suggestion.status == "failed_parse":
                        await progress_callback(100, FAILED_PARSE_MESSAGE)
                        return FAILED_PARSE_MESSAGE
                    final_message = f"已生成 {len(suggestion.operations)} 条智能粗剪建议，等待审阅。"
                    await progress_callback(100, final_message)
                    return final_message
                except Exception as exc:
                    log.exception("智能粗剪建议生成失败")
                    await progress_callback(0, MAGIC_CUT_OPERATION_FAILURE_MESSAGE)
                    raise RuntimeError(MAGIC_CUT_OPERATION_FAILURE_MESSAGE) from exc
            else:
                await progress_callback(55, f"正在分析时间线：{timeline.id}")
            return None

        try:
            task = self._task_manager.submit(
                task_type="ai-workspace-command",
                coro_factory=_command_task,
                project_id=project_id,
            )
        except ValueError as exc:
            log.exception("提交 AI 命令任务失败")
            raise HTTPException(status_code=409, detail="AI 命令任务已存在。") from exc
        except Exception as exc:
            log.exception("提交 AI 命令任务失败")
            raise HTTPException(status_code=500, detail="提交 AI 命令任务失败。") from exc

        task.kind = "ai-workspace-command"
        task.task_type = "ai-workspace-command"
        task.label = f"AI 命令：{payload.capabilityId}"
        task.owner_ref = {"kind": "timeline", "id": timeline.id}
        task.message = f"AI 命令 {payload.capabilityId} 已进入任务队列。"

        task_data = task.to_dict()
        task_data["kind"] = task.kind
        task_data["label"] = task.label
        task_data["projectId"] = project_id
        task_data["ownerRef"] = task.owner_ref
        task_data["status"] = task.status
        task_data["message"] = task.message

        return WorkspaceAICommandResultDto(
            status=task.status,
            task=task_data,
            message="AI 命令已进入任务队列，正在通过 TaskBus 处理。",
        )

    def get_latest_magic_cut_suggestion(
        self,
        project_id: str,
        timeline_id: str,
    ) -> MagicCutSuggestionDraftDto | None:
        return self._magic_cut_suggestion_service.latest(project_id, timeline_id)

    def apply_magic_cut_suggestion(
        self,
        suggestion_id: str,
        payload: MagicCutSuggestionApplyInput,
    ) -> MagicCutSuggestionApplyResultDto:
        suggestion, timeline, applied_count = self._magic_cut_suggestion_service.apply(
            suggestion_id,
            payload.operationIds,
            payload.confirmTimelineVersionToken,
            self,
        )
        return MagicCutSuggestionApplyResultDto(
            suggestion=suggestion,
            timeline=self._to_dto(timeline),
            appliedCount=applied_count,
            failedCount=0,
            message=f"已应用 {applied_count} 条智能粗剪建议。",
        )

    def dismiss_magic_cut_suggestion(self, suggestion_id: str) -> MagicCutSuggestionDismissResultDto:
        suggestion = self._magic_cut_suggestion_service.dismiss(suggestion_id)
        return MagicCutSuggestionDismissResultDto(
            suggestion=suggestion,
            message="已忽略本次智能粗剪建议，时间线未修改。",
        )

    def _build_timeline_result(
        self,
        timeline: Timeline,
        *,
        message: str,
        save_source: str,
        save_message: str,
    ) -> WorkspaceTimelineResultDto:
        return WorkspaceTimelineResultDto(
            timeline=self._to_dto(timeline),
            activeTask=self._resolve_active_task(timeline),
            saveState=self._build_save_state(
                timeline,
                source=save_source,
                message=save_message,
            ),
            message=message,
        )

    def _resolve_command_timeline(
        self,
        project_id: str,
        timeline_id: str | None,
    ) -> Timeline:
        if timeline_id is not None:
            timeline = self._load_timeline(timeline_id)
            if timeline.project_id != project_id:
                raise HTTPException(status_code=404, detail="时间线不存在。")
            return timeline

        timeline = self._repository.get_current_for_project(project_id)
        if timeline is None:
            raise HTTPException(status_code=404, detail="时间线不存在。")
        return timeline

    def _save_tracks(
        self,
        timeline: Timeline,
        tracks: list[dict[str, object]],
        message: str,
        save_source: str,
        save_message: str,
    ) -> WorkspaceTimelineResultDto:
        tracks_json = json.dumps(tracks, ensure_ascii=False)
        try:
            updated = self._repository.update_timeline(
                timeline.id,
                name=timeline.name,
                duration_seconds=timeline.duration_seconds,
                tracks_json=tracks_json,
            )
        except Exception as exc:
            log.exception("保存片段变更失败")
            raise HTTPException(status_code=500, detail="保存片段变更失败。") from exc

        if updated is None:
            raise HTTPException(status_code=404, detail="时间线不存在。")

        return self._build_timeline_result(
            updated,
            message=message,
            save_source=save_source,
            save_message=save_message,
        )

    def _find_clip_context(
        self,
        clip_id: str,
    ) -> tuple[Timeline, int, int, TimelineClipDto]:
        timeline, tracks, track_index, clip_index, clip = self._locate_clip(clip_id)
        parsed_clip = TimelineClipDto.model_validate(clip)
        return timeline, track_index, clip_index, parsed_clip

    def _locate_clip(
        self,
        clip_id: str,
    ) -> tuple[Timeline, list[dict[str, object]], int, int, dict[str, object]]:
        for timeline in self._repository.list_all():
            tracks = self._parse_tracks(timeline.tracks_json)
            for track_index, track in enumerate(tracks):
                for clip_index, clip in enumerate(track["clips"]):
                    if str(clip.get("id")) == clip_id:
                        return timeline, tracks, track_index, clip_index, clip
        raise HTTPException(status_code=404, detail="片段不存在。")

    def _locate_clip_for_operation(
        self,
        clip_id: str,
        timeline_id: str | None,
    ) -> tuple[Timeline, list[dict[str, object]], int, int, dict[str, object]]:
        if timeline_id is None:
            return self._locate_clip(clip_id)

        timeline = self._load_timeline(timeline_id)
        tracks = self._parse_tracks(timeline.tracks_json)
        for track_index, track in enumerate(tracks):
            for clip_index, clip in enumerate(track["clips"]):
                if str(clip.get("id")) == clip_id:
                    return timeline, tracks, track_index, clip_index, clip
        raise HTTPException(status_code=404, detail="片段不存在。")

    def _load_timeline(self, timeline_id: str) -> Timeline:
        try:
            timeline = self._repository.get_by_id(timeline_id)
        except Exception as exc:
            log.exception("读取时间线失败")
            raise HTTPException(status_code=500, detail="读取时间线失败。") from exc
        if timeline is None:
            raise HTTPException(status_code=404, detail="时间线不存在。")
        return timeline

    def _to_dto(self, timeline: Timeline) -> TimelineDto:
        tracks = self._parse_tracks(timeline.tracks_json)
        return TimelineDto(
            id=timeline.id,
            projectId=timeline.project_id,
            name=timeline.name,
            status=timeline.status,
            durationSeconds=timeline.duration_seconds,
            source=timeline.source,
            tracks=[TimelineTrackDto.model_validate(track) for track in tracks],
            createdAt=timeline.created_at,
            updatedAt=timeline.updated_at,
            version=self._build_version(timeline, tracks),
            assetReferenceStatus=self._build_asset_reference_status(tracks),
        )

    def _parse_tracks(self, tracks_json: str) -> list[dict[str, object]]:
        try:
            raw_tracks = json.loads(tracks_json)
            if not isinstance(raw_tracks, list):
                raise ValueError("tracks_json must be a list")
            return [self._normalize_track(track) for track in raw_tracks]
        except (TypeError, ValueError, ValidationError) as exc:
            log.exception("解析时间线轨道 JSON 失败")
            raise HTTPException(status_code=500, detail="解析时间线轨道 JSON 失败。") from exc

    def _normalize_track(self, track: object) -> dict[str, object]:
        validated = TimelineTrackDto.model_validate(track)
        return validated.model_dump(mode="json")

    def _validate_and_normalize_tracks(
        self,
        tracks: list[TimelineTrackDto],
    ) -> list[dict[str, object]]:
        normalized_tracks: list[dict[str, object]] = []
        for track in tracks:
            if track.kind not in SUPPORTED_TRACK_KINDS:
                raise HTTPException(status_code=400, detail="时间线轨道类型不支持。")
            normalized_tracks.append(track.model_dump(mode="json"))
        return normalized_tracks

    def _normalize_payload(self, payload: Any) -> dict[str, object]:
        if hasattr(payload, "model_dump"):
            return payload.model_dump(mode="json")  # type: ignore[no-any-return]
        if isinstance(payload, dict):
            return dict(payload)
        raise HTTPException(status_code=400, detail="请求参数不正确。")

    def _find_track_index(
        self,
        tracks: list[dict[str, object]],
        track_id: str,
    ) -> int | None:
        for index, track in enumerate(tracks):
            if str(track.get("id")) == track_id:
                return index
        return None

    def _load_asset(self, asset_id: str) -> Asset:
        if asset_id.strip() == "":
            raise HTTPException(status_code=400, detail="资产 ID 不能为空。")
        if self._asset_repository is None:
            log.error("资产仓储未初始化")
            raise HTTPException(status_code=503, detail="资产服务未就绪，无法使用资产。")
        try:
            asset = self._asset_repository.get_asset(asset_id)
        except Exception as exc:
            log.exception("读取资产失败")
            raise HTTPException(status_code=500, detail="读取资产失败。") from exc
        if asset is None:
            raise HTTPException(status_code=404, detail="资产不存在。")
        return asset

    def _track_kind_for_asset(self, asset: Asset) -> str:
        asset_type = str(asset.type or "").strip().lower()
        target_kind = ASSET_TRACK_KIND_BY_TYPE.get(asset_type)
        if target_kind is None:
            raise HTTPException(status_code=400, detail="该资产类型不支持加入时间线。")
        return target_kind

    def _require_asset_file(self, asset: Asset) -> Path:
        file_path = (asset.file_path or "").strip()
        if file_path == "":
            raise HTTPException(status_code=400, detail="资产缺少源文件路径，无法加入时间线。")
        try:
            source_path = Path(file_path)
            if not source_path.exists() or not source_path.is_file():
                raise HTTPException(status_code=400, detail="资产源文件不存在，无法加入时间线。")
        except HTTPException:
            raise
        except Exception as exc:
            log.exception("检查资产源文件失败")
            raise HTTPException(status_code=400, detail="资产源文件不可用，无法加入时间线。") from exc
        return source_path

    def _resolve_asset_target_track_index(
        self,
        tracks: list[dict[str, object]],
        target_kind: str,
        target_track_id: object,
    ) -> int:
        requested_track_id = str(target_track_id or "").strip()
        if requested_track_id:
            track_index = self._find_track_index(tracks, requested_track_id)
            if track_index is None:
                raise HTTPException(status_code=404, detail="目标轨道不存在。")
            track = tracks[track_index]
            if str(track.get("kind") or "") != target_kind:
                raise HTTPException(status_code=400, detail="资产类型与目标轨道不匹配。")
            return track_index

        for index, track in enumerate(tracks):
            if str(track.get("kind") or "") == target_kind:
                return index
        raise HTTPException(status_code=404, detail="时间线缺少匹配的目标轨道。")

    def _asset_insert_start(self, input_data: dict[str, object], track: dict[str, object]) -> int:
        if input_data.get("startMs") is not None:
            try:
                start_ms = int(input_data["startMs"])
            except (TypeError, ValueError) as exc:
                raise HTTPException(status_code=400, detail="资产入轨起点不正确。") from exc
            if start_ms < 0:
                raise HTTPException(status_code=400, detail="资产入轨起点不能小于 0。")
            return start_ms

        clips = track.get("clips")
        if not isinstance(clips, list):
            return 0
        return max(
            (
                int(clip.get("startMs") or 0) + int(clip.get("durationMs") or 0)
                for clip in clips
                if isinstance(clip, dict)
            ),
            default=0,
        )

    def _resolve_asset_duration_ms(self, asset: Asset) -> int:
        try:
            duration_ms = int(asset.duration_ms) if asset.duration_ms is not None else DEFAULT_ASSET_CLIP_DURATION_MS
        except (TypeError, ValueError):
            duration_ms = DEFAULT_ASSET_CLIP_DURATION_MS
        return max(duration_ms, MIN_ASSET_CLIP_DURATION_MS)

    def _build_asset_clip_id(
        self,
        tracks: list[dict[str, object]],
        asset_id: str,
        start_ms: int,
    ) -> str:
        existing_ids = {str(clip.get("id")) for clip in self._iter_clips(tracks)}
        base_id = f"asset-{asset_id}-{start_ms}"
        if base_id not in existing_ids:
            return base_id

        suffix = 2
        while f"{base_id}-{suffix}" in existing_ids:
            suffix += 1
        return f"{base_id}-{suffix}"

    def _build_asset_clip(
        self,
        asset: Asset,
        *,
        clip_id: str,
        track_id: str,
        start_ms: int,
        duration_ms: int,
    ) -> dict[str, object]:
        return {
            "id": clip_id,
            "trackId": track_id,
            "sourceType": "asset",
            "sourceId": asset.id,
            "label": asset.name,
            "startMs": start_ms,
            "durationMs": duration_ms,
            "inPointMs": 0,
            "outPointMs": duration_ms,
            "status": "ready",
            "prompt": None,
            "resolution": self._asset_resolution_payload(asset),
            "editableFields": ["label", "startMs", "durationMs"],
            "metadata": {
                "sourceKind": "asset",
                "text": asset.name,
            },
        }

    def _build_asset_replacement_clip(
        self,
        track: dict[str, object],
        clip: dict[str, object],
        asset_id: str,
    ) -> dict[str, object]:
        if bool(track.get("locked")):
            raise HTTPException(status_code=400, detail="锁定轨道不能替换片段。")
        asset = self._load_asset(asset_id)
        target_kind = self._track_kind_for_asset(asset)
        self._require_asset_file(asset)
        if str(track.get("kind") or "") != target_kind:
            raise HTTPException(status_code=400, detail="资产类型与目标轨道不匹配。")

        replaced_clip = dict(clip)
        replaced_clip["sourceType"] = "asset"
        replaced_clip["sourceId"] = asset.id
        replaced_clip["label"] = asset.name
        replaced_clip["prompt"] = None
        replaced_clip["resolution"] = self._asset_resolution_payload(asset)
        editable_fields: list[str] = []
        if isinstance(replaced_clip.get("editableFields"), list):
            editable_fields = [
                field
                for field in replaced_clip["editableFields"]
                if isinstance(field, str)
            ]
        for field in ("label", "startMs", "durationMs"):
            if field not in editable_fields:
                editable_fields.append(field)
        replaced_clip["editableFields"] = editable_fields
        replaced_clip["status"] = "ready"
        replaced_clip["metadata"] = {
            "sourceKind": "asset",
            "text": asset.name,
        }
        return replaced_clip

    def _asset_resolution_payload(self, asset: Asset) -> dict[str, int] | None:
        metadata_json = (asset.metadata_json or "").strip()
        if metadata_json == "":
            return None
        try:
            decoded = json.loads(metadata_json)
        except Exception:
            log.warning("解析资产元数据失败 asset_id=%s", asset.id, exc_info=True)
            return None
        if not isinstance(decoded, dict):
            return None
        metadata = {str(key): value for key, value in decoded.items()}
        resolution = metadata.get("resolution")
        if isinstance(resolution, dict):
            metadata = {str(key): value for key, value in resolution.items()}
        try:
            width = int(metadata.get("width"))
            height = int(metadata.get("height"))
        except (TypeError, ValueError):
            return None
        if width <= 0 or height <= 0:
            return None
        return {"width": width, "height": height}

    def _build_split_clip_id(
        self,
        tracks: list[dict[str, object]],
        clip_id: str,
        split_at_ms: int,
    ) -> str:
        existing_ids = {str(clip.get("id")) for clip in self._iter_clips(tracks)}
        base_id = f"{clip_id}-split-{split_at_ms}"
        if base_id not in existing_ids:
            return base_id

        suffix = 2
        while f"{base_id}-{suffix}" in existing_ids:
            suffix += 1
        return f"{base_id}-{suffix}"

    def _clip_overlaps_track(
        self,
        clip: dict[str, object],
        track: dict[str, object],
        *,
        exclude_clip_id: str,
    ) -> bool:
        start_ms = int(clip.get("startMs") or 0)
        duration_ms = int(clip.get("durationMs") or 0)
        end_ms = start_ms + duration_ms
        clips = track.get("clips")
        if not isinstance(clips, list):
            return False

        for other_clip in clips:
            if not isinstance(other_clip, dict):
                continue
            if str(other_clip.get("id")) == exclude_clip_id:
                continue
            other_start_ms = int(other_clip.get("startMs") or 0)
            other_duration_ms = int(other_clip.get("durationMs") or 0)
            other_end_ms = other_start_ms + other_duration_ms
            if start_ms < other_end_ms and end_ms > other_start_ms:
                return True
        return False

    def _build_version(
        self,
        timeline: Timeline,
        tracks: list[dict[str, object]],
    ) -> TimelineVersionDto:
        clip_count = sum(1 for _ in self._iter_clips(tracks))
        version_token = f"{timeline.id}:{timeline.updated_at}:{len(tracks)}:{clip_count}"
        return TimelineVersionDto(
            versionToken=version_token,
            updatedAt=timeline.updated_at,
            trackCount=len(tracks),
            clipCount=clip_count,
        )

    def _build_asset_reference_status(
        self,
        tracks: list[dict[str, object]],
    ) -> AssetReferenceStatusDto:
        total_clips = 0
        ready_clips = 0
        processing_clips = 0
        failed_clips = 0
        missing_reference_clips = 0
        manual_clips = 0
        referenced_clips = 0

        for clip in self._iter_clips(tracks):
            total_clips += 1
            source_type = str(clip.get("sourceType") or "manual")
            source_id = clip.get("sourceId")
            normalized_status = str(clip.get("status") or "ready").strip().lower()
            has_reference = isinstance(source_id, str) and bool(source_id.strip())

            if normalized_status in FAILED_CLIP_STATUSES:
                failed_clips += 1
            elif normalized_status in PROCESSING_CLIP_STATUSES:
                processing_clips += 1
            else:
                ready_clips += 1

            if source_type == "manual":
                manual_clips += 1
            if has_reference:
                referenced_clips += 1
            if source_type != "manual" and not has_reference:
                missing_reference_clips += 1

        return AssetReferenceStatusDto(
            totalClips=total_clips,
            readyClips=ready_clips,
            processingClips=processing_clips,
            failedClips=failed_clips,
            missingReferenceClips=missing_reference_clips,
            manualClips=manual_clips,
            referencedClips=referenced_clips,
        )

    def _resolve_active_task(self, timeline: Timeline) -> WorkspaceActiveTaskDto | None:
        candidates: list[TaskInfo] = []
        for task in self._task_manager.list_active():
            if task.project_id != timeline.project_id:
                continue

            owner_ref = getattr(task, "owner_ref", None)
            if not isinstance(owner_ref, dict):
                continue
            if owner_ref.get("kind") != "timeline" or str(owner_ref.get("id")) != timeline.id:
                continue

            candidates.append(task)

        if not candidates:
            return None

        candidates.sort(key=self._active_task_sort_key, reverse=True)
        active_task = candidates[0]
        return WorkspaceActiveTaskDto(
            id=active_task.id,
            taskType=active_task.task_type,
            status=active_task.status,
            progress=active_task.progress,
            message=active_task.message,
            updatedAt=active_task.updated_at,
        )

    def _active_task_sort_key(self, task: TaskInfo) -> tuple[int, int, str]:
        return (
            1 if task.task_type == "ai-workspace-command" else 0,
            1 if task.status == "running" else 0,
            task.updated_at,
        )

    def _build_save_state(
        self,
        timeline: Timeline,
        *,
        source: str,
        message: str,
    ) -> WorkspaceSaveStateDto:
        return WorkspaceSaveStateDto(
            saved=True,
            updatedAt=timeline.updated_at,
            source=source,
            message=message,
        )

    def _iter_clips(
        self,
        tracks: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        clips: list[dict[str, object]] = []
        for track in tracks:
            raw_clips = track.get("clips")
            if not isinstance(raw_clips, list):
                continue
            clips.extend(clip for clip in raw_clips if isinstance(clip, dict))
        return clips

    def _build_timeline_preview_payload(
        self,
        timeline: Timeline,
        tracks: list[dict[str, object]],
    ) -> dict[str, object]:
        track_summaries: list[dict[str, object]] = []
        clip_count = 0
        total_clip_duration_ms = 0

        for track in tracks:
            clips = track.get("clips")
            if not isinstance(clips, list):
                clips = []

            clip_summaries = [self._summarize_clip(clip) for clip in clips if isinstance(clip, dict)]
            track_clip_count = len(clip_summaries)
            track_clip_duration_ms = sum(int(clip["durationMs"]) for clip in clip_summaries)
            clip_count += track_clip_count
            total_clip_duration_ms = max(total_clip_duration_ms, self._track_end_ms(clip_summaries))
            track_summaries.append(
                {
                    "id": track.get("id"),
                    "kind": track.get("kind"),
                    "name": track.get("name"),
                    "orderIndex": track.get("orderIndex"),
                    "locked": track.get("locked", False),
                    "muted": track.get("muted", False),
                    "clipCount": track_clip_count,
                    "clipDurationMs": track_clip_duration_ms,
                    "clips": clip_summaries,
                }
            )

        return {
            "timelineId": timeline.id,
            "timelineName": timeline.name,
            "status": timeline.status,
            "source": timeline.source,
            "durationSeconds": timeline.duration_seconds,
            "trackCount": len(track_summaries),
            "clipCount": clip_count,
            "totalClipDurationMs": total_clip_duration_ms,
            "tracks": track_summaries,
        }

    def _track_end_ms(self, clips: list[dict[str, object]]) -> int:
        track_end_ms = 0
        for clip in clips:
            start_ms = int(clip.get("startMs") or 0)
            duration_ms = int(clip.get("durationMs") or 0)
            track_end_ms = max(track_end_ms, start_ms + duration_ms)
        return track_end_ms

    def _encode_data_url(self, payload: dict[str, object]) -> str:
        json_payload = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        return f"data:application/json;charset=utf-8,{quote(json_payload, safe='')}"

    def _summarize_clip(self, clip: dict[str, object]) -> dict[str, object]:
        return {
            "id": clip.get("id"),
            "trackId": clip.get("trackId"),
            "label": clip.get("label"),
            "startMs": clip.get("startMs"),
            "durationMs": clip.get("durationMs"),
            "status": clip.get("status"),
            "sourceType": clip.get("sourceType"),
            "sourceId": clip.get("sourceId"),
        }

    def _parse_precheck_tracks(self, tracks_json: str) -> list[object]:
        try:
            raw_tracks = json.loads(tracks_json)
        except (TypeError, ValueError) as exc:
            log.exception("解析时间线预检轨道 JSON 失败")
            raise HTTPException(status_code=500, detail="解析时间线轨道 JSON 失败。") from exc
        if not isinstance(raw_tracks, list):
            return []
        return raw_tracks

    def _build_timeline_precheck_issue_details(
        self,
        timeline_id: str,
        tracks: list[object],
    ) -> list[TimelinePrecheckIssueDto]:
        issues: list[TimelinePrecheckIssueDto] = []
        if not tracks:
            return [
                self._make_precheck_issue(
                    issue_id=f"timeline-{timeline_id}-tracks-missing",
                    message="时间线尚未配置轨道，无法生成本地预检结果。",
                    target_type="timeline",
                    target_id=timeline_id,
                    suggestion="请先汇入创作结果或创建基础轨道。",
                    action_label="汇入创作结果",
                )
            ]

        for track in tracks:
            if not isinstance(track, dict):
                issues.append(
                    self._make_precheck_issue(
                        issue_id=f"timeline-{timeline_id}-track-format",
                        message="时间线存在无法识别的轨道数据。",
                        target_type="timeline",
                        target_id=timeline_id,
                        suggestion="请重新汇入创作结果后再预检。",
                        action_label="重新预检",
                    )
                )
                continue

            track_id = str(track.get("id") or "").strip()
            track_name = str(track.get("name") or track.get("id") or "未命名轨道")
            track_kind = str(track.get("kind") or "")
            if track_kind not in SUPPORTED_TRACK_KINDS:
                issues.append(
                    self._make_precheck_issue(
                        issue_id=f"track-{track_id or track_name}-kind",
                        message=f"轨道 {track_name} 的类型 {track_kind} 不受支持。",
                        target_type="track",
                        target_id=track_id or None,
                        track_id=track_id or None,
                        suggestion="请移除或转换不支持的轨道类型。",
                        action_label="定位轨道",
                    )
                )

            clips = track.get("clips")
            if not isinstance(clips, list):
                issues.append(
                    self._make_precheck_issue(
                        issue_id=f"track-{track_id or track_name}-clips",
                        message=f"轨道 {track_name} 的片段数据格式无效。",
                        target_type="track",
                        target_id=track_id or None,
                        track_id=track_id or None,
                        suggestion="请重新汇入或修复该轨道片段数据。",
                        action_label="定位轨道",
                    )
                )
                continue

            for clip in clips:
                if not isinstance(clip, dict):
                    issues.append(
                        self._make_precheck_issue(
                            issue_id=f"track-{track_id or track_name}-clip-format",
                            message=f"轨道 {track_name} 存在无法识别的片段。",
                            target_type="track",
                            target_id=track_id or None,
                            track_id=track_id or None,
                            suggestion="请删除异常片段或重新汇入创作结果。",
                            action_label="定位轨道",
                        )
                    )
                    continue

                clip_id = str(clip.get("id") or "").strip()
                clip_label = str(clip.get("label") or clip.get("id") or "未命名片段")
                duration_ms = clip.get("durationMs")
                start_ms = clip.get("startMs")
                if not isinstance(duration_ms, int) or duration_ms <= 0:
                    issues.append(
                        self._make_clip_or_track_precheck_issue(
                            issue_id=f"{clip_id or 'clip-' + clip_label}-duration",
                            message=f"片段 {clip_label} 的时长无效。",
                            track_id=track_id,
                            clip_id=clip_id,
                            suggestion="请调整片段时长后重新预检。",
                        )
                    )
                if not isinstance(start_ms, int) or start_ms < 0:
                    issues.append(
                        self._make_clip_or_track_precheck_issue(
                            issue_id=f"{clip_id or 'clip-' + clip_label}-start",
                            message=f"片段 {clip_label} 的起始时间无效。",
                            track_id=track_id,
                            clip_id=clip_id,
                            suggestion="请调整片段起始时间后重新预检。",
                        )
                    )

        return issues

    def _make_clip_or_track_precheck_issue(
        self,
        *,
        issue_id: str,
        message: str,
        track_id: str,
        clip_id: str,
        suggestion: str,
    ) -> TimelinePrecheckIssueDto:
        if clip_id:
            return self._make_precheck_issue(
                issue_id=issue_id,
                message=message,
                target_type="clip",
                target_id=clip_id,
                track_id=track_id or None,
                clip_id=clip_id,
                suggestion=suggestion,
                action_label="定位片段",
            )
        return self._make_precheck_issue(
            issue_id=issue_id,
            message=message,
            target_type="track",
            target_id=track_id or None,
            track_id=track_id or None,
            suggestion=suggestion,
            action_label="定位轨道",
        )

    def _make_precheck_issue(
        self,
        *,
        issue_id: str,
        message: str,
        target_type: str,
        target_id: str | None,
        track_id: str | None = None,
        clip_id: str | None = None,
        suggestion: str | None = None,
        action_label: str | None = None,
    ) -> TimelinePrecheckIssueDto:
        return TimelinePrecheckIssueDto(
            id=issue_id,
            severity="warning",
            message=message,
            targetType=target_type,
            targetId=target_id,
            trackId=track_id,
            clipId=clip_id,
            suggestion=suggestion,
            actionLabel=action_label,
        )
