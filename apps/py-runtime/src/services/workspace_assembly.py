from __future__ import annotations

import json
import logging
import math
import re
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException

from domain.models.timeline import SubtitleTrack, Timeline, VoiceTrack
from repositories.script_repository import ScriptRepository, StoredScriptVersion
from repositories.storyboard_repository import StoryboardRepository, StoredStoryboardVersion
from repositories.subtitle_repository import SubtitleRepository
from repositories.timeline_repository import TimelineRepository
from repositories.voice_repository import VoiceRepository
from schemas.workspace import (
    WorkspaceAssemblySourceDto,
    WorkspaceAssemblyStateDto,
    WorkspaceTimelineAssembleInput,
    WorkspaceTimelineResultDto,
)
from services.workspace_service import WorkspaceService

log = logging.getLogger(__name__)

MANAGED_VIDEO_TRACK_ID = "managed-video-storyboard"
MANAGED_AUDIO_TRACK_ID = "managed-audio-voice"
MANAGED_SUBTITLE_TRACK_ID = "managed-subtitle-track"
MANAGED_TRACK_IDS = {
    MANAGED_VIDEO_TRACK_ID,
    MANAGED_AUDIO_TRACK_ID,
    MANAGED_SUBTITLE_TRACK_ID,
}
READY_VOICE_STATUSES = {"ready", "completed", "done"}
READY_SUBTITLE_STATUSES = {"aligned", "ready", "completed", "done"}
FALLBACK_SEGMENT_MS = 5000
TIME_RANGE_RE = re.compile(
    r"(?P<start>\d+(?:\.\d+)?)\s*(?:-|–|—|~|至)\s*(?P<end>\d+(?:\.\d+)?)\s*s?",
    re.IGNORECASE,
)
SCRIPT_PREFIX_RE = re.compile(
    r"^\s*(?:S|SH)\d{1,3}\s+\d+(?:\.\d+)?\s*(?:-|–|—|~|至)\s*\d+(?:\.\d+)?s?\s*",
    re.IGNORECASE,
)
CONTINUATION_MARK_RE = re.compile(
    r"[（(]?\s*延续上(?:句|一段)(?:口播|字幕|文案)?\s*[）)]?",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class AssemblySegment:
    index: int
    segment_id: str
    start_ms: int
    end_ms: int
    text: str
    visual_prompt: str | None = None

    @property
    def duration_ms(self) -> int:
        return max(0, self.end_ms - self.start_ms)


@dataclass(frozen=True, slots=True)
class AssemblyContext:
    sources: list[WorkspaceAssemblySourceDto]
    issues: list[str]
    managed_tracks: list[dict[str, object]]


class WorkspaceAssemblyService:
    def __init__(
        self,
        *,
        timeline_repository: TimelineRepository,
        script_repository: ScriptRepository,
        storyboard_repository: StoryboardRepository,
        voice_repository: VoiceRepository,
        subtitle_repository: SubtitleRepository,
        workspace_service: WorkspaceService,
    ) -> None:
        self._timeline_repository = timeline_repository
        self._script_repository = script_repository
        self._storyboard_repository = storyboard_repository
        self._voice_repository = voice_repository
        self._subtitle_repository = subtitle_repository
        self._workspace_service = workspace_service

    def assemble_project_timeline(
        self,
        project_id: str,
        payload: WorkspaceTimelineAssembleInput,
    ) -> WorkspaceTimelineResultDto:
        if payload.mode != "merge_managed":
            raise HTTPException(status_code=400, detail="时间线汇入模式不支持。")

        try:
            timeline = self._resolve_timeline(project_id, payload.timelineName)
            context = self._build_assembly_context(project_id)
            existing_tracks = self._workspace_service._parse_tracks(timeline.tracks_json)
            tracks = self._merge_tracks(existing_tracks, context.managed_tracks)
            updated = self._save_assembled_timeline(
                timeline,
                name=payload.timelineName,
                tracks=tracks,
            )
            assembly_state = WorkspaceAssemblyStateDto(
                status=self._assembly_status(context),
                sources=context.sources,
                issues=context.issues,
            )
            result = self._workspace_service._build_timeline_result(
                updated,
                message=self._assembly_message(context),
                save_source="assembly",
                save_message=self._assembly_save_message(context),
            )
            result.assemblyState = assembly_state
            return result
        except HTTPException:
            raise
        except Exception as exc:
            log.exception("汇入剪辑工作台时间线失败")
            raise HTTPException(status_code=500, detail="汇入剪辑工作台时间线失败。") from exc

    def build_project_assembly_state(self, project_id: str) -> WorkspaceAssemblyStateDto:
        try:
            context = self._build_assembly_context(project_id)
            return WorkspaceAssemblyStateDto(
                status=self._assembly_status(context),
                sources=context.sources,
                issues=context.issues,
            )
        except HTTPException:
            raise
        except Exception as exc:
            log.exception("读取剪辑工作台汇入状态失败")
            raise HTTPException(status_code=500, detail="读取剪辑工作台汇入状态失败。") from exc

    def _build_assembly_context(self, project_id: str) -> AssemblyContext:
        script = self._latest_script(project_id)
        storyboard = self._latest_storyboard(project_id)
        voice_track = self._latest_ready_voice_track(project_id)
        subtitle_track = self._latest_ready_subtitle_track(project_id)

        script_segments = self._build_script_segments(script)
        storyboard_segments = self._build_storyboard_segments(storyboard, script_segments)
        voice_segments = self._build_timed_segments_from_track(
            voice_track.segments_json if voice_track else None,
            default_source="配音",
            script_segments=script_segments,
        )
        subtitle_segments = self._build_timed_segments_from_track(
            subtitle_track.segments_json if subtitle_track else None,
            default_source="字幕",
            script_segments=script_segments,
        )
        sync_segments = self._resolve_sync_segments(
            storyboard_segments,
            script_segments,
            voice_segments,
            subtitle_segments,
        )
        voice_segments = self._align_segments_to_reference(voice_segments, sync_segments)
        subtitle_segments = self._align_segments_to_reference(subtitle_segments, sync_segments)
        issues = self._build_issues(
            script,
            storyboard,
            voice_track,
            subtitle_track,
            storyboard_segments,
        )
        sources = self._build_sources(
            script=script,
            storyboard=storyboard,
            voice_track=voice_track,
            subtitle_track=subtitle_track,
            script_segments=script_segments,
            storyboard_segments=storyboard_segments,
            voice_segments=voice_segments,
            subtitle_segments=subtitle_segments,
        )
        managed_tracks = self._build_managed_tracks(
            script=script,
            storyboard=storyboard,
            voice_track=voice_track,
            subtitle_track=subtitle_track,
            storyboard_segments=storyboard_segments,
            voice_segments=voice_segments,
            subtitle_segments=subtitle_segments,
        )
        return AssemblyContext(
            sources=sources,
            issues=issues,
            managed_tracks=managed_tracks,
        )

    def _assembly_status(self, context: AssemblyContext) -> str:
        return "warning" if context.issues or not context.managed_tracks else "ready"

    def _assembly_message(self, context: AssemblyContext) -> str:
        if self._assembly_status(context) == "ready":
            return "剪辑工作台时间线已从脚本、分镜、配音和字幕汇入。"
        if not context.managed_tracks:
            return "未生成 AI 三轨，请先补齐来源后重新汇入。"
        return "未生成完整 AI 三轨，请先补齐来源后重新汇入；当前仅保留可用受管轨道。"

    def _assembly_save_message(self, context: AssemblyContext) -> str:
        if not context.managed_tracks:
            return "已保存当前时间线状态，未生成 AI 受管轨道。"
        if self._assembly_status(context) != "ready":
            return "已保存可用 AI 受管轨道，仍需补齐缺失来源。"
        return "已保存 M05 剪辑工作台受管轨道。"

    def _resolve_timeline(self, project_id: str, timeline_name: str) -> Timeline:
        timeline = self._timeline_repository.get_current_for_project(project_id)
        if timeline is not None:
            return timeline
        return self._timeline_repository.create_empty(project_id, timeline_name.strip() or "主时间线")

    def _latest_script(self, project_id: str) -> StoredScriptVersion | None:
        versions = self._script_repository.list_versions(project_id)
        return versions[0] if versions else None

    def _latest_storyboard(self, project_id: str) -> StoredStoryboardVersion | None:
        versions = self._storyboard_repository.list_versions(project_id)
        return versions[0] if versions else None

    def _latest_ready_voice_track(self, project_id: str) -> VoiceTrack | None:
        for track in self._voice_repository.list_tracks(project_id):
            if str(track.status or "").lower() in READY_VOICE_STATUSES:
                return track
        return None

    def _latest_ready_subtitle_track(self, project_id: str) -> SubtitleTrack | None:
        for track in self._subtitle_repository.list_tracks(project_id):
            if str(track.status or "").lower() in READY_SUBTITLE_STATUSES:
                return track
        return None

    def _build_script_segments(
        self,
        script: StoredScriptVersion | None,
    ) -> list[AssemblySegment]:
        if script is None:
            return []

        raw_segments = None
        if script.document_json is not None:
            segments = script.document_json.get("segments")
            raw_segments = segments if isinstance(segments, list) else None

        if raw_segments:
            return [
                self._segment_from_mapping(item, index)
                for index, item in enumerate(raw_segments)
                if isinstance(item, dict)
            ]

        lines = [
            self._clean_script_text(line)
            for line in str(script.content or "").splitlines()
            if self._clean_script_text(line)
        ]
        return [
            AssemblySegment(
                index=index,
                segment_id=f"S{index + 1:02d}",
                start_ms=index * FALLBACK_SEGMENT_MS,
                end_ms=(index + 1) * FALLBACK_SEGMENT_MS,
                text=line,
            )
            for index, line in enumerate(lines)
        ]

    def _build_storyboard_segments(
        self,
        storyboard: StoredStoryboardVersion | None,
        script_segments: list[AssemblySegment],
    ) -> list[AssemblySegment]:
        if storyboard is None:
            return []

        scenes = self._extract_storyboard_scenes(storyboard)
        segments: list[AssemblySegment] = []
        for index, scene in enumerate(scenes):
            fallback = script_segments[index] if index < len(script_segments) else None
            start_ms, end_ms = self._parse_time_range_ms(
                scene.get("time"),
                index=index,
                fallback=fallback,
            )
            segment_id = str(
                scene.get("segmentId")
                or (fallback.segment_id if fallback else "")
                or f"S{index + 1:02d}"
            )
            text = self._clean_script_text(
                str(
                    scene.get("subtitle")
                    or scene.get("voiceover")
                    or (fallback.text if fallback else "")
                    or scene.get("summary")
                    or scene.get("title")
                    or f"镜头 {index + 1}"
                )
            )
            visual_prompt = self._clean_script_text(
                str(scene.get("visualPrompt") or scene.get("summary") or scene.get("title") or "")
            )
            segments.append(
                AssemblySegment(
                    index=index,
                    segment_id=segment_id,
                    start_ms=start_ms,
                    end_ms=end_ms,
                    text=text,
                    visual_prompt=visual_prompt or None,
                )
            )
        return segments

    def _extract_storyboard_scenes(
        self,
        storyboard: StoredStoryboardVersion,
    ) -> list[dict[str, object]]:
        if storyboard.storyboard_json is not None:
            shots = storyboard.storyboard_json.get("shots")
            if isinstance(shots, list):
                return [item for item in shots if isinstance(item, dict)]
        return [dict(scene) for scene in storyboard.scenes]

    def _segment_from_mapping(self, item: dict[str, object], index: int) -> AssemblySegment:
        start_ms, end_ms = self._parse_time_range_ms(item.get("time"), index=index)
        text = self._clean_script_text(
            str(
                item.get("subtitle")
                or item.get("voiceover")
                or item.get("voiceOver")
                or item.get("copy")
                or item.get("text")
                or ""
            )
        )
        visual_prompt = self._clean_script_text(
            str(item.get("visualSuggestion") or item.get("visualPrompt") or "")
        )
        return AssemblySegment(
            index=index,
            segment_id=str(item.get("segmentId") or f"S{index + 1:02d}"),
            start_ms=start_ms,
            end_ms=end_ms,
            text=text,
            visual_prompt=visual_prompt or None,
        )

    def _build_timed_segments_from_track(
        self,
        segments_json: str | None,
        *,
        default_source: str,
        script_segments: list[AssemblySegment],
    ) -> list[AssemblySegment]:
        if not segments_json:
            return []

        try:
            loaded = json.loads(segments_json)
        except json.JSONDecodeError:
            log.exception("解析%s分段失败", default_source)
            return []

        if not isinstance(loaded, list):
            return []

        segments: list[AssemblySegment] = []
        for index, item in enumerate(loaded):
            if not isinstance(item, dict):
                continue
            fallback = script_segments[index] if index < len(script_segments) else None
            start_ms = self._coerce_ms(item.get("startMs"), fallback.start_ms if fallback else index * FALLBACK_SEGMENT_MS)
            end_ms = self._coerce_ms(
                item.get("endMs"),
                fallback.end_ms if fallback else start_ms + FALLBACK_SEGMENT_MS,
            )
            if end_ms <= start_ms:
                duration_ms = self._coerce_ms(item.get("durationMs"), FALLBACK_SEGMENT_MS)
                end_ms = start_ms + max(duration_ms, 1)
            text = self._clean_script_text(
                str(item.get("text") or (fallback.text if fallback else "") or default_source)
            )
            segments.append(
                AssemblySegment(
                    index=index,
                    segment_id=fallback.segment_id if fallback else f"S{index + 1:02d}",
                    start_ms=start_ms,
                    end_ms=end_ms,
                    text=text,
                    visual_prompt=fallback.visual_prompt if fallback else None,
                )
            )
        return segments

    def _resolve_sync_segments(
        self,
        *segment_sets: list[AssemblySegment],
    ) -> list[AssemblySegment]:
        for segments in segment_sets:
            if segments:
                return segments
        return []

    def _align_segments_to_reference(
        self,
        segments: list[AssemblySegment],
        reference_segments: list[AssemblySegment],
    ) -> list[AssemblySegment]:
        if not segments or not reference_segments:
            return segments

        by_segment_id = {segment.segment_id: segment for segment in reference_segments}
        aligned: list[AssemblySegment] = []
        for segment in segments:
            reference = by_segment_id.get(segment.segment_id)
            if reference is None and segment.index < len(reference_segments):
                reference = reference_segments[segment.index]
            if reference is None:
                continue
            aligned.append(
                AssemblySegment(
                    index=segment.index,
                    segment_id=segment.segment_id,
                    start_ms=reference.start_ms,
                    end_ms=reference.end_ms,
                    text=segment.text,
                    visual_prompt=segment.visual_prompt or reference.visual_prompt,
                )
            )
        return aligned

    def _build_issues(
        self,
        script: StoredScriptVersion | None,
        storyboard: StoredStoryboardVersion | None,
        voice_track: VoiceTrack | None,
        subtitle_track: SubtitleTrack | None,
        storyboard_segments: list[AssemblySegment],
    ) -> list[str]:
        issues: list[str] = []
        if script is None:
            issues.append("缺少可用脚本。")
        if storyboard is None or not storyboard_segments:
            issues.append("缺少可用分镜。")
        if voice_track is None:
            issues.append("缺少可用配音轨。")
        if subtitle_track is None:
            issues.append("缺少可用字幕轨。")
        return issues

    def _build_sources(
        self,
        *,
        script: StoredScriptVersion | None,
        storyboard: StoredStoryboardVersion | None,
        voice_track: VoiceTrack | None,
        subtitle_track: SubtitleTrack | None,
        script_segments: list[AssemblySegment],
        storyboard_segments: list[AssemblySegment],
        voice_segments: list[AssemblySegment],
        subtitle_segments: list[AssemblySegment],
    ) -> list[WorkspaceAssemblySourceDto]:
        return [
            self._source_dto(
                kind="script",
                status="ready" if script else "missing",
                label=f"脚本 v{script.revision}" if script else "脚本",
                revision=script.revision if script else None,
                segment_count=len(script_segments),
                message="已读取最新脚本。" if script else "未找到可用脚本。",
            ),
            self._source_dto(
                kind="storyboard",
                status="ready" if storyboard and storyboard_segments else "missing",
                label=f"分镜 v{storyboard.revision}" if storyboard else "分镜",
                revision=storyboard.revision if storyboard else None,
                segment_count=len(storyboard_segments),
                message="已读取最新分镜。" if storyboard and storyboard_segments else "未找到可用分镜。",
            ),
            self._source_dto(
                kind="voice",
                status="ready" if voice_track else "missing",
                label=voice_track.voice_name if voice_track else "配音轨",
                track_id=voice_track.id if voice_track else None,
                segment_count=len(voice_segments),
                message="已读取可用配音轨。" if voice_track else "未找到已完成配音轨。",
            ),
            self._source_dto(
                kind="subtitle",
                status="ready" if subtitle_track else "missing",
                label=subtitle_track.language if subtitle_track else "字幕轨",
                track_id=subtitle_track.id if subtitle_track else None,
                segment_count=len(subtitle_segments),
                message="已读取可用字幕轨。" if subtitle_track else "未找到可用字幕轨。",
            ),
        ]

    def _source_dto(
        self,
        *,
        kind: str,
        status: str,
        label: str,
        segment_count: int,
        message: str,
        revision: int | None = None,
        track_id: str | None = None,
    ) -> WorkspaceAssemblySourceDto:
        return WorkspaceAssemblySourceDto(
            kind=kind,
            status=status,
            label=label,
            revision=revision,
            trackId=track_id,
            segmentCount=segment_count,
            message=message,
        )

    def _build_managed_tracks(
        self,
        *,
        script: StoredScriptVersion | None,
        storyboard: StoredStoryboardVersion | None,
        voice_track: VoiceTrack | None,
        subtitle_track: SubtitleTrack | None,
        storyboard_segments: list[AssemblySegment],
        voice_segments: list[AssemblySegment],
        subtitle_segments: list[AssemblySegment],
    ) -> list[dict[str, object]]:
        tracks: list[dict[str, object]] = []
        if storyboard is not None and storyboard_segments:
            tracks.append(
                self._track(
                    track_id=MANAGED_VIDEO_TRACK_ID,
                    kind="video",
                    name="分镜视频轨",
                    order_index=0,
                    clips=[
                        self._storyboard_clip(segment, storyboard_revision=storyboard.revision)
                        for segment in storyboard_segments
                    ],
                )
            )
        if voice_track is not None and voice_segments:
            tracks.append(
                self._track(
                    track_id=MANAGED_AUDIO_TRACK_ID,
                    kind="audio",
                    name="配音轨",
                    order_index=1,
                    clips=[
                        self._voice_clip(segment, voice_track=voice_track)
                        for segment in voice_segments
                    ],
                )
            )
        if subtitle_track is not None and subtitle_segments:
            tracks.append(
                self._track(
                    track_id=MANAGED_SUBTITLE_TRACK_ID,
                    kind="subtitle",
                    name="字幕轨",
                    order_index=2,
                    clips=[
                        self._subtitle_clip(segment, subtitle_track=subtitle_track)
                        for segment in subtitle_segments
                    ],
                )
            )
        return tracks

    def _track(
        self,
        *,
        track_id: str,
        kind: str,
        name: str,
        order_index: int,
        clips: list[dict[str, object]],
    ) -> dict[str, object]:
        return {
            "id": track_id,
            "kind": kind,
            "name": name,
            "orderIndex": order_index,
            "locked": False,
            "muted": False,
            "clips": clips,
        }

    def _storyboard_clip(
        self,
        segment: AssemblySegment,
        *,
        storyboard_revision: int,
    ) -> dict[str, object]:
        return self._clip(
            clip_id=f"managed-video-storyboard-{segment.index + 1:02d}",
            track_id=MANAGED_VIDEO_TRACK_ID,
            source_type="storyboard",
            source_id=f"storyboard:{storyboard_revision}:{segment.segment_id}",
            label=f"{segment.segment_id} · 分镜画面",
            segment=segment,
            status="pending",
            prompt=segment.visual_prompt,
            editable_fields=["label", "startMs", "durationMs", "prompt"],
            metadata={
                "sourceKind": "storyboard",
                "sourceRevision": storyboard_revision,
                "segmentIndex": segment.index,
                "segmentId": segment.segment_id,
                "text": segment.text,
                "visualPrompt": segment.visual_prompt,
            },
        )

    def _voice_clip(self, segment: AssemblySegment, *, voice_track: VoiceTrack) -> dict[str, object]:
        return self._clip(
            clip_id=f"managed-audio-voice-{segment.index + 1:02d}",
            track_id=MANAGED_AUDIO_TRACK_ID,
            source_type="voice_track",
            source_id=voice_track.id,
            label=f"{segment.segment_id} · 配音",
            segment=segment,
            status="ready",
            prompt=segment.text,
            editable_fields=["startMs", "durationMs"],
            metadata={
                "sourceKind": "voice",
                "sourceRevision": int(voice_track.version or 0),
                "segmentIndex": segment.index,
                "segmentId": segment.segment_id,
                "text": segment.text,
                "visualPrompt": segment.visual_prompt,
            },
        )

    def _subtitle_clip(
        self,
        segment: AssemblySegment,
        *,
        subtitle_track: SubtitleTrack,
    ) -> dict[str, object]:
        return self._clip(
            clip_id=f"managed-subtitle-{segment.index + 1:02d}",
            track_id=MANAGED_SUBTITLE_TRACK_ID,
            source_type="subtitle_track",
            source_id=subtitle_track.id,
            label=f"{segment.segment_id} · 字幕",
            segment=segment,
            status="ready",
            prompt=segment.text,
            editable_fields=["label", "startMs", "durationMs"],
            metadata={
                "sourceKind": "subtitle",
                "sourceRevision": None,
                "segmentIndex": segment.index,
                "segmentId": segment.segment_id,
                "text": segment.text,
                "visualPrompt": segment.visual_prompt,
            },
        )

    def _clip(
        self,
        *,
        clip_id: str,
        track_id: str,
        source_type: str,
        source_id: str | None,
        label: str,
        segment: AssemblySegment,
        status: str,
        prompt: str | None,
        editable_fields: list[str],
        metadata: dict[str, object],
    ) -> dict[str, object]:
        return {
            "id": clip_id,
            "trackId": track_id,
            "sourceType": source_type,
            "sourceId": source_id,
            "label": label,
            "startMs": segment.start_ms,
            "durationMs": max(segment.duration_ms, 1),
            "inPointMs": 0,
            "outPointMs": None,
            "status": status,
            "prompt": prompt,
            "resolution": {"width": 1080, "height": 1920} if source_type == "storyboard" else None,
            "editableFields": editable_fields,
            "metadata": metadata,
        }

    def _merge_tracks(
        self,
        existing_tracks: list[dict[str, object]],
        managed_tracks: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        manual_tracks = [
            track
            for track in existing_tracks
            if str(track.get("id")) not in MANAGED_TRACK_IDS
        ]
        merged = [*managed_tracks, *manual_tracks]
        for index, track in enumerate(merged):
            track["orderIndex"] = index
        return merged

    def _save_assembled_timeline(
        self,
        timeline: Timeline,
        *,
        name: str,
        tracks: list[dict[str, object]],
    ) -> Timeline:
        duration_seconds = self._resolve_duration_seconds(tracks)
        updated = self._timeline_repository.update_timeline(
            timeline.id,
            name=name.strip() or timeline.name,
            duration_seconds=duration_seconds,
            tracks_json=json.dumps(tracks, ensure_ascii=False),
        )
        if updated is None:
            raise HTTPException(status_code=404, detail="时间线不存在。")
        return updated

    def _resolve_duration_seconds(self, tracks: list[dict[str, object]]) -> float | None:
        max_end_ms = 0
        for track in tracks:
            clips = track.get("clips")
            if not isinstance(clips, list):
                continue
            for clip in clips:
                if not isinstance(clip, dict):
                    continue
                start_ms = self._coerce_ms(clip.get("startMs"), 0)
                duration_ms = self._coerce_ms(clip.get("durationMs"), 0)
                max_end_ms = max(max_end_ms, start_ms + duration_ms)
        if max_end_ms <= 0:
            return None
        return float(math.ceil(max_end_ms / 1000))

    def _parse_time_range_ms(
        self,
        value: object,
        *,
        index: int,
        fallback: AssemblySegment | None = None,
    ) -> tuple[int, int]:
        if fallback is not None:
            default_start = fallback.start_ms
            default_end = fallback.end_ms
        else:
            default_start = index * FALLBACK_SEGMENT_MS
            default_end = (index + 1) * FALLBACK_SEGMENT_MS

        if value is None:
            return default_start, default_end

        match = TIME_RANGE_RE.search(str(value))
        if match is None:
            return default_start, default_end

        start_ms = int(float(match.group("start")) * 1000)
        end_ms = int(float(match.group("end")) * 1000)
        if end_ms <= start_ms:
            end_ms = start_ms + FALLBACK_SEGMENT_MS
        return start_ms, end_ms

    def _coerce_ms(self, value: object, fallback: int) -> int:
        try:
            return max(0, int(float(value)))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return fallback

    def _clean_script_text(self, value: str) -> str:
        cleaned = SCRIPT_PREFIX_RE.sub("", value.strip())
        cleaned = CONTINUATION_MARK_RE.sub("", cleaned)
        return " ".join(cleaned.split()).strip(" -:：")
