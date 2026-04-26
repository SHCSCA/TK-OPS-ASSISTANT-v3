from __future__ import annotations

import json
import logging
from typing import Any

from repositories.video_deconstruction_repository import StoredVideoDeconstructionArtifact
from schemas.video_deconstruction import (
    VideoContentStructureDto,
    VideoKeyframeDto,
    VideoResultSourceDto,
    VideoScriptLineDto,
    VideoScriptResultDto,
    VideoSegmentDto,
    VideoStructureExtractionDto,
    VideoTranscriptDto,
)

log = logging.getLogger(__name__)

VIDEO_DECONSTRUCTION_PROMPT_VERSION = "video_deconstruction_result_v1"


def build_standard_video_result(
    video,
    *,
    transcript: VideoTranscriptDto,
    segments: list[VideoSegmentDto],
    structure: VideoStructureExtractionDto,
    artifact: StoredVideoDeconstructionArtifact | None,
) -> tuple[VideoScriptResultDto, list[VideoKeyframeDto], VideoContentStructureDto, VideoResultSourceDto]:
    payload = _load_payload(artifact)
    summary = _summary_from_payload(payload, structure)
    keyframes = _build_keyframes(payload, segments)
    script = _build_script(video, transcript, payload, summary, keyframes)
    content_structure = _build_content_structure(script, payload, summary, keyframes)
    source = VideoResultSourceDto(
        provider=artifact.provider if artifact is not None and artifact.provider else "local",
        model=artifact.model if artifact is not None and artifact.model else "fallback",
        promptVersion=VIDEO_DECONSTRUCTION_PROMPT_VERSION,
    )
    return script, keyframes, content_structure, source


def _build_script(
    video,
    transcript: VideoTranscriptDto,
    payload: dict[str, Any],
    summary: dict[str, Any],
    keyframes: list[VideoKeyframeDto],
) -> VideoScriptResultDto:
    raw_script = _as_dict(payload.get("script"))
    lines = _script_lines_from_payload(raw_script)
    if not lines:
        lines = [
            VideoScriptLineDto(
                startMs=item.startMs,
                endMs=item.endMs,
                text=item.speech or item.onscreenText,
                type="speech",
            )
            for item in keyframes
            if item.speech or item.onscreenText
        ]
    full_text = _text(raw_script.get("fullText")) or "\n".join(item.text for item in lines if item.text)
    if not full_text and transcript.text:
        full_text = transcript.text
    title = _text(raw_script.get("title")) or _text(summary.get("topic")) or _text(summary.get("title"))
    language = _text(raw_script.get("language")) or transcript.language or _text(summary.get("language"))
    return VideoScriptResultDto(
        title=title,
        language=language or "",
        fullText=full_text,
        lines=lines,
    )


def _build_keyframes(payload: dict[str, Any], segments: list[VideoSegmentDto]) -> list[VideoKeyframeDto]:
    raw_keyframes = _as_list(payload.get("keyframes"))
    if raw_keyframes:
        keyframes = [
            _keyframe_from_mapping(item, index)
            for index, item in enumerate(raw_keyframes, start=1)
            if isinstance(item, dict)
        ]
        return [item for item in keyframes if _is_meaningful_keyframe(item)]
    keyframes = [_keyframe_from_segment(item) for item in segments]
    return [item for item in keyframes if _is_meaningful_keyframe(item)]


def _build_content_structure(
    script: VideoScriptResultDto,
    payload: dict[str, Any],
    summary: dict[str, Any],
    keyframes: list[VideoKeyframeDto],
) -> VideoContentStructureDto:
    raw_structure = _as_dict(payload.get("contentStructure"))
    visuals = [item.visual for item in keyframes if item.visual]
    speeches = [item.speech for item in keyframes if item.speech]
    intents = [item.intent for item in keyframes if item.intent]
    return VideoContentStructureDto(
        topic=_text(raw_structure.get("topic")) or _text(summary.get("topic")) or script.title,
        hook=_text(raw_structure.get("hook")) or _text(summary.get("hook")) or (intents[0] if intents else ""),
        painPoints=_string_list(raw_structure.get("painPoints") or summary.get("painPoints")),
        sellingPoints=_string_list(raw_structure.get("sellingPoints") or summary.get("sellingPoints")),
        rhythm=_string_list(raw_structure.get("rhythm") or summary.get("rhythm") or intents),
        cta=_text(raw_structure.get("cta")) or _text(summary.get("cta")),
        reusableForScript=_string_list(raw_structure.get("reusableForScript") or speeches),
        reusableForStoryboard=_string_list(raw_structure.get("reusableForStoryboard") or visuals),
        risks=_string_list(raw_structure.get("risks") or summary.get("risks")),
    )


