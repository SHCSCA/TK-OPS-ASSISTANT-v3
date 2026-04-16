from __future__ import annotations

import json
import logging
from uuid import uuid4

from fastapi import HTTPException

from common.time import utc_now_iso
from domain.models import VoiceTrack
from repositories.voice_repository import VoiceRepository
from schemas.voice import (
    VoiceProfileDto,
    VoiceTrackDto,
    VoiceTrackGenerateInput,
    VoiceTrackGenerateResultDto,
    VoiceTrackSegmentDto,
)

log = logging.getLogger(__name__)

BLOCKED_PROVIDER_MESSAGE = "尚未配置可用 TTS Provider，已保存配音版本草稿。"


class VoiceService:
    def __init__(self, repository: VoiceRepository) -> None:
        self._repository = repository

    def list_profiles(self) -> list[VoiceProfileDto]:
        return [
            VoiceProfileDto(
                id="alloy-zh",
                provider="pending_provider",
                voiceId="alloy",
                displayName="清晰叙述",
                locale="zh-CN",
                tags=["清晰", "旁白"],
                enabled=True,
            ),
            VoiceProfileDto(
                id="nova-zh",
                provider="pending_provider",
                voiceId="nova",
                displayName="温柔讲述",
                locale="zh-CN",
                tags=["温柔", "生活感"],
                enabled=True,
            ),
            VoiceProfileDto(
                id="echo-zh",
                provider="pending_provider",
                voiceId="echo",
                displayName="沉稳男声",
                locale="zh-CN",
                tags=["沉稳", "解说"],
                enabled=True,
            ),
        ]

    def list_tracks(self, project_id: str) -> list[VoiceTrackDto]:
        try:
            tracks = self._repository.list_tracks(project_id)
        except Exception as exc:
            log.exception("查询配音版本列表失败")
            raise HTTPException(status_code=500, detail="查询配音版本列表失败") from exc
        return [self._to_dto(track) for track in tracks]

    def generate_track(
        self,
        project_id: str,
        payload: VoiceTrackGenerateInput,
    ) -> VoiceTrackGenerateResultDto:
        profile = self._get_profile(payload.profileId)
        segments = self._split_segments(payload.sourceText)
        if not segments:
            raise HTTPException(
                status_code=400,
                detail="脚本文本为空，请先在脚本与选题中心创建内容。",
            )

        track = VoiceTrack(
            id=str(uuid4()),
            project_id=project_id,
            timeline_id=None,
            source="tts",
            provider=profile.provider,
            voice_name=profile.displayName,
            file_path=None,
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
            log.exception("创建配音版本失败")
            raise HTTPException(status_code=500, detail="创建配音版本失败") from exc

        return VoiceTrackGenerateResultDto(
            track=self._to_dto(saved),
            task=None,
            message=BLOCKED_PROVIDER_MESSAGE,
        )

    def get_track(self, track_id: str) -> VoiceTrackDto:
        try:
            track = self._repository.get_track(track_id)
        except Exception as exc:
            log.exception("查询配音版本详情失败")
            raise HTTPException(status_code=500, detail="查询配音版本详情失败") from exc
        if track is None:
            raise HTTPException(status_code=404, detail="配音版本不存在")
        return self._to_dto(track)

    def delete_track(self, track_id: str) -> None:
        try:
            deleted = self._repository.delete_track(track_id)
        except Exception as exc:
            log.exception("删除配音版本失败")
            raise HTTPException(status_code=500, detail="删除配音版本失败") from exc
        if not deleted:
            raise HTTPException(status_code=404, detail="配音版本不存在")

    def _get_profile(self, profile_id: str) -> VoiceProfileDto:
        for profile in self.list_profiles():
            if profile.id == profile_id:
                return profile
        raise HTTPException(status_code=400, detail="音色不存在，请重新选择。")

    def _split_segments(self, source_text: str) -> list[VoiceTrackSegmentDto]:
        return [
            VoiceTrackSegmentDto(segmentIndex=index, text=text)
            for index, text in enumerate(
                line.strip() for line in source_text.splitlines() if line.strip()
            )
        ]

    def _to_dto(self, track: VoiceTrack) -> VoiceTrackDto:
        return VoiceTrackDto(
            id=track.id,
            projectId=track.project_id,
            timelineId=track.timeline_id,
            source=track.source,
            provider=track.provider,
            voiceName=track.voice_name,
            filePath=track.file_path,
            segments=self._decode_segments(track.segments_json),
            status=track.status,
            createdAt=track.created_at,
        )

    def _decode_segments(self, segments_json: str) -> list[VoiceTrackSegmentDto]:
        try:
            raw_segments = json.loads(segments_json)
        except json.JSONDecodeError:
            log.exception("解析配音段落失败")
            raise HTTPException(status_code=500, detail="解析配音段落失败")
        return [VoiceTrackSegmentDto.model_validate(item) for item in raw_segments]
