from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from uuid import uuid4

from fastapi import HTTPException

from ai.providers import has_tts_adapter
from ai.providers.base import TTSRequest, TTSResponse
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
    VoiceWaveformPointDto,
)
from services.ai_capability_service import AICapabilityService, ProviderRuntimeConfig
from services.task_manager import TaskInfo, TaskManager, task_manager as default_task_manager
from services.voice_artifact_store import VoiceArtifactStore

log = logging.getLogger(__name__)

BLOCKED_PROVIDER_MESSAGE = "当前未配置可用 TTS Provider，已保留配音轨草稿。"
PROCESSING_MESSAGE = "配音生成任务已提交。"
WAVEFORM_MISSING_AUDIO_MESSAGE = "未找到音频文件，无法生成波形摘要。"
WAVEFORM_READY_MESSAGE = "已根据音频文件生成波形摘要。"
SEGMENT_REGENERATE_MESSAGE = "片段重生成任务已提交。"
SEGMENT_REGENERATE_BLOCKED_MESSAGE = "片段重生成暂时被阻塞，等待可用 TTS Provider。"
SEGMENT_REGENERATE_FAILED_MESSAGE = "片段重生成失败。"
SEGMENT_REGENERATE_SUCCEEDED_MESSAGE = "片段重生成完成。"