def _script_lines_from_payload(raw_script: dict[str, Any]) -> list[VideoScriptLineDto]:
    lines = []
    for index, item in enumerate(_as_list(raw_script.get("lines")), start=1):
        if not isinstance(item, dict):
            continue
        start_ms = _int(item.get("startMs"), default=(index - 1) * 3000)
        end_ms = _int(item.get("endMs"), default=start_ms + 3000)
        text = _text(item.get("text"))
        if not text:
            continue
        lines.append(
            VideoScriptLineDto(
                startMs=start_ms,
                endMs=max(end_ms, start_ms + 1),
                text=text,
                type=_text(item.get("type")) or "speech",
            )
        )
    return lines


def _keyframe_from_mapping(item: dict[str, Any], index: int) -> VideoKeyframeDto:
    start_ms = _int(item.get("startMs"), default=(index - 1) * 3000)
    end_ms = _int(item.get("endMs"), default=start_ms + 3000)
    keyframe = VideoKeyframeDto(
        index=_int(item.get("index"), default=index),
        startMs=start_ms,
        endMs=max(end_ms, start_ms + 1),
        visual=_text(item.get("visual")),
        speech=_text(item.get("speech")),
        onscreenText=_text(item.get("onscreenText")),
        shotType=_text(item.get("shotType")),
        camera=_text(item.get("camera") or item.get("cameraAngle")),
        intent=_text(item.get("intent")),
    )
    return keyframe if _is_meaningful_keyframe(keyframe) else _empty_keyframe(index, start_ms, end_ms)


def _keyframe_from_segment(segment: VideoSegmentDto) -> VideoKeyframeDto:
    metadata = _json_dict(segment.metadataJson)
    return VideoKeyframeDto(
        index=segment.segmentIndex,
        startMs=segment.startMs,
        endMs=segment.endMs,
        visual=_text(metadata.get("visual")),
        speech=segment.transcriptText or _text(metadata.get("speech")),
        onscreenText=_text(metadata.get("onscreenText")),
        shotType=_text(metadata.get("shotType")),
        camera=_text(metadata.get("camera") or metadata.get("cameraAngle")),
        intent=segment.label or _text(metadata.get("intent")),
    )


def _is_meaningful_keyframe(item: VideoKeyframeDto) -> bool:
    return bool(item.visual or item.speech or item.onscreenText)


def _empty_keyframe(index: int, start_ms: int, end_ms: int) -> VideoKeyframeDto:
    return VideoKeyframeDto(
        index=index,
        startMs=start_ms,
        endMs=end_ms,
        visual="",
        speech="",
        onscreenText="",
        shotType="",
        camera="",
        intent="",
    )


def _summary_from_payload(payload: dict[str, Any], structure: VideoStructureExtractionDto) -> dict[str, Any]:
    summary = _as_dict(payload.get("summary"))
    if summary:
        return summary
    if not structure.scriptJson:
        return {}
    return _as_dict(_json_dict(structure.scriptJson).get("summary"))


def _load_payload(artifact: StoredVideoDeconstructionArtifact | None) -> dict[str, Any]:
    if artifact is None:
        return {}
    return _json_dict(artifact.payload_json)


def _json_dict(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        log.warning("视频拆解标准结果 JSON 解析失败")
        return {}
    return payload if isinstance(payload, dict) else {}


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = _text(value)
    return [text] if text else []


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _int(value: Any, *, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
