from __future__ import annotations

import json
import logging
from typing import Any
from urllib.parse import quote

from fastapi import HTTPException
from pydantic import ValidationError

from domain.models.timeline import Timeline
from repositories.timeline_repository import TimelineRepository
from schemas.workspace import (
    AssetReferenceStatusDto,
    ClipMoveInput,
    ClipReplaceInput,
    ClipTrimInput,
    TimelineClipDto,
    TimelineCreateInput,
    TimelineDto,
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
from services.task_manager import TaskInfo, TaskManager, task_manager as default_task_manager

log = logging.getLogger(__name__)

SUPPORTED_TRACK_KINDS = {"video", "audio", "subtitle"}
PROCESSING_CLIP_STATUSES = {"queued", "running", "pending", "processing"}
FAILED_CLIP_STATUSES = {"failed", "error", "missing", "invalid"}


class WorkspaceService:
    def __init__(
        self,
        repository: TimelineRepository,
        *,
        task_manager: TaskManager | None = None,
    ) -> None:
        self._repository = repository
        self._task_manager = task_manager or default_task_manager

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
    ) -> WorkspaceTimelineResultDto:
        input_data = self._normalize_payload(payload)
        timeline, tracks, track_index, clip_index, clip = self._locate_clip(clip_id)
        target_track_index = self._find_track_index(tracks, str(input_data["targetTrackId"]))
        if target_track_index is None:
            raise HTTPException(status_code=404, detail="目标轨道不存在。")

        source_track = tracks[track_index]
        target_track = tracks[target_track_index]

        moved_clip = dict(clip)
        moved_clip["trackId"] = target_track["id"]
        moved_clip["startMs"] = int(input_data["startMs"])

        if track_index == target_track_index:
            source_track["clips"][clip_index] = moved_clip
        else:
            source_track["clips"].pop(clip_index)
            target_track["clips"].append(moved_clip)

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
    ) -> WorkspaceTimelineResultDto:
        input_data = self._normalize_payload(payload)
        timeline, tracks, track_index, clip_index, clip = self._locate_clip(clip_id)
        trimmed_clip = dict(clip)
        for field in ("startMs", "durationMs", "inPointMs", "outPointMs"):
            if input_data.get(field) is not None:
                trimmed_clip[field] = input_data[field]
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
        replaced_clip = dict(clip)
        replaced_clip["sourceType"] = str(input_data["sourceType"])
        replaced_clip["sourceId"] = input_data.get("sourceId")
        replaced_clip["label"] = str(input_data["label"])
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

    def fetch_timeline_preview(self, timeline_id: str) -> TimelinePreviewDto:
        timeline = self._load_timeline(timeline_id)
        try:
            tracks = self._parse_tracks(timeline.tracks_json)
            preview_payload = self._build_timeline_preview_payload(timeline, tracks)
            preview_url = self._encode_data_url(preview_payload)
        except HTTPException:
            raise
        except Exception as exc:
            log.exception("生成时间线本地预览失败")
            raise HTTPException(status_code=500, detail="生成时间线本地预览失败。") from exc

        return TimelinePreviewDto(
            timelineId=timeline_id,
            status="ready",
            message="时间线本地预览已生成，包含真实轨道与片段摘要。",
            previewUrl=preview_url,
        )

    def precheck_timeline(self, timeline_id: str) -> TimelinePrecheckDto:
        timeline = self._load_timeline(timeline_id)
        try:
            tracks = self._parse_tracks(timeline.tracks_json)
            issues = self._build_timeline_precheck_issues(tracks)
        except HTTPException:
            raise
        except Exception as exc:
            log.exception("执行时间线本地预检失败")
            raise HTTPException(status_code=500, detail="执行时间线本地预检失败。") from exc

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
        )

    def run_ai_command(
        self,
        project_id: str,
        payload: WorkspaceAICommandInput,
    ) -> WorkspaceAICommandResultDto:
        timeline = self._resolve_command_timeline(project_id, payload.timelineId)

        async def _command_task(progress_callback):
            await progress_callback(55, f"正在分析时间线：{timeline.id}")

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
            total_clip_duration_ms += track_clip_duration_ms
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

    def _build_timeline_precheck_issues(
        self,
        tracks: list[dict[str, object]],
    ) -> list[str]:
        issues: list[str] = []
        if not tracks:
            return ["时间线尚未配置轨道，无法生成本地预检结果。"]

        for track in tracks:
            track_name = str(track.get("name") or track.get("id") or "未命名轨道")
            track_kind = str(track.get("kind") or "")
            if track_kind not in SUPPORTED_TRACK_KINDS:
                issues.append(f"轨道 {track_name} 的类型 {track_kind} 不受支持。")

            clips = track.get("clips")
            if not isinstance(clips, list):
                issues.append(f"轨道 {track_name} 的片段数据格式无效。")
                continue

            for clip in clips:
                if not isinstance(clip, dict):
                    issues.append(f"轨道 {track_name} 存在无法识别的片段。")
                    continue

                clip_label = str(clip.get("label") or clip.get("id") or "未命名片段")
                duration_ms = clip.get("durationMs")
                start_ms = clip.get("startMs")
                if not isinstance(duration_ms, int) or duration_ms <= 0:
                    issues.append(f"片段 {clip_label} 的时长无效。")
                if not isinstance(start_ms, int) or start_ms < 0:
                    issues.append(f"片段 {clip_label} 的起始时间无效。")

        return issues