TTSDispatcher = Callable[[ProviderRuntimeConfig, TTSRequest], TTSResponse]


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
        ai_capability_service: AICapabilityService | None = None,
        tts_dispatcher: TTSDispatcher | None = None,
        voice_artifact_store: VoiceArtifactStore | None = None,
    ) -> None:
        self._repository = repository
        self._profile_repository = profile_repository
        self._task_manager = task_manager or default_task_manager
        self._ai_capability_service = ai_capability_service
        self._tts_dispatcher = tts_dispatcher
        self._voice_artifact_store = voice_artifact_store

    def list_profiles(self) -> list[VoiceProfileDto]:
        profiles = self._load_or_seed_profiles()
        return [self._profile_to_dto(profile) for profile in profiles]

    def create_profile(self, payload: VoiceProfileCreateInput) -> VoiceProfileDto:
        if self._profile_repository is None:
            raise HTTPException(status_code=503, detail="音色仓库未初始化。")

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
            raise HTTPException(status_code=500, detail="创建音色配置失败。") from exc
        return self._profile_to_dto(saved)

    def list_tracks(self, project_id: str) -> list[VoiceTrackDto]:
        try:
            tracks = self._repository.list_tracks(project_id)
        except Exception as exc:
            log.exception("查询配音轨列表失败")
            raise HTTPException(status_code=500, detail="查询配音轨列表失败。") from exc
        return [self._to_dto(track) for track in tracks]

    def generate_track(
        self,
        project_id: str,
        payload: VoiceTrackGenerateInput,
    ) -> VoiceTrackGenerateResultDto:
        profile = self._get_profile(payload.profileId)
        segments = self._split_segments(payload.sourceText)
        if not segments:
            raise HTTPException(status_code=400, detail="脚本文本为空，请先准备可用于配音的内容。")

        runtime_config = self._resolve_tts_runtime(profile.provider)
        initial_status = "processing" if runtime_config is not None else "blocked"
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
            status=initial_status,
            created_at=utc_now_iso(),
        )

        try:
            saved = self._repository.create_track(track)
        except Exception as exc:
            log.exception("创建配音轨失败")
            raise HTTPException(status_code=500, detail="创建配音轨失败。") from exc

        if runtime_config is None:
            return VoiceTrackGenerateResultDto(
                track=self._to_dto(saved),
                task=None,
                message=BLOCKED_PROVIDER_MESSAGE,
            )

        tts_request = TTSRequest(
            text=payload.sourceText,
            voice_id=profile.voiceId,
            model=self._resolve_tts_model(profile.provider),
            speed=payload.speed,
            output_format="mp3",
        )

        async def _job(progress_callback) -> None:
            try:
                await progress_callback(15, f"正在生成配音：{profile.displayName}")
                tts_response = await asyncio.to_thread(
                    self._tts_dispatcher,
                    runtime_config,
                    tts_request,
                )
                await progress_callback(75, "正在写入配音文件。")
                file_path = await asyncio.to_thread(
                    self._voice_artifact_store.write_audio,
                    saved.id,
                    audio_bytes=tts_response.audio_bytes,
                    output_format=tts_request.output_format,
                )
                updated = self._repository.update_track(
                    saved.id,
                    file_path=file_path,
                    status="ready",
                    provider=tts_response.provider or profile.provider,
                )
                if updated is None:
                    raise HTTPException(status_code=404, detail="配音轨不存在。")
                await progress_callback(100, "配音生成完成。")
            except Exception:
                log.exception("配音生成失败: track=%s provider=%s", saved.id, profile.provider)
                self._mark_track_failed(saved.id, profile.provider)
                raise

        try:
            task_info = self._submit_task("ai-voice", _job, project_id=project_id)
        except Exception:
            self._mark_track_failed(saved.id, profile.provider)
            raise

        task_data = self._task_payload(
            task_info,
            track_id=saved.id,
            label=f"配音生成：{profile.displayName}",
            message=PROCESSING_MESSAGE,
        )
        return VoiceTrackGenerateResultDto(
            track=self._to_dto(saved),
            task=task_data,
            message=PROCESSING_MESSAGE,
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
        segment = next((item for item in segments if item.segmentIndex == segment_index), None)
        if segment is None:
            raise HTTPException(status_code=404, detail="配音片段不存在。")

        profile_id = payload.profileId or self.list_profiles()[0].id
        profile = self._get_profile(profile_id)
        runtime_config = self._resolve_tts_runtime(profile.provider)
        task_id = str(uuid4())
        label = f"片段重生成：{segment.segmentIndex + 1}"
        segment_text = str(segment.text).strip()
        if segment_text == "":
            raise HTTPException(status_code=400, detail="片段文本为空，无法重生成。")

        if runtime_config is None:
            updated = self._update_segment_regeneration_state(
                track_id=track.id,
                segment_index=segment_index,
                status="blocked",
                profile_id=profile.id,
                task_id=task_id,
                retryable=True,
                message=SEGMENT_REGENERATE_BLOCKED_MESSAGE,
                track_status="blocked",
                provider=profile.provider,
            )
            return VoiceTrackRegenerateResultDto(
                track=self._to_dto(updated),
                task=self._blocked_task_payload(
                    track_id=track.id,
                    project_id=track.project_id,
                    task_id=task_id,
                    label=label,
                    message=SEGMENT_REGENERATE_BLOCKED_MESSAGE,
                ),
                message=SEGMENT_REGENERATE_BLOCKED_MESSAGE,
            )

        updated = self._update_segment_regeneration_state(
            track_id=track.id,
            segment_index=segment_index,
            status="queued",
            profile_id=profile.id,
            task_id=task_id,
            retryable=False,
            message=SEGMENT_REGENERATE_MESSAGE,
            track_status="processing",
            provider=profile.provider,
        )

        tts_request = TTSRequest(
            text=segment_text,
            voice_id=profile.voiceId,
            model=self._resolve_tts_model(profile.provider),
            speed=payload.speed,
            output_format="mp3",
        )

        async def _job(progress_callback) -> None:
            try:
                await progress_callback(15, f"正在重生成片段 {segment.segmentIndex + 1}，使用音色 {profile.displayName}")
                tts_response = await asyncio.to_thread(
                    self._tts_dispatcher,
                    runtime_config,
                    tts_request,
                )
                await progress_callback(75, "正在写入片段音频文件。")
                file_path = await asyncio.to_thread(
                    self._voice_artifact_store.write_audio,
                    f"{track.id}-segment-{segment.segmentIndex + 1}",
                    audio_bytes=tts_response.audio_bytes,
                    output_format=tts_request.output_format,
                )
                self._update_segment_regeneration_state(
                    track_id=track.id,
                    segment_index=segment_index,
                    status="succeeded",
                    profile_id=profile.id,
                    task_id=task_id,
                    retryable=False,
                    message=SEGMENT_REGENERATE_SUCCEEDED_MESSAGE,
                    audio_asset_id=file_path,
                    track_status="ready",
                    provider=tts_response.provider or profile.provider,
                )
                await progress_callback(100, SEGMENT_REGENERATE_SUCCEEDED_MESSAGE)
            except Exception:
                log.exception(
                    "片段重生成失败: track=%s segment=%s provider=%s",
                    track.id,
                    segment.segmentIndex,
                    profile.provider,
                )
                self._update_segment_regeneration_state(
                    track_id=track.id,
                    segment_index=segment_index,
                    status="failed",
                    profile_id=profile.id,
                    task_id=task_id,
                    retryable=True,
                    message=SEGMENT_REGENERATE_FAILED_MESSAGE,
                    track_status="failed",
                    provider=profile.provider,
                )
                raise

        try:
            task_info = self._submit_task(
                "ai-voice",
                _job,
                project_id=track.project_id,
                task_id=task_id,
            )
        except Exception:
            self._update_segment_regeneration_state(
                track_id=track.id,
                segment_index=segment_index,
                status="failed",
                profile_id=profile.id,
                task_id=task_id,
                retryable=True,
                message=SEGMENT_REGENERATE_FAILED_MESSAGE,
                track_status="failed",
                provider=profile.provider,
            )
            raise

        task_data = self._task_payload(
            task_info,
            track_id=track.id,
            label=label,
            message=SEGMENT_REGENERATE_MESSAGE,
        )
        return VoiceTrackRegenerateResultDto(
            track=self._to_dto(updated),
            task=task_data,
            message=SEGMENT_REGENERATE_MESSAGE,
        )

    def fetch_waveform(self, track_id: str) -> VoiceWaveformDto:
        track = self._get_track(track_id)
        if track.file_path is None or track.file_path.strip() == "":
            return VoiceWaveformDto(
                status="missing_audio",
                message=WAVEFORM_MISSING_AUDIO_MESSAGE,
                points=[],
            )

        audio_path = Path(track.file_path)
        if not audio_path.is_file():
            return VoiceWaveformDto(
                status="missing_audio",
                message=WAVEFORM_MISSING_AUDIO_MESSAGE,
                points=[],
            )

        try:
            audio_bytes = audio_path.read_bytes()
        except Exception as exc:
            log.exception("读取配音音频文件失败: track=%s path=%s", track_id, audio_path)
            raise HTTPException(status_code=500, detail="读取配音音频文件失败。") from exc

        if not audio_bytes:
            return VoiceWaveformDto(
                status="empty_audio",
                message="音频文件为空，无法生成波形摘要。",
                points=[],
            )
        return self._build_waveform_summary(audio_bytes)

    def get_track(self, track_id: str) -> VoiceTrackDto:
        return self._to_dto(self._get_track(track_id))

    def delete_track(self, track_id: str) -> None:
        try:
            deleted = self._repository.delete_track(track_id)
        except Exception as exc:
            log.exception("删除配音轨失败: track=%s", track_id)
            raise HTTPException(status_code=500, detail="删除配音轨失败。") from exc
        if not deleted:
            raise HTTPException(status_code=404, detail="配音轨不存在。")

    def _build_waveform_summary(self, audio_bytes: bytes) -> VoiceWaveformDto:
        point_count = min(64, max(16, len(audio_bytes)))
        if point_count <= 0:
            return VoiceWaveformDto(
                status="empty_audio",
                message="音频文件为空，无法生成波形摘要。",
                points=[],
            )

        duration_ms = max(1000, len(audio_bytes) * 4)
        points: list[VoiceWaveformPointDto] = []
        for index in range(point_count):
            start = (len(audio_bytes) * index) // point_count
            end = (len(audio_bytes) * (index + 1)) // point_count
            chunk = audio_bytes[start:end] or audio_bytes[-1:]
            amplitude = sum(abs(byte - 128) for byte in chunk) / (len(chunk) * 127)
            time_ms = round(index * duration_ms / max(1, point_count - 1))
            points.append(
                VoiceWaveformPointDto(
                    timeMs=time_ms,
                    amplitude=round(amplitude, 4),
                )
            )

        return VoiceWaveformDto(
            status="ready",
            message=WAVEFORM_READY_MESSAGE,
            durationMs=duration_ms,
            sampleRate=16000,
            channels=1,
            points=points,
        )

    def _load_segment_records(self, segments_json: str) -> list[dict[str, object]]:
        try:
            raw_segments = json.loads(segments_json)
        except json.JSONDecodeError as exc:
            log.exception("解析配音片段失败")
            raise HTTPException(status_code=500, detail="解析配音片段失败。") from exc
        if not isinstance(raw_segments, list):
            raise HTTPException(status_code=500, detail="解析配音片段失败。")

        records: list[dict[str, object]] = []
        for item in raw_segments:
            if not isinstance(item, dict):
                raise HTTPException(status_code=500, detail="解析配音片段失败。")
            records.append(dict(item))
        return records

    def _update_segment_regeneration_state(
        self,
        *,
        track_id: str,
        segment_index: int,
        status: str,
        profile_id: str,
        task_id: str,
        retryable: bool,
        message: str,
        audio_asset_id: str | None = None,
        track_status: str | None = None,
        provider: str | None = None,
    ) -> VoiceTrack:
        track = self._get_track(track_id)
        segments = self._load_segment_records(track.segments_json)
        target: dict[str, object] | None = None
        for record in segments:
            if int(record.get("segmentIndex", -1)) == segment_index:
                target = record
                break
        if target is None:
            raise HTTPException(status_code=404, detail="配音片段不存在。")

        target["regeneration"] = {
            "status": status,
            "profileId": profile_id,
            "taskId": task_id,
            "retryable": retryable,
            "message": message,
            "updatedAt": utc_now_iso(),
        }
        if audio_asset_id is not None:
            target["audioAssetId"] = audio_asset_id

        try:
            saved = self._repository.update_track(
                track_id,
                segments_json=json.dumps(segments, ensure_ascii=False),
                status=track_status or track.status,
                provider=provider,
            )
        except Exception as exc:
            log.exception("保存片段重生状态失败: track=%s segment=%s", track_id, segment_index)
            raise HTTPException(status_code=500, detail="保存片段重生状态失败。") from exc

        if saved is None:
            raise HTTPException(status_code=404, detail="配音片段不存在。")
        return saved

    def _blocked_task_payload(
        self,
        *,
        track_id: str,
        project_id: str,
        task_id: str,
        label: str,
        message: str,
    ) -> dict[str, object]:
        now = utc_now_iso()
        return {
            "id": task_id,
            "kind": "ai-voice",
            "taskType": "ai-voice",
            "projectId": project_id,
            "ownerRef": {"kind": "voice-track", "id": track_id},
            "label": label,
            "message": message,
            "status": "blocked",
            "progress": 0,
            "retryable": True,
            "createdAt": now,
            "updatedAt": now,
        }

    def _load_or_seed_profiles(self) -> list[VoiceProfile]:
        if self._profile_repository is None:
            return [self._builtin_profile_model(item) for item in self._builtin_profile_definitions()]

        try:
            existing = self._profile_repository.list_profiles()
            existing_ids = {profile.id for profile in existing}
            for builtin in self._builtin_profile_definitions():
                if builtin.id not in existing_ids:
                    self._profile_repository.create_profile(self._builtin_profile_model(builtin))
            return self._profile_repository.list_profiles()
        except Exception as exc:
            log.exception("查询音色配置失败")
            raise HTTPException(status_code=500, detail="查询音色配置失败。") from exc

    def _builtin_profile_definitions(self) -> list[_BuiltinVoiceProfile]:
        return [
            _BuiltinVoiceProfile(
                id="alloy-zh",
                provider="openai",
                voice_id="alloy",
                display_name="清晰女声",
                locale="zh-CN",
                tags=["清晰", "旁白"],
            ),
            _BuiltinVoiceProfile(
                id="nova-zh",
                provider="openai",
                voice_id="nova",
                display_name="温柔讲述",
                locale="zh-CN",
                tags=["温柔", "生活感"],
            ),
            _BuiltinVoiceProfile(
                id="echo-zh",
                provider="openai",
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
            log.exception("查询配音轨详情失败")
            raise HTTPException(status_code=500, detail="查询配音轨详情失败。") from exc
        if track is None:
            raise HTTPException(status_code=404, detail="配音轨不存在。")
        return track

    def _resolve_tts_runtime(self, provider_id: str) -> ProviderRuntimeConfig | None:
        if (
            self._ai_capability_service is None
            or self._tts_dispatcher is None
            or self._voice_artifact_store is None
        ):
            return None

        try:
            runtime = self._ai_capability_service.get_provider_runtime_config(provider_id)
        except HTTPException:
            return None

        if not has_tts_adapter(provider_id):
            return None
        if not runtime.supports_tts:
            return None
        if runtime.base_url.strip() == "":
            return None
        if runtime.requires_secret and not runtime.api_key:
            return None
        return runtime

    def _resolve_tts_model(self, provider_id: str) -> str:
        default_model = "gpt-4o-mini-tts" if provider_id == "openai" else ""
        if self._ai_capability_service is None:
            return default_model

        try:
            capability = self._ai_capability_service.get_capability("tts_generation")
        except HTTPException:
            return default_model

        model = capability.model.strip()
        if capability.provider != provider_id or model == "":
            return default_model
        if provider_id == "openai" and "tts" not in model:
            return default_model
        return model

    def _mark_track_failed(self, track_id: str, provider: str | None) -> None:
        try:
            self._repository.update_track(track_id, status="failed", provider=provider)
        except Exception:
            log.exception("更新配音轨失败状态失败: track=%s", track_id)

    def _submit_task(
        self,
        task_type: str,
        coro_factory,
        *,
        project_id: str | None = None,
        task_id: str | None = None,
    ) -> TaskInfo:
        try:
            return self._task_manager.submit(
                task_type,
                coro_factory,
                project_id=project_id,
                task_id=task_id,
            )
        except Exception as exc:
            log.exception("提交配音任务失败")
            raise HTTPException(status_code=500, detail="提交配音任务失败。") from exc

    def _task_payload(
        self,
        task_info: TaskInfo,
        *,
        track_id: str,
        label: str,
        message: str,
    ) -> dict[str, object]:
        task_info.owner_ref = {"kind": "voice-track", "id": track_id}
        task_info.label = label
        task_info.message = message
        task_data = task_info.to_dict()
        task_data["kind"] = task_info.task_type
        task_data["projectId"] = task_info.project_id
        task_data["ownerRef"] = task_info.owner_ref
        task_data["label"] = label
        task_data["message"] = task_info.message
        return task_data

    def _parse_segment_id(self, segment_id: str) -> int:
        try:
            return int(segment_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail="配音片段不存在。") from exc

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
        except json.JSONDecodeError as exc:
            log.exception("解析音色标签失败")
            raise HTTPException(status_code=500, detail="解析音色标签失败。") from exc
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
        except json.JSONDecodeError as exc:
            log.exception("解析配音片段失败")
            raise HTTPException(status_code=500, detail="解析配音片段失败。") from exc
        return [VoiceTrackSegmentDto.model_validate(item) for item in raw_segments]
