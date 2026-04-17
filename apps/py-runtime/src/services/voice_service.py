from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException

from common.time import utc_now_iso
from domain.models import VoiceProfile, VoiceTrack
from repositories.voice_profile_repository import VoiceProfileRepository
from repositories.voice_repository import VoiceRepository
from schemas.voice import (
    VoiceProfileCreateInput,
    VoiceProfileDto,
    VoiceSegmentRegenerateInput,
    VoiceTrackDto,
    VoiceTrackGenerateInput,
    VoiceTrackGenerateResultDto,
    VoiceTrackRegenerateResultDto,
    VoiceTrackSegmentDto,
    VoiceWaveformDto,
)
from services.task_manager import TaskInfo, TaskManager, task_manager as default_task_manager

log = logging.getLogger(__name__)

BLOCKED_PROVIDER_MESSAGE = "尚未接入可用 TTS Provider，已保存配音草稿。"
WAVEFORM_UNAVAILABLE_MESSAGE = "当前没有真实音频文件，波形预览不可用。"
SEGMENT_REGENERATE_MESSAGE = "段落重生成任务已进入队列。"


@dataclass(frozen=True)
class _BuiltinVoiceProfile:
    id: str
    provider: str
    voice_id: str
    display_name: str
    locale: str
    tags: list[str]


