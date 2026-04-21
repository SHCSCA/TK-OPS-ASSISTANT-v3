from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from uuid import uuid4

from fastapi import HTTPException

from common.time import utc_now_iso
from domain.models import SubtitleTrack, VoiceTrack
from repositories.subtitle_repository import SubtitleRepository
from repositories.voice_repository import VoiceRepository
from schemas.subtitles import (
    SubtitleAlignmentDiffSummaryDto,
    SubtitleAlignmentDto,
    SubtitleExportDto,
    SubtitleExportInput,
    SubtitleSegmentDto,
    SubtitleSourceVoiceDto,
    SubtitleStyleDto,
    SubtitleStyleTemplateDto,
    SubtitleTrackAlignInput,
    SubtitleTrackDto,
    SubtitleTrackGenerateInput,
    SubtitleTrackGenerateResultDto,
    SubtitleTrackUpdateInput,
)

log = logging.getLogger(__name__)

ALIGN_MESSAGE = "\u5b57\u5e55\u65f6\u95f4\u7801\u5df2\u66f4\u65b0\u3002"
EXPORT_MESSAGE = "\u5b57\u5e55\u5bfc\u51fa\u5b8c\u6210\u3002"
GENERATE_MESSAGE = "\u5b57\u5e55\u8f68\u9053\u5df2\u57fa\u4e8e\u672c\u5730\u6587\u672c\u89c4\u5219\u751f\u6210\u3002"
MISSING_SOURCE_TEXT_MESSAGE = "\u5b57\u5e55\u6e90\u6587\u672c\u4e0d\u80fd\u4e3a\u7a7a\uff0c\u8bf7\u5148\u5728\u811a\u672c\u6216\u9009\u9898\u4e2d\u5fc3\u63d0\u4f9b\u5185\u5bb9\u3002"
MISSING_TIMECODE_MESSAGE = "\u5b57\u5e55\u7247\u6bb5\u7f3a\u5c11\u6709\u6548\u65f6\u95f4\u7801\uff0c\u65e0\u6cd5\u5b8c\u6210\u5bf9\u9f50\u6216\u5bfc\u51fa\u3002"
INVALID_TIMECODE_MESSAGE = "\u5b57\u5e55\u7247\u6bb5\u65f6\u95f4\u7801\u65e0\u6548\uff0c\u8bf7\u5148\u4fee\u6b63\u540e\u518d\u91cd\u8bd5\u3002"
SOURCE_VOICE_NOT_FOUND_MESSAGE = "\u6307\u5b9a\u7684\u6765\u6e90\u97f3\u8f68\u4e0d\u5b58\u5728\uff0c\u8bf7\u91cd\u65b0\u9009\u62e9\u540e\u518d\u751f\u6210\u5b57\u5e55\u3002"


@dataclass(frozen=True)
class _BuiltinSubtitleStyleTemplate:
    id: str
    name: str
    description: str
    style: SubtitleStyleDto


