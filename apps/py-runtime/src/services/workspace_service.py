from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import HTTPException
from pydantic import ValidationError

from domain.models.timeline import Timeline
from repositories.timeline_repository import TimelineRepository
from schemas.workspace import (
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
    WorkspaceAICommandInput,
    WorkspaceAICommandResultDto,
    WorkspaceClipDetailDto,
    WorkspaceTimelineResultDto,
)
from services.task_manager import TaskManager, task_manager as default_task_manager

log = logging.getLogger(__name__)

SUPPORTED_TRACK_KINDS = {"video", "audio", "subtitle"}

_UNAVAILABLE_PREVIEW_MESSAGE = "时间线预览能力不可用，尚未接入真实媒体帮助器。"
_UNAVAILABLE_PRECHECK_MESSAGE = "时间线预检能力不可用，尚未接入真实媒体帮助器。"


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
                message="当前项目还没有时间线草稿。",
            )

        return WorkspaceTimelineResultDto(
            timeline=self._to_dto(timeline),
            message="已读取时间线草稿。",
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

        return WorkspaceTimelineResultDto(
            timeline=self._to_dto(timeline),
            message="已创建时间线草稿。",
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

        return WorkspaceTimelineResultDto(
            timeline=self._to_dto(timeline),
            message="已保存时间线草稿。",
        )

    def fetch_clip(self, clip_id: str) -> WorkspaceClipDetailDto:
        timeline, track_index, clip_index, clip = self._find_clip_context(clip_id)
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

        return self._save_tracks(timeline, tracks, "片段已移动。")

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
        return self._save_tracks(timeline, tracks, "片段已裁剪。")

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
        resolution = input_data.get("resolution")
        replaced_clip["resolution"] = resolution
        editable_fields = input_data.get("editableFields")
        replaced_clip["editableFields"] = editable_fields if editable_fields is not None else []
        replaced_clip["status"] = "ready"
        tracks[track_index]["clips"][clip_index] = replaced_clip
        return self._save_tracks(timeline, tracks, "片段已替换。")

    def fetch_timeline_preview(self, timeline_id: str) -> TimelinePreviewDto:
        self._load_timeline(timeline_id)
        return TimelinePreviewDto(
            timelineId=timeline_id,
            status="unavailable",
            message=_UNAVAILABLE_PREVIEW_MESSAGE,
            previewUrl=None,
        )

    def precheck_timeline(self, timeline_id: str) -> TimelinePrecheckDto:
        self._load_timeline(timeline_id)
        return TimelinePrecheckDto(
            timelineId=timeline_id,
            status="unavailable",
            message=_UNAVAILABLE_PRECHECK_MESSAGE,
            issues=[],
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

        return WorkspaceTimelineResultDto(
            timeline=self._to_dto(updated),
            message=message,
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
