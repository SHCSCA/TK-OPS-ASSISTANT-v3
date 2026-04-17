from __future__ import annotations

import json
import logging
from uuid import uuid4

from fastapi import HTTPException

from common.time import utc_now
from domain.models.base import generate_uuid
from domain.models.video_deconstruction import (
    VideoSegment,
    VideoStructureExtraction,
    VideoTranscript,
)
from repositories.imported_video_repository import ImportedVideoRepository
from repositories.script_repository import ScriptRepository
from repositories.video_deconstruction_repository import VideoDeconstructionRepository
from schemas.video_deconstruction import (
    ApplyVideoExtractionResultDto,
    VideoSegmentDto,
    VideoStructureExtractionDto,
    VideoTranscriptDto,
)
from services.dashboard_service import DashboardService

log = logging.getLogger(__name__)


class VideoDeconstructionService:
    def __init__(
        self,
        *,
        imported_video_repository: ImportedVideoRepository,
        repository: VideoDeconstructionRepository,
        dashboard_service: DashboardService,
        script_repository: ScriptRepository,
    ) -> None:
        self._imported_video_repository = imported_video_repository
        self._repository = repository
        self._dashboard_service = dashboard_service
        self._script_repository = script_repository

    def start_transcription(self, video_id: str) -> VideoTranscriptDto:
        self._require_video(video_id)
        transcript = VideoTranscript(
            id=generate_uuid(),
            imported_video_id=video_id,
            language="zh-CN",
            text=None,
            status="pending_provider",
        )
        try:
            saved = self._repository.save_transcript(transcript)
        except Exception as exc:
            log.exception("创建视频转写记录失败")
            raise HTTPException(status_code=500, detail="创建视频转写记录失败") from exc
        return self._to_transcript_dto(saved)

    def get_transcript(self, video_id: str) -> VideoTranscriptDto:
        self._require_video(video_id)
        try:
            transcript = self._repository.get_transcript(video_id)
        except Exception as exc:
            log.exception("查询视频转写结果失败")
            raise HTTPException(status_code=500, detail="查询视频转写结果失败") from exc
        if transcript is None:
            raise HTTPException(status_code=404, detail="视频转写结果不存在")
        return self._to_transcript_dto(transcript)

    def run_segmentation(self, video_id: str) -> list[VideoSegmentDto]:
        video = self._require_video(video_id)
        total_ms = max(int((video.duration_seconds or 30) * 1000), 1_000)
        size_ms = 30_000
        segment_count = max(1, (total_ms + size_ms - 1) // size_ms)
        segments: list[VideoSegment] = []
        for index in range(segment_count):
            start_ms = index * size_ms
            end_ms = min(total_ms, start_ms + size_ms)
            segments.append(
                VideoSegment(
                    id=str(uuid4()),
                    imported_video_id=video_id,
                    segment_index=index,
                    start_ms=start_ms,
                    end_ms=end_ms,
                    label=_segment_label(index),
                    transcript_text=None,
                    metadata_json=None,
                )
            )
        try:
            saved = self._repository.replace_segments(video_id, segments)
        except Exception as exc:
            log.exception("生成视频切段失败")
            raise HTTPException(status_code=500, detail="生成视频切段失败") from exc
        return [self._to_segment_dto(item) for item in saved]

    def list_segments(self, video_id: str) -> list[VideoSegmentDto]:
        self._require_video(video_id)
        try:
            segments = self._repository.list_segments(video_id)
        except Exception as exc:
            log.exception("查询视频切段失败")
            raise HTTPException(status_code=500, detail="查询视频切段失败") from exc
        return [self._to_segment_dto(item) for item in segments]

    def extract_structure(self, video_id: str) -> VideoStructureExtractionDto:
        self._require_video(video_id)
        try:
            transcript = self._repository.get_transcript(video_id)
            segments = self._repository.list_segments(video_id)
        except Exception as exc:
            log.exception("查询视频拆解依赖数据失败")
            raise HTTPException(status_code=500, detail="查询视频拆解依赖数据失败") from exc
        if not segments:
            self.run_segmentation(video_id)
            segments = self._repository.list_segments(video_id)

        if transcript is None or not transcript.text:
            structure = VideoStructureExtraction(
                id=generate_uuid(),
                imported_video_id=video_id,
                status="pending_provider",
                script_json=None,
                storyboard_json=json.dumps(
                    [
                        {
                            "sceneId": item.id,
                            "title": item.label or f"segment-{item.segment_index}",
                            "summary": f"{item.start_ms}-{item.end_ms}",
                        }
                        for item in segments
                    ],
                    ensure_ascii=False,
                ),
            )
        else:
            structure = VideoStructureExtraction(
                id=generate_uuid(),
                imported_video_id=video_id,
                status="ready",
                script_json=json.dumps(
                    {
                        "title": "视频拆解脚本草稿",
                        "sections": [
                            {
                                "label": item.label or f"segment-{item.segment_index}",
                                "startMs": item.start_ms,
                                "endMs": item.end_ms,
                                "text": transcript.text,
                            }
                            for item in segments
                        ],
                    },
                    ensure_ascii=False,
                ),
                storyboard_json=json.dumps(
                    [
                        {
                            "sceneId": item.id,
                            "title": item.label or f"segment-{item.segment_index}",
                            "summary": transcript.text,
                        }
                        for item in segments
                    ],
                    ensure_ascii=False,
                ),
            )
        try:
            saved = self._repository.save_structure(structure)
        except Exception as exc:
            log.exception("生成视频结构提取失败")
            raise HTTPException(status_code=500, detail="生成视频结构提取失败") from exc
        return self._to_structure_dto(saved)

    def get_structure(self, video_id: str) -> VideoStructureExtractionDto:
        self._require_video(video_id)
        try:
            structure = self._repository.get_structure_by_video(video_id)
        except Exception as exc:
            log.exception("查询视频结构提取失败")
            raise HTTPException(status_code=500, detail="查询视频结构提取失败") from exc
        if structure is None:
            raise HTTPException(status_code=404, detail="视频结构提取结果不存在")
        return self._to_structure_dto(structure)

    def apply_to_project(self, extraction_id: str) -> ApplyVideoExtractionResultDto:
        try:
            extraction = self._repository.get_structure(extraction_id)
        except Exception as exc:
            log.exception("查询视频结构提取详情失败")
            raise HTTPException(status_code=500, detail="查询视频结构提取详情失败") from exc
        if extraction is None:
            raise HTTPException(status_code=404, detail="视频结构提取结果不存在")
        if extraction.status != "ready" or not extraction.script_json:
            raise HTTPException(status_code=409, detail="请先完成转写和结构提取，再回流到项目。")

        video = self._require_video(extraction.imported_video_id)
        self._dashboard_service.require_project(video.project_id)
        script_content = _structure_json_to_script(extraction.script_json)
        stored = self._script_repository.save_version(
            video.project_id,
            source="video_extraction",
            content=script_content,
        )
        self._dashboard_service.update_project_versions(
            video.project_id,
            current_script_version=stored.revision,
        )
        return ApplyVideoExtractionResultDto(
            projectId=video.project_id,
            extractionId=extraction_id,
            scriptRevision=stored.revision,
            status="applied",
            message="视频拆解结果已回流到脚本。",
        )

    def _require_video(self, video_id: str):
        video = self._imported_video_repository.get(video_id)
        if video is None:
            raise HTTPException(status_code=404, detail="视频记录不存在")
        return video

    def _to_transcript_dto(self, transcript: VideoTranscript) -> VideoTranscriptDto:
        return VideoTranscriptDto(
            id=transcript.id,
            videoId=transcript.imported_video_id,
            language=transcript.language,
            text=transcript.text,
            status=transcript.status,
            createdAt=transcript.created_at,
            updatedAt=transcript.updated_at,
        )

    def _to_segment_dto(self, segment: VideoSegment) -> VideoSegmentDto:
        return VideoSegmentDto(
            id=segment.id,
            videoId=segment.imported_video_id,
            segmentIndex=segment.segment_index,
            startMs=segment.start_ms,
            endMs=segment.end_ms,
            label=segment.label,
            transcriptText=segment.transcript_text,
            metadataJson=segment.metadata_json,
            createdAt=segment.created_at,
        )

    def _to_structure_dto(
        self,
        structure: VideoStructureExtraction,
    ) -> VideoStructureExtractionDto:
        return VideoStructureExtractionDto(
            id=structure.id,
            videoId=structure.imported_video_id,
            status=structure.status,
            scriptJson=structure.script_json,
            storyboardJson=structure.storyboard_json,
            createdAt=structure.created_at,
            updatedAt=structure.updated_at,
        )


def _segment_label(index: int) -> str:
    if index == 0:
        return "intro"
    if index == 1:
        return "main"
    if index == 2:
        return "cta"
    return "outro"


def _structure_json_to_script(script_json: str) -> str:
    try:
        payload = json.loads(script_json)
    except json.JSONDecodeError:
        return script_json
    title = payload.get("title", "视频拆解脚本")
    sections = payload.get("sections", [])
    lines = [str(title)]
    for item in sections:
        if not isinstance(item, dict):
            continue
        label = item.get("label", "segment")
        text = item.get("text", "")
        lines.append(f"\n## {label}\n{text}")
    return "\n".join(lines).strip()
