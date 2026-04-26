from __future__ import annotations

import base64
import json
import logging
import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ai.providers.base import TextGenerationMediaInput
from ai.providers.errors import ProviderHTTPException
from services.ai_text_generation_service import AITextGenerationService
from services.video_deconstruction_prompt import build_video_deconstruction_request_prompt

log = logging.getLogger(__name__)

_MAX_INLINE_VIDEO_BYTES = 50 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class MultimodalVideoAnalysisResult:
    payload: dict[str, Any]
    provider: str
    model: str


class VideoMultimodalAnalysisService:
    def __init__(self, *, ai_text_generation_service: AITextGenerationService) -> None:
        self._ai_text_generation_service = ai_text_generation_service

    def analyze_video(self, video) -> MultimodalVideoAnalysisResult | None:
        video_path = Path(video.file_path)
        media_input = self._build_video_media_input(video_path)
        if media_input is None:
            return None

        prompt = build_video_deconstruction_request_prompt(video)
        for capability_id in ("video_transcription", "asset_analysis"):
            try:
                result = self._ai_text_generation_service.generate_text(
                    capability_id,
                    {"assets": prompt, "media_file": prompt},
                    project_id=video.project_id,
                    media_inputs=(media_input,),
                )
            except ProviderHTTPException as exc:
                log.warning(
                    "多模态视频拆解能力不可用 video_id=%s capability=%s code=%s detail=%s",
                    video.id,
                    capability_id,
                    exc.error_code,
                    exc.detail,
                )
                continue
            except Exception as exc:  # pragma: no cover - 防御性兜底
                log.exception("多模态视频拆解失败 video_id=%s capability=%s", video.id, capability_id)
                continue

            payload = _parse_multimodal_payload(result.text)
            if payload is None:
                log.warning(
                    "多模态视频拆解返回无法解析 video_id=%s capability=%s model=%s",
                    video.id,
                    capability_id,
                    result.model,
                )
                continue

            return MultimodalVideoAnalysisResult(
                payload=payload,
                provider=result.provider,
                model=result.model,
            )
        return None

    def _build_video_media_input(self, video_path: Path) -> TextGenerationMediaInput | None:
        try:
            file_size = video_path.stat().st_size
        except OSError as exc:
            log.exception("读取视频文件信息失败 path=%s", video_path)
            return None

        if file_size <= 0:
            log.warning("视频文件为空，跳过多模态拆解 path=%s", video_path)
            return None
        if file_size > _MAX_INLINE_VIDEO_BYTES:
            log.warning("视频文件超过内联上限，跳过多模态拆解 path=%s size=%s", video_path, file_size)
            return None

        try:
            raw = video_path.read_bytes()
        except OSError as exc:
            log.exception("读取视频文件失败 path=%s", video_path)
            return None

        mime_type = mimetypes.guess_type(video_path.name)[0] or "video/mp4"
        encoded = base64.b64encode(raw).decode("ascii")
        return TextGenerationMediaInput(
            kind="video",
            url=f"data:{mime_type};base64,{encoded}",
            mime_type=mime_type,
            fps=1.0,
            filename=video_path.name,
        )


def _parse_multimodal_payload(text: str) -> dict[str, Any] | None:
    cleaned = _strip_json_fence(text)
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError:
        return None

    if not isinstance(payload, dict):
        return None
    segments = payload.get("segments")
    if not isinstance(segments, list) or not segments:
        segments = payload.get("keyframes")
    if not isinstance(segments, list) or not segments:
        return None
    normalized_segments = []
    for index, item in enumerate(segments, start=1):
        if not isinstance(item, dict):
            continue
        normalized = _normalize_segment(item, index)
        if normalized is not None:
            normalized_segments.append(normalized)
    if not normalized_segments:
        return None
    payload["segments"] = normalized_segments
    if not isinstance(payload.get("summary"), dict):
        payload["summary"] = {}
    return payload


def _normalize_segment(item: dict[str, Any], index: int) -> dict[str, Any] | None:
    start_ms = _to_int(item.get("startMs"), default=(index - 1) * 3000)
    end_ms = _to_int(item.get("endMs"), default=start_ms + 3000)
    if end_ms <= start_ms:
        end_ms = start_ms + 3000
    return {
        "startMs": start_ms,
        "endMs": end_ms,
        "visual": str(item.get("visual") or item.get("画面内容") or "").strip(),
        "speech": str(item.get("speech") or item.get("口播") or item.get("语音") or "").strip(),
        "onscreenText": str(item.get("onscreenText") or item.get("屏幕字幕") or "").strip(),
        "shotType": str(item.get("shotType") or item.get("景别") or "").strip(),
        "intent": str(item.get("intent") or item.get("阶段") or item.get("目的") or f"片段 {index}").strip(),
    }


def _to_int(value: Any, *, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _strip_json_fence(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return cleaned
