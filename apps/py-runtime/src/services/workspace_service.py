from __future__ import annotations

import json
import logging

from fastapi import HTTPException
from pydantic import ValidationError

from domain.models.timeline import Timeline
from repositories.timeline_repository import TimelineRepository
from schemas.workspace import (
    TimelineCreateInput,
    TimelineDto,
    TimelineTrackDto,
    TimelineUpdateInput,
    WorkspaceAICommandInput,
    WorkspaceAICommandResultDto,
    WorkspaceTimelineResultDto,
)

log = logging.getLogger(__name__)

SUPPORTED_TRACK_KINDS = {"video", "audio", "subtitle"}


class WorkspaceService:
    def __init__(self, repository: TimelineRepository) -> None:
        self._repository = repository

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
        self._validate_tracks(payload.tracks)
        tracks_json = json.dumps(
            [track.model_dump(mode="json") for track in payload.tracks],
            ensure_ascii=False,
        )
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
            log.exception("保存时间线草稿失败")
            raise HTTPException(status_code=500, detail="保存时间线草稿失败。") from exc

        if timeline is None:
            raise HTTPException(status_code=404, detail="时间线草稿不存在。")

        return WorkspaceTimelineResultDto(
            timeline=self._to_dto(timeline),
            message="已保存时间线草稿。",
        )

    def run_ai_command(
        self,
        project_id: str,
        payload: WorkspaceAICommandInput,
    ) -> WorkspaceAICommandResultDto:
        _ = project_id
        _ = payload
        return WorkspaceAICommandResultDto(
            status="blocked",
            task=None,
            message="AI 剪辑命令尚未接入 Provider，本阶段仅保存时间线草稿。",
        )

    def _to_dto(self, timeline: Timeline) -> TimelineDto:
        tracks = self._parse_tracks(timeline.tracks_json)
        return TimelineDto(
            id=timeline.id,
            projectId=timeline.project_id,
            name=timeline.name,
            status=timeline.status,
            durationSeconds=timeline.duration_seconds,
            source=timeline.source,
            tracks=tracks,
            createdAt=timeline.created_at,
            updatedAt=timeline.updated_at,
        )

    def _parse_tracks(self, tracks_json: str) -> list[TimelineTrackDto]:
        try:
            raw_tracks = json.loads(tracks_json)
            if not isinstance(raw_tracks, list):
                raise ValueError("tracks_json must be a list")
            tracks = [TimelineTrackDto.model_validate(item) for item in raw_tracks]
            self._validate_tracks(tracks)
            return tracks
        except (TypeError, ValueError, ValidationError):
            log.exception("解析时间线轨道 JSON 失败")
            return []

    def _validate_tracks(self, tracks: list[TimelineTrackDto]) -> None:
        for track in tracks:
            if track.kind not in SUPPORTED_TRACK_KINDS:
                raise HTTPException(status_code=400, detail="时间线轨道类型不支持。")
