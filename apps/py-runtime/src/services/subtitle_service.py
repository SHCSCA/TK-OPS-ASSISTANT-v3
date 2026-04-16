from __future__ import annotations

import json
import logging
from uuid import uuid4

from fastapi import HTTPException

from common.time import utc_now_iso
from domain.models import SubtitleTrack
from repositories.subtitle_repository import SubtitleRepository
from schemas.subtitles import (
    SubtitleSegmentDto,
    SubtitleStyleDto,
    SubtitleTrackDto,
    SubtitleTrackGenerateInput,
    SubtitleTrackGenerateResultDto,
    SubtitleTrackUpdateInput,
)

log = logging.getLogger(__name__)

BLOCKED_PROVIDER_MESSAGE = "尚未配置可用字幕对齐 Provider，已保存字幕草稿。"


class SubtitleService:
    def __init__(self, repository: SubtitleRepository) -> None:
        self._repository = repository

    def list_tracks(self, project_id: str) -> list[SubtitleTrackDto]:
        try:
            tracks = self._repository.list_tracks(project_id)
        except Exception as exc:
            log.exception("查询字幕版本列表失败")
            raise HTTPException(status_code=500, detail="查询字幕版本列表失败") from exc
        return [self._to_dto(track) for track in tracks]

    def generate_track(
        self,
        project_id: str,
        payload: SubtitleTrackGenerateInput,
    ) -> SubtitleTrackGenerateResultDto:
        segments = self._split_segments(payload.sourceText)
        if not segments:
            raise HTTPException(
                status_code=400,
                detail="字幕源文本为空，请先在脚本与选题中心创建内容。",
            )

        style = SubtitleStyleDto(preset=payload.stylePreset)
        track = SubtitleTrack(
            id=str(uuid4()),
            project_id=project_id,
            timeline_id=None,
            source="script",
            language=payload.language,
            style_json=json.dumps(style.model_dump(mode="json"), ensure_ascii=False),
            segments_json=json.dumps(
                [segment.model_dump(mode="json") for segment in segments],
                ensure_ascii=False,
            ),
            status="blocked",
            created_at=utc_now_iso(),
        )

        try:
            saved = self._repository.create_track(track)
        except Exception as exc:
            log.exception("创建字幕版本失败")
            raise HTTPException(status_code=500, detail="创建字幕版本失败") from exc

        return SubtitleTrackGenerateResultDto(
            track=self._to_dto(saved),
            task=None,
            message=BLOCKED_PROVIDER_MESSAGE,
        )

    def get_track(self, track_id: str) -> SubtitleTrackDto:
        try:
            track = self._repository.get_track(track_id)
        except Exception as exc:
            log.exception("查询字幕版本详情失败")
            raise HTTPException(status_code=500, detail="查询字幕版本详情失败") from exc
        if track is None:
            raise HTTPException(status_code=404, detail="字幕版本不存在")
        return self._to_dto(track)

    def update_track(
        self,
        track_id: str,
        payload: SubtitleTrackUpdateInput,
    ) -> SubtitleTrackDto:
        segments_json = json.dumps(
            [segment.model_dump(mode="json") for segment in payload.segments],
            ensure_ascii=False,
        )
        style_json = json.dumps(payload.style.model_dump(mode="json"), ensure_ascii=False)
        try:
            track = self._repository.update_track(
                track_id,
                segments_json=segments_json,
                style_json=style_json,
                status="ready",
            )
        except Exception as exc:
            log.exception("保存字幕校正失败")
            raise HTTPException(status_code=500, detail="保存字幕校正失败") from exc
        if track is None:
            raise HTTPException(status_code=404, detail="字幕版本不存在")
        return self._to_dto(track)

    def delete_track(self, track_id: str) -> None:
        try:
            deleted = self._repository.delete_track(track_id)
        except Exception as exc:
            log.exception("删除字幕版本失败")
            raise HTTPException(status_code=500, detail="删除字幕版本失败") from exc
        if not deleted:
            raise HTTPException(status_code=404, detail="字幕版本不存在")

    def _split_segments(self, source_text: str) -> list[SubtitleSegmentDto]:
        return [
            SubtitleSegmentDto(segmentIndex=index, text=text)
            for index, text in enumerate(
                line.strip() for line in source_text.splitlines() if line.strip()
            )
        ]

    def _to_dto(self, track: SubtitleTrack) -> SubtitleTrackDto:
        return SubtitleTrackDto(
            id=track.id,
            projectId=track.project_id,
            timelineId=track.timeline_id,
            source=track.source,
            language=track.language,
            style=self._decode_style(track.style_json),
            segments=self._decode_segments(track.segments_json),
            status=track.status,
            createdAt=track.created_at,
        )

    def _decode_style(self, style_json: str) -> SubtitleStyleDto:
        try:
            raw_style = json.loads(style_json)
        except json.JSONDecodeError:
            log.exception("解析字幕样式失败")
            raise HTTPException(status_code=500, detail="解析字幕样式失败")
        return SubtitleStyleDto.model_validate(raw_style)

    def _decode_segments(self, segments_json: str) -> list[SubtitleSegmentDto]:
        try:
            raw_segments = json.loads(segments_json)
        except json.JSONDecodeError:
            log.exception("解析字幕段落失败")
            raise HTTPException(status_code=500, detail="解析字幕段落失败")
        return [SubtitleSegmentDto.model_validate(item) for item in raw_segments]