class VoiceService:
    def __init__(
        self,
        repository: VoiceRepository,
        *,
        profile_repository: VoiceProfileRepository | None = None,
        task_manager: TaskManager | None = None,
    ) -> None:
        self._repository = repository
        self._profile_repository = profile_repository
        self._task_manager = task_manager or default_task_manager

    def list_profiles(self) -> list[VoiceProfileDto]:
        profiles = self._load_or_seed_profiles()
        return [self._profile_to_dto(profile) for profile in profiles]

    def create_profile(self, payload: VoiceProfileCreateInput) -> VoiceProfileDto:
        if self._profile_repository is None:
            raise HTTPException(status_code=503, detail="音色仓库未初始化")

        profile = VoiceProfile(
            id=f"{payload.provider}-{payload.voiceId}",
            provider=payload.provider,
            voice_id=payload.voiceId,
            display_name=payload.displayName.strip(),
            locale=payload.locale,
            tags_json=json.dumps(payload.tags, ensure_ascii=False),
            enabled=payload.enabled,
            created_at=utc_now_iso(),
            updated_at=utc_now_iso(),
        )
        try:
            saved = self._profile_repository.create_profile(profile)
        except Exception as exc:
            log.exception("创建音色配置失败")
            raise HTTPException(status_code=500, detail="创建音色配置失败") from exc
        return self._profile_to_dto(saved)

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

    async def regenerate_segment(
        self,
        track_id: str,
        segment_id: str,
        payload: VoiceSegmentRegenerateInput,
    ) -> VoiceTrackRegenerateResultDto:
        track = self._get_track(track_id)
        segments = self._decode_segments(track.segments_json)
        segment_index = self._parse_segment_id(segment_id)
        segment = next(
            (item for item in segments if item.segmentIndex == segment_index),
            None,
        )
        if segment is None:
            raise HTTPException(status_code=404, detail="配音片段不存在")

        profile_id = payload.profileId or self.list_profiles()[0].id
        profile = self._get_profile(profile_id)

        async def _job(progress_callback):
            await progress_callback(
                20,
                f"正在重生成片段 {segment.segmentIndex + 1}，使用音色 {profile.displayName}。",
            )
            await progress_callback(100, "配音片段已重生成。")

        task_info = self._submit_task(
            "ai-voice",
            _job,
            project_id=track.project_id,
        )
        task_info.owner_ref = {"kind": "voice-track", "id": track.id}
        task_info.label = f"配音重生成：{segment.segmentIndex + 1}"
        task_info.message = SEGMENT_REGENERATE_MESSAGE

        return VoiceTrackRegenerateResultDto(
            track=self._to_dto(track),
            task=task_info.to_dict(),
            message=SEGMENT_REGENERATE_MESSAGE,
        )

    def fetch_waveform(self, track_id: str) -> VoiceWaveformDto:
        self._get_track(track_id)
        return VoiceWaveformDto(
            status="unavailable",
            message=WAVEFORM_UNAVAILABLE_MESSAGE,
            points=[],
        )

    def get_track(self, track_id: str) -> VoiceTrackDto:
        return self._to_dto(self._get_track(track_id))

    def delete_track(self, track_id: str) -> None:
        try:
            deleted = self._repository.delete_track(track_id)
        except Exception as exc:
            log.exception("删除配音版本失败")
            raise HTTPException(status_code=500, detail="删除配音版本失败") from exc
        if not deleted:
            raise HTTPException(status_code=404, detail="配音版本不存在")

    def _load_or_seed_profiles(self) -> list[VoiceProfile]:
        if self._profile_repository is None:
            return [
                self._builtin_profile_model(item)
                for item in self._builtin_profile_definitions()
            ]

        try:
            existing = self._profile_repository.list_profiles()
            existing_ids = {profile.id for profile in existing}
            for builtin in self._builtin_profile_definitions():
                if builtin.id not in existing_ids:
                    self._profile_repository.create_profile(
                        self._builtin_profile_model(builtin)
                    )
            return self._profile_repository.list_profiles()
        except Exception as exc:
            log.exception("查询音色配置失败")
            raise HTTPException(status_code=500, detail="查询音色配置失败") from exc

    def _builtin_profile_definitions(self) -> list[_BuiltinVoiceProfile]:
        return [
            _BuiltinVoiceProfile(
                id="alloy-zh",
                provider="pending_provider",
                voice_id="alloy",
                display_name="清晰女声",
                locale="zh-CN",
                tags=["清晰", "旁白"],
            ),
            _BuiltinVoiceProfile(
                id="nova-zh",
                provider="pending_provider",
                voice_id="nova",
                display_name="温柔讲述",
                locale="zh-CN",
                tags=["温柔", "生活感"],
            ),
            _BuiltinVoiceProfile(
                id="echo-zh",
                provider="pending_provider",
                voice_id="echo",
                display_name="沉稳男声",
                locale="zh-CN",
                tags=["沉稳", "解说"],
            ),
        ]

    def _builtin_profile_model(self, builtin: _BuiltinVoiceProfile) -> VoiceProfile:
        now = utc_now_iso()
        return VoiceProfile(
            id=builtin.id,
            provider=builtin.provider,
            voice_id=builtin.voice_id,
            display_name=builtin.display_name,
            locale=builtin.locale,
            tags_json=json.dumps(builtin.tags, ensure_ascii=False),
            enabled=True,
            created_at=now,
            updated_at=now,
        )

    def _get_profile(self, profile_id: str) -> VoiceProfileDto:
        if self._profile_repository is not None:
            profile = self._profile_repository.get_profile(profile_id)
            if profile is not None:
                return self._profile_to_dto(profile)
        for profile in self.list_profiles():
            if profile.id == profile_id:
                return profile
        raise HTTPException(status_code=400, detail="音色不存在，请重新选择。")

    def _get_track(self, track_id: str) -> VoiceTrack:
        try:
            track = self._repository.get_track(track_id)
        except Exception as exc:
            log.exception("查询配音版本详情失败")
            raise HTTPException(status_code=500, detail="查询配音版本详情失败") from exc
        if track is None:
            raise HTTPException(status_code=404, detail="配音版本不存在")
        return track

    def _submit_task(
        self,
        task_type: str,
        coro_factory,
        *,
        project_id: str | None = None,
    ) -> TaskInfo:
        try:
            task = self._task_manager.submit(
                task_type,
                coro_factory,
                project_id=project_id,
            )
        except Exception as exc:
            log.exception("提交配音任务失败")
            raise HTTPException(status_code=500, detail="提交配音任务失败") from exc
        return task

    def _parse_segment_id(self, segment_id: str) -> int:
        try:
            return int(segment_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail="配音片段不存在") from exc

    def _split_segments(self, source_text: str) -> list[VoiceTrackSegmentDto]:
        return [
            VoiceTrackSegmentDto(segmentIndex=index, text=text)
            for index, text in enumerate(
                line.strip() for line in source_text.splitlines() if line.strip()
            )
        ]

    def _profile_to_dto(self, profile: VoiceProfile) -> VoiceProfileDto:
        return VoiceProfileDto(
            id=profile.id,
            provider=profile.provider,
            voiceId=profile.voice_id,
            displayName=profile.display_name,
            locale=profile.locale,
            tags=self._decode_tags(profile.tags_json),
            enabled=profile.enabled,
        )

    def _decode_tags(self, tags_json: str) -> list[str]:
        try:
            raw_tags = json.loads(tags_json)
        except json.JSONDecodeError:
            log.exception("解析音色标签失败")
            raise HTTPException(status_code=500, detail="解析音色标签失败")
        return [str(item) for item in raw_tags]

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
            log.exception("解析配音片段失败")
            raise HTTPException(status_code=500, detail="解析配音片段失败")
        return [VoiceTrackSegmentDto.model_validate(item) for item in raw_segments]