class SubtitleService:
    def __init__(
        self,
        repository: SubtitleRepository,
        *,
        voice_repository: VoiceRepository | None = None,
    ) -> None:
        self._repository = repository
        self._voice_repository = voice_repository

    def list_tracks(self, project_id: str) -> list[SubtitleTrackDto]:
        try:
            tracks = self._repository.list_tracks(project_id)
        except Exception as exc:
            log.exception("\u67e5\u8be2\u5b57\u5e55\u8f68\u9053\u5217\u8868\u5931\u8d25")
            raise HTTPException(status_code=500, detail="\u67e5\u8be2\u5b57\u5e55\u8f68\u9053\u5217\u8868\u5931\u8d25\u3002") from exc
        return [self._to_dto(track) for track in tracks]

    def generate_track(
        self,
        project_id: str,
        payload: SubtitleTrackGenerateInput,
    ) -> SubtitleTrackGenerateResultDto:
        segments = self._split_segments(payload.sourceText)
        if not segments:
            raise HTTPException(status_code=400, detail=MISSING_SOURCE_TEXT_MESSAGE)

        style = self._resolve_style(payload.stylePreset)
        generated_at = utc_now_iso()
        source_voice = self._resolve_source_voice(payload.sourceVoiceTrackId)
        alignment_status = "pending_alignment" if source_voice is not None else "draft"
        metadata = self._build_metadata(
            source_voice=source_voice,
            alignment_status=alignment_status,
            diff_summary=None,
            error_code=None,
            error_message=None,
            next_action=(
                "\u8fd0\u884c\u5b57\u5e55\u5bf9\u9f50\uff0c\u786e\u8ba4\u5b57\u5e55\u65f6\u95f4\u7801\u4e0e\u97f3\u8f68\u4fdd\u6301\u4e00\u81f4\u3002"
                if source_voice is not None
                else "\u5148\u9009\u62e9\u6765\u6e90\u97f3\u8f68\uff0c\u518d\u6267\u884c\u5b57\u5e55\u5bf9\u9f50\u3002"
            ),
            updated_at=generated_at,
        )
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
            metadata_json=json.dumps(metadata, ensure_ascii=False),
            status="ready",
            created_at=generated_at,
            updated_at=generated_at,
        )

        try:
            saved = self._repository.create_track(track)
        except Exception as exc:
            log.exception("\u521b\u5efa\u5b57\u5e55\u8f68\u9053\u5931\u8d25")
            raise HTTPException(status_code=500, detail="\u521b\u5efa\u5b57\u5e55\u8f68\u9053\u5931\u8d25\u3002") from exc

        return SubtitleTrackGenerateResultDto(
            track=self._to_dto(saved),
            task={
                "kind": "local-subtitle-generate",
                "mode": "deterministic-local",
                "language": payload.language,
                "stylePreset": style.preset,
                "segmentCount": len(segments),
                "sourceCharacters": len(payload.sourceText),
                "generatedAt": generated_at,
                "sourceVoiceTrackId": payload.sourceVoiceTrackId,
            },
            message=GENERATE_MESSAGE,
        )

    def align_track(
        self,
        track_id: str,
        payload: SubtitleTrackAlignInput,
    ) -> SubtitleTrackDto:
        track = self._get_track(track_id)
        style = self._decode_style(track.style_json)
        self._validate_segments_have_timecodes(payload.segments)
        segments_json = json.dumps(
            [segment.model_dump(mode="json") for segment in payload.segments],
            ensure_ascii=False,
        )
        diff_summary = self._build_diff_summary(
            self._decode_segments(track.segments_json),
            payload.segments,
        )
        updated_at = utc_now_iso()
        metadata = self._decode_metadata(track.metadata_json)
        metadata["alignment"] = self._alignment_payload(
            status="aligned",
            updated_at=updated_at,
            diff_summary=diff_summary.model_dump(mode="json"),
            error_code=None,
            error_message=None,
            next_action="\u53ef\u7ee7\u7eed\u5bfc\u51fa\u5b57\u5e55\uff0c\u6216\u56de\u5230\u5b57\u5e55\u7f16\u8f91\u4e2d\u5fae\u8c03\u6587\u6848\u3002",
        )
        try:
            saved = self._repository.update_track(
                track_id,
                segments_json=segments_json,
                style_json=json.dumps(style.model_dump(mode="json"), ensure_ascii=False),
                metadata_json=json.dumps(metadata, ensure_ascii=False),
                status="ready",
                updated_at=updated_at,
            )
        except Exception as exc:
            log.exception("\u4fdd\u5b58\u5b57\u5e55\u5bf9\u9f50\u7ed3\u679c\u5931\u8d25")
            raise HTTPException(status_code=500, detail="\u4fdd\u5b58\u5b57\u5e55\u5bf9\u9f50\u7ed3\u679c\u5931\u8d25\u3002") from exc
        if saved is None:
            raise HTTPException(status_code=404, detail="\u5b57\u5e55\u8f68\u9053\u4e0d\u5b58\u5728\u3002")
        return self._to_dto(saved)

    def list_style_templates(self) -> list[SubtitleStyleTemplateDto]:
        return [
            SubtitleStyleTemplateDto(
                id=item.id,
                name=item.name,
                description=item.description,
                style=item.style,
            )
            for item in self._builtin_style_templates()
        ]

    def export_track(
        self,
        track_id: str,
        payload: SubtitleExportInput,
    ) -> SubtitleExportDto:
        track = self._get_track(track_id)
        segments = self._decode_segments(track.segments_json)
        self._validate_segments_have_timecodes(segments)

        content = self._build_export_content(payload.format, segments)
        return SubtitleExportDto(
            trackId=track.id,
            format=payload.format,
            fileName=f"{track.id}.{payload.format}",
            content=content,
            lineCount=len(content.splitlines()),
            status="ready",
            message=EXPORT_MESSAGE,
        )

    def get_track(self, track_id: str) -> SubtitleTrackDto:
        return self._to_dto(self._get_track(track_id))

    def update_track(
        self,
        track_id: str,
        payload: SubtitleTrackUpdateInput,
    ) -> SubtitleTrackDto:
        segments = payload.segments
        has_valid_timecodes = self._segments_have_valid_timecodes(segments)
        updated_at = utc_now_iso()
        current_track = self._get_track(track_id)
        current_segments = self._decode_segments(current_track.segments_json)
        diff_summary = self._build_diff_summary(current_segments, segments)
        metadata = self._decode_metadata(current_track.metadata_json)
        metadata["alignment"] = self._alignment_payload(
            status="edited" if has_valid_timecodes else "needs_alignment",
            updated_at=updated_at,
            diff_summary=diff_summary.model_dump(mode="json"),
            error_code=None if has_valid_timecodes else "subtitle.timecode_incomplete",
            error_message=None if has_valid_timecodes else MISSING_TIMECODE_MESSAGE,
            next_action=(
                "\u53ef\u7ee7\u7eed\u5bfc\u51fa\u5b57\u5e55\uff0c\u6216\u518d\u6b21\u6267\u884c\u5b57\u5e55\u5bf9\u9f50\u786e\u8ba4\u65f6\u95f4\u7801\u3002"
                if has_valid_timecodes
                else "\u8bf7\u91cd\u65b0\u6267\u884c\u5b57\u5e55\u5bf9\u9f50\uff0c\u8865\u9f50\u5b57\u5e55\u65f6\u95f4\u7801\u3002"
            ),
        )
        segments_json = json.dumps(
            [segment.model_dump(mode="json") for segment in segments],
            ensure_ascii=False,
        )
        style_json = json.dumps(payload.style.model_dump(mode="json"), ensure_ascii=False)
        try:
            track = self._repository.update_track(
                track_id,
                segments_json=segments_json,
                style_json=style_json,
                metadata_json=json.dumps(metadata, ensure_ascii=False),
                status="ready" if has_valid_timecodes else "draft",
                updated_at=updated_at,
            )
        except Exception as exc:
            log.exception("\u4fdd\u5b58\u5b57\u5e55\u6821\u6b63\u7ed3\u679c\u5931\u8d25")
            raise HTTPException(status_code=500, detail="\u4fdd\u5b58\u5b57\u5e55\u6821\u6b63\u7ed3\u679c\u5931\u8d25\u3002") from exc
        if track is None:
            raise HTTPException(status_code=404, detail="\u5b57\u5e55\u8f68\u9053\u4e0d\u5b58\u5728\u3002")
        return self._to_dto(track)

    def delete_track(self, track_id: str) -> None:
        try:
            deleted = self._repository.delete_track(track_id)
        except Exception as exc:
            log.exception("\u5220\u9664\u5b57\u5e55\u8f68\u9053\u5931\u8d25")
            raise HTTPException(status_code=500, detail="\u5220\u9664\u5b57\u5e55\u8f68\u9053\u5931\u8d25\u3002") from exc
        if not deleted:
            raise HTTPException(status_code=404, detail="\u5b57\u5e55\u8f68\u9053\u4e0d\u5b58\u5728\u3002")

    def _builtin_style_templates(self) -> list[_BuiltinSubtitleStyleTemplate]:
        return [
            _BuiltinSubtitleStyleTemplate(
                id="creator-default",
                name="\u521b\u4f5c\u8005\u9ed8\u8ba4",
                description="\u9002\u5408\u5927\u591a\u6570\u7ad6\u5c4f\u521b\u4f5c\u89c6\u9891\u7684\u57fa\u7840\u6837\u5f0f\u3002",
                style=SubtitleStyleDto(
                    preset="creator-default",
                    fontSize=32,
                    position="bottom",
                    textColor="#FFFFFF",
                    background="rgba(0,0,0,0.62)",
                ),
            ),
            _BuiltinSubtitleStyleTemplate(
                id="clean-contrast",
                name="\u9ad8\u5bf9\u6bd4\u7b80\u6d01",
                description="\u66f4\u9002\u5408\u590d\u6742\u80cc\u666f\u7684\u89c6\u9891\u5b57\u5e55\u3002",
                style=SubtitleStyleDto(
                    preset="clean-contrast",
                    fontSize=34,
                    position="bottom",
                    textColor="#F8F8F8",
                    background="rgba(0,0,0,0.72)",
                ),
            ),
            _BuiltinSubtitleStyleTemplate(
                id="center-highlight",
                name="\u5c45\u4e2d\u5f3a\u8c03",
                description="\u9002\u5408\u8282\u594f\u5316\u53e3\u64ad\u6216\u91cd\u70b9\u5f3a\u8c03\u7247\u6bb5\u3002",
                style=SubtitleStyleDto(
                    preset="center-highlight",
                    fontSize=38,
                    position="center",
                    textColor="#FFFFFF",
                    background="rgba(12,12,12,0.72)",
                ),
            ),
        ]

    def _resolve_style(self, preset: str) -> SubtitleStyleDto:
        for template in self._builtin_style_templates():
            if template.id == preset:
                return template.style
        return SubtitleStyleDto(preset=preset)

    def _build_export_content(
        self,
        format_name: str,
        segments: list[SubtitleSegmentDto],
    ) -> str:
        if format_name == "srt":
            return self._build_srt(segments)
        if format_name == "vtt":
            return self._build_vtt(segments)
        return self._build_ass(segments)

    def _build_srt(self, segments: list[SubtitleSegmentDto]) -> str:
        blocks = []
        for index, segment in enumerate(segments, start=1):
            blocks.append(
                "\n".join(
                    [
                        str(index),
                        f"{self._format_srt_time(segment.startMs)} --> {self._format_srt_time(segment.endMs)}",
                        segment.text,
                    ]
                )
            )
        return "\n\n".join(blocks) + "\n"

    def _build_vtt(self, segments: list[SubtitleSegmentDto]) -> str:
        lines = ["WEBVTT", ""]
        for segment in segments:
            lines.extend(
                [
                    f"{self._format_vtt_time(segment.startMs)} --> {self._format_vtt_time(segment.endMs)}",
                    segment.text,
                    "",
                ]
            )
        return "\n".join(lines)

    def _build_ass(self, segments: list[SubtitleSegmentDto]) -> str:
        lines = [
            "[Script Info]",
            "ScriptType: v4.00+",
            "",
            "[V4+ Styles]",
            "Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
            "Style: Default,Arial,32,&H00FFFFFF,&H00000000,&H9A000000,0,0,0,0,100,100,0,0,1,2,0,2,20,20,30,1",
            "",
            "[Events]",
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
        ]
        for segment in segments:
            lines.append(
                "Dialogue: 0,{start},{end},Default,,0,0,0,,{text}".format(
                    start=self._format_ass_time(segment.startMs),
                    end=self._format_ass_time(segment.endMs),
                    text=segment.text,
                )
            )
        return "\n".join(lines) + "\n"

    def _format_srt_time(self, milliseconds: int | None) -> str:
        milliseconds = self._ensure_timecode_value(milliseconds)
        total_seconds, ms = divmod(milliseconds, 1000)
        minutes, seconds = divmod(total_seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{ms:03d}"

    def _format_vtt_time(self, milliseconds: int | None) -> str:
        milliseconds = self._ensure_timecode_value(milliseconds)
        total_seconds, ms = divmod(milliseconds, 1000)
        minutes, seconds = divmod(total_seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{ms:03d}"

    def _format_ass_time(self, milliseconds: int | None) -> str:
        milliseconds = self._ensure_timecode_value(milliseconds)
        total_seconds, ms = divmod(milliseconds, 1000)
        minutes, seconds = divmod(total_seconds, 60)
        hours, minutes = divmod(minutes, 60)
        centiseconds = ms // 10
        return f"{hours:d}:{minutes:02d}:{seconds:02d}.{centiseconds:02d}"

    def _split_segments(self, source_text: str) -> list[SubtitleSegmentDto]:
        segments: list[SubtitleSegmentDto] = []
        current_start_ms = 0
        for index, text in enumerate(self._split_source_text(source_text)):
            duration_ms = self._estimate_segment_duration_ms(text)
            segments.append(
                SubtitleSegmentDto(
                    segmentIndex=index,
                    text=text,
                    startMs=current_start_ms,
                    endMs=current_start_ms + duration_ms,
                )
            )
            current_start_ms += duration_ms + 120
        return segments

    def _split_source_text(self, source_text: str) -> list[str]:
        segments: list[str] = []
        for raw_line in source_text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            parts = [
                part.strip()
                for part in re.split(r"(?<=[\u3002\uff01\uff1f!?])\s*", line)
                if part.strip()
            ]
            if parts:
                segments.extend(parts)
            else:
                segments.append(line)
        return segments

    def _estimate_segment_duration_ms(self, text: str) -> int:
        normalized_text = re.sub(r"\s+", "", text)
        char_count = max(len(normalized_text), 1)
        return max(900, min(5000, 900 + char_count * 120))

    def _get_track(self, track_id: str) -> SubtitleTrack:
        try:
            track = self._repository.get_track(track_id)
        except Exception as exc:
            log.exception("\u67e5\u8be2\u5b57\u5e55\u8f68\u9053\u8be6\u60c5\u5931\u8d25")
            raise HTTPException(status_code=500, detail="\u67e5\u8be2\u5b57\u5e55\u8f68\u9053\u8be6\u60c5\u5931\u8d25\u3002") from exc
        if track is None:
            raise HTTPException(status_code=404, detail="\u5b57\u5e55\u8f68\u9053\u4e0d\u5b58\u5728\u3002")
        return track

    def _resolve_source_voice(self, track_id: str | None) -> SubtitleSourceVoiceDto | None:
        if track_id is None:
            return None
        if self._voice_repository is None:
            raise HTTPException(status_code=503, detail="\u6765\u6e90\u97f3\u8f68\u4ed3\u5e93\u672a\u521d\u59cb\u5316\u3002")
        try:
            voice_track = self._voice_repository.get_track(track_id)
        except Exception as exc:
            log.exception("\u67e5\u8be2\u6765\u6e90\u97f3\u8f68\u5931\u8d25")
            raise HTTPException(status_code=500, detail="\u67e5\u8be2\u6765\u6e90\u97f3\u8f68\u5931\u8d25\u3002") from exc
        if voice_track is None:
            raise HTTPException(status_code=404, detail=SOURCE_VOICE_NOT_FOUND_MESSAGE)
        return self._voice_track_to_source_dto(voice_track)

    def _voice_track_to_source_dto(self, track: VoiceTrack) -> SubtitleSourceVoiceDto:
        return SubtitleSourceVoiceDto(
            trackId=track.id,
            revision=int(track.version or 1),
            updatedAt=track.updated_at or track.created_at,
        )

    def _default_alignment_payload(self, *, track: SubtitleTrack, updated_at: str) -> dict[str, object]:
        has_valid_timecodes = self._segments_have_valid_timecodes(self._decode_segments(track.segments_json))
        return self._alignment_payload(
            status="aligned" if has_valid_timecodes else "needs_alignment",
            updated_at=updated_at,
            diff_summary=None,
            error_code=None if has_valid_timecodes else "subtitle.timecode_incomplete",
            error_message=None if has_valid_timecodes else MISSING_TIMECODE_MESSAGE,
            next_action=(
                "\u53ef\u7ee7\u7eed\u5bfc\u51fa\u5b57\u5e55\uff0c\u6216\u56de\u5230\u5b57\u5e55\u7f16\u8f91\u4e2d\u5fae\u8c03\u6587\u6848\u3002"
                if has_valid_timecodes
                else "\u8bf7\u91cd\u65b0\u6267\u884c\u5b57\u5e55\u5bf9\u9f50\uff0c\u8865\u9f50\u5b57\u5e55\u65f6\u95f4\u7801\u3002"
            ),
        )

    def _alignment_payload(
        self,
        *,
        status: str,
        updated_at: str,
        diff_summary: dict[str, object] | None,
        error_code: str | None,
        error_message: str | None,
        next_action: str | None,
    ) -> dict[str, object]:
        return {
            "status": status,
            "diffSummary": diff_summary,
            "errorCode": error_code,
            "errorMessage": error_message,
            "nextAction": next_action,
            "updatedAt": updated_at,
        }

    def _build_metadata(
        self,
        *,
        source_voice: SubtitleSourceVoiceDto | None,
        alignment_status: str,
        diff_summary: SubtitleAlignmentDiffSummaryDto | None,
        error_code: str | None,
        error_message: str | None,
        next_action: str | None,
        updated_at: str,
    ) -> dict[str, object]:
        return {
            "sourceVoice": (
                source_voice.model_dump(mode="json") if source_voice is not None else None
            ),
            "alignment": self._alignment_payload(
                status=alignment_status,
                updated_at=updated_at,
                diff_summary=(
                    diff_summary.model_dump(mode="json") if diff_summary is not None else None
                ),
                error_code=error_code,
                error_message=error_message,
                next_action=next_action,
            ),
        }

    def _decode_metadata(self, metadata_json: str) -> dict[str, object]:
        raw_metadata = metadata_json.strip()
        if raw_metadata == "":
            return {}
        try:
            metadata = json.loads(raw_metadata)
        except json.JSONDecodeError as exc:
            log.exception("\u89e3\u6790\u5b57\u5e55\u5143\u6570\u636e\u5931\u8d25")
            raise HTTPException(status_code=500, detail="\u89e3\u6790\u5b57\u5e55\u5143\u6570\u636e\u5931\u8d25\u3002") from exc
        if not isinstance(metadata, dict):
            raise HTTPException(status_code=500, detail="\u89e3\u6790\u5b57\u5e55\u5143\u6570\u636e\u5931\u8d25\u3002")
        return dict(metadata)

    def _decode_alignment(
        self,
        metadata: dict[str, object],
        *,
        track: SubtitleTrack,
    ) -> SubtitleAlignmentDto:
        payload = metadata.get("alignment")
        if not isinstance(payload, dict):
            payload = self._default_alignment_payload(
                track=track,
                updated_at=track.updated_at or track.created_at,
            )
        diff_summary = payload.get("diffSummary")
        return SubtitleAlignmentDto(
            status=str(payload.get("status") or "draft"),
            diffSummary=(
                SubtitleAlignmentDiffSummaryDto.model_validate(diff_summary)
                if isinstance(diff_summary, dict)
                else None
            ),
            errorCode=self._string_or_none(payload.get("errorCode")),
            errorMessage=self._string_or_none(payload.get("errorMessage")),
            nextAction=self._string_or_none(payload.get("nextAction")),
            updatedAt=self._string_or_none(payload.get("updatedAt"), fallback=track.updated_at or track.created_at) or track.created_at,
        )

    def _decode_source_voice(self, metadata: dict[str, object]) -> SubtitleSourceVoiceDto | None:
        payload = metadata.get("sourceVoice")
        if not isinstance(payload, dict):
            return None
        return SubtitleSourceVoiceDto.model_validate(payload)

    def _build_diff_summary(
        self,
        original_segments: list[SubtitleSegmentDto],
        updated_segments: list[SubtitleSegmentDto],
    ) -> SubtitleAlignmentDiffSummaryDto:
        original_by_index = {segment.segmentIndex: segment for segment in original_segments}
        updated_by_index = {segment.segmentIndex: segment for segment in updated_segments}
        shared_indexes = set(original_by_index) & set(updated_by_index)
        timing_changed_segments = 0
        text_changed_segments = 0
        for segment_index in shared_indexes:
            before = original_by_index[segment_index]
            after = updated_by_index[segment_index]
            if before.startMs != after.startMs or before.endMs != after.endMs:
                timing_changed_segments += 1
            if before.text != after.text:
                text_changed_segments += 1
        return SubtitleAlignmentDiffSummaryDto(
            segmentCountChanged=len(original_segments) != len(updated_segments),
            timingChangedSegments=timing_changed_segments,
            textChangedSegments=text_changed_segments,
            lockedSegments=sum(1 for segment in updated_segments if segment.locked),
        )

    def _segments_have_valid_timecodes(self, segments: list[SubtitleSegmentDto]) -> bool:
        return all(
            segment.startMs is not None
            and segment.endMs is not None
            and segment.startMs >= 0
            and segment.endMs > segment.startMs
            for segment in segments
        )

    def _validate_segments_have_timecodes(self, segments: list[SubtitleSegmentDto]) -> None:
        for segment in segments:
            self._ensure_valid_timecode_pair(segment.startMs, segment.endMs)

    def _ensure_valid_timecode_pair(
        self,
        start_ms: int | None,
        end_ms: int | None,
    ) -> None:
        if start_ms is None or end_ms is None:
            raise HTTPException(status_code=400, detail=MISSING_TIMECODE_MESSAGE)
        if start_ms < 0 or end_ms <= start_ms:
            raise HTTPException(status_code=400, detail=INVALID_TIMECODE_MESSAGE)

    def _ensure_timecode_value(self, milliseconds: int | None) -> int:
        if milliseconds is None:
            raise HTTPException(status_code=400, detail=MISSING_TIMECODE_MESSAGE)
        if milliseconds < 0:
            raise HTTPException(status_code=400, detail=INVALID_TIMECODE_MESSAGE)
        return milliseconds

    def _string_or_none(self, value: object, *, fallback: str | None = None) -> str | None:
        if value is None:
            return fallback
        text_value = str(value).strip()
        if text_value == "":
            return fallback
        return text_value

    def _to_dto(self, track: SubtitleTrack) -> SubtitleTrackDto:
        metadata = self._decode_metadata(track.metadata_json)
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
            updatedAt=track.updated_at or track.created_at,
            sourceVoice=self._decode_source_voice(metadata),
            alignment=self._decode_alignment(metadata, track=track),
        )

    def _decode_style(self, style_json: str) -> SubtitleStyleDto:
        try:
            raw_style = json.loads(style_json)
        except json.JSONDecodeError as exc:
            log.exception("\u89e3\u6790\u5b57\u5e55\u6837\u5f0f\u5931\u8d25")
            raise HTTPException(status_code=500, detail="\u89e3\u6790\u5b57\u5e55\u6837\u5f0f\u5931\u8d25\u3002") from exc
        return SubtitleStyleDto.model_validate(raw_style)

    def _decode_segments(self, segments_json: str) -> list[SubtitleSegmentDto]:
        try:
            raw_segments = json.loads(segments_json)
        except json.JSONDecodeError as exc:
            log.exception("\u89e3\u6790\u5b57\u5e55\u7247\u6bb5\u5931\u8d25")
            raise HTTPException(status_code=500, detail="\u89e3\u6790\u5b57\u5e55\u7247\u6bb5\u5931\u8d25\u3002") from exc
        return [SubtitleSegmentDto.model_validate(item) for item in raw_segments]
