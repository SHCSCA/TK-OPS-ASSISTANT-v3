from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from uuid import uuid4

from fastapi import HTTPException

from common.time import utc_now_iso
from domain.models import SubtitleTrack
from repositories.subtitle_repository import SubtitleRepository
from schemas.subtitles import (
    SubtitleExportDto,
    SubtitleExportInput,
    SubtitleSegmentDto,
    SubtitleStyleDto,
    SubtitleStyleTemplateDto,
    SubtitleTrackAlignInput,
    SubtitleTrackDto,
    SubtitleTrackGenerateInput,
    SubtitleTrackGenerateResultDto,
    SubtitleTrackUpdateInput,
)

log = logging.getLogger(__name__)

ALIGN_MESSAGE = "字幕时间码已更新。"
EXPORT_MESSAGE = "字幕导出完成。"


@dataclass(frozen=True)
class _BuiltinSubtitleStyleTemplate:
    id: str
    name: str
    description: str
    style: SubtitleStyleDto


class SubtitleService:
    def __init__(self, repository: SubtitleRepository) -> None:
        self._repository = repository

    def list_tracks(self, project_id: str) -> list[SubtitleTrackDto]:
        try:
            tracks = self._repository.list_tracks(project_id)
        except Exception as exc:
            log.exception("查询字幕轨道列表失败")
            raise HTTPException(status_code=500, detail="查询字幕轨道列表失败") from exc
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
                detail="字幕源文本不能为空，请先在脚本或选题中心提供内容。",
            )

        style = self._resolve_style(payload.stylePreset)
        generated_at = utc_now_iso()
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
            status="ready",
            created_at=generated_at,
        )

        try:
            saved = self._repository.create_track(track)
        except Exception as exc:
            log.exception("创建字幕轨道失败")
            raise HTTPException(status_code=500, detail="创建字幕轨道失败") from exc

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
            },
            message="字幕轨道已基于本地文本规则生成。",
        )

    def align_track(
        self,
        track_id: str,
        payload: SubtitleTrackAlignInput,
    ) -> SubtitleTrackDto:
        track = self._get_track(track_id)
        style = self._decode_style(track.style_json)
        segments_json = json.dumps(
            [segment.model_dump(mode="json") for segment in payload.segments],
            ensure_ascii=False,
        )
        try:
            saved = self._repository.update_track(
                track_id,
                segments_json=segments_json,
                style_json=json.dumps(style.model_dump(mode="json"), ensure_ascii=False),
                status="ready",
            )
        except Exception as exc:
            log.exception("保存字幕对齐结果失败")
            raise HTTPException(status_code=500, detail="保存字幕对齐结果失败") from exc
        if saved is None:
            raise HTTPException(status_code=404, detail="字幕轨道不存在。")
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
        for segment in segments:
            if segment.startMs is None or segment.endMs is None:
                raise HTTPException(status_code=400, detail="字幕片段缺少时间码，无法导出。")

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
            log.exception("保存字幕校正结果失败")
            raise HTTPException(status_code=500, detail="保存字幕校正结果失败") from exc
        if track is None:
            raise HTTPException(status_code=404, detail="字幕轨道不存在。")
        return self._to_dto(track)

    def delete_track(self, track_id: str) -> None:
        try:
            deleted = self._repository.delete_track(track_id)
        except Exception as exc:
            log.exception("删除字幕轨道失败")
            raise HTTPException(status_code=500, detail="删除字幕轨道失败") from exc
        if not deleted:
            raise HTTPException(status_code=404, detail="字幕轨道不存在。")

    def _builtin_style_templates(self) -> list[_BuiltinSubtitleStyleTemplate]:
        return [
            _BuiltinSubtitleStyleTemplate(
                id="creator-default",
                name="创作者默认",
                description="适合大多数竖屏创作视频的基础样式。",
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
                name="高对比简洁",
                description="更适合复杂背景的视频字幕。",
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
                name="居中强调",
                description="适合节奏化口播或重点强调片段。",
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
        if milliseconds is None:
            raise HTTPException(status_code=400, detail="字幕片段缺少时间码，无法导出。")
        total_seconds, ms = divmod(milliseconds, 1000)
        minutes, seconds = divmod(total_seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{ms:03d}"

    def _format_vtt_time(self, milliseconds: int | None) -> str:
        if milliseconds is None:
            raise HTTPException(status_code=400, detail="字幕片段缺少时间码，无法导出。")
        total_seconds, ms = divmod(milliseconds, 1000)
        minutes, seconds = divmod(total_seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{ms:03d}"

    def _format_ass_time(self, milliseconds: int | None) -> str:
        if milliseconds is None:
            raise HTTPException(status_code=400, detail="字幕片段缺少时间码，无法导出。")
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
            parts = [part.strip() for part in re.split(r"(?<=[。！？!?；;])\s*", line) if part.strip()]
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
            log.exception("查询字幕轨道详情失败")
            raise HTTPException(status_code=500, detail="查询字幕轨道详情失败") from exc
        if track is None:
            raise HTTPException(status_code=404, detail="字幕轨道不存在。")
        return track

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
            log.exception("解析字幕片段失败")
            raise HTTPException(status_code=500, detail="解析字幕片段失败")
        return [SubtitleSegmentDto.model_validate(item) for item in raw_segments]
