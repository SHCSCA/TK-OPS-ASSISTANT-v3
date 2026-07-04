from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.workspace_service import WorkspaceService

log = logging.getLogger(__name__)

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*\n?(.*?)\n?```", re.DOTALL)

MIN_CLIP_DURATION_MS = 500
MAX_CLIP_DURATION_MS = 600_000


def serialize_timeline_context(timeline: object) -> str:
    """从 Timeline ORM 对象提取轨道上下文，序列化为 AI 友好摘要。"""
    tracks_json: str = getattr(timeline, "tracks_json", "[]")
    return serialize_timeline_for_ai(tracks_json)


def serialize_timeline_for_ai(tracks_json: str) -> str:
    """将 tracks_json 转换为 AI 友好的紧凑摘要 JSON 字符串。"""
    try:
        tracks = json.loads(tracks_json)
    except (TypeError, ValueError) as exc:
        log.exception("序列化时间线轨道 JSON 失败")
        raise ValueError("时间线轨道数据格式无效。") from exc

    if not isinstance(tracks, list):
        raise ValueError("时间线轨道数据格式无效。")

    summary: list[dict[str, object]] = []
    for track in tracks:
        if not isinstance(track, dict):
            continue
        clips = track.get("clips")
        if not isinstance(clips, list):
            clips = []
        clip_summaries: list[dict[str, object]] = []
        for clip in clips:
            if not isinstance(clip, dict):
                continue
            clip_summaries.append({
                "id": str(clip.get("id", "")),
                "trackId": str(clip.get("trackId", "")),
                "label": str(clip.get("label", "")),
                "startMs": int(clip.get("startMs") or 0),
                "durationMs": int(clip.get("durationMs") or 0),
                "sourceType": str(clip.get("sourceType", "")),
            })
        summary.append({
            "trackId": str(track.get("id", "")),
            "kind": str(track.get("kind", "")),
            "name": str(track.get("name", "")),
            "clipCount": len(clip_summaries),
            "clips": clip_summaries,
        })

    return json.dumps(summary, ensure_ascii=False)


def parse_magic_cut_operations(ai_response_text: str) -> tuple[list[dict[str, object]], str]:
    """从 AI 响应中解析剪辑操作列表与摘要。

    返回 (operations, summary)。解析失败时返回空列表与错误摘要，不抛异常。
    """
    ai_text = ai_response_text.strip()
    if not ai_text:
        return [], "AI 未返回任何内容。"

    json_text = _extract_json(ai_text)
    try:
        result = json.loads(json_text)
    except json.JSONDecodeError as exc:
        log.warning("解析 AI 魔术剪辑 JSON 失败: %s", exc)
        return [], "AI 返回的内容格式不正确，无法解析剪辑操作。"

    if not isinstance(result, dict):
        return [], "AI 返回的 JSON 结构不正确。"

    summary = str(result.get("summary") or "智能粗剪已完成。")
    raw_operations = result.get("operations")
    if not isinstance(raw_operations, list):
        return [], summary

    valid_actions = {"delete", "trim", "move", "split"}
    parsed: list[dict[str, object]] = []
    for op in raw_operations:
        if not isinstance(op, dict):
            continue
        action = str(op.get("action") or "").strip().lower()
        if action not in valid_actions:
            log.warning("魔术剪辑忽略未知操作类型: %s", action)
            continue

        clip_id = str(op.get("clipId") or "").strip()
        if not clip_id:
            log.warning("魔术剪辑操作缺少 clipId，已跳过: %s", op)
            continue

        normalized: dict[str, object] = {"action": action, "clipId": clip_id}
        if action in ("trim", "move"):
            start_ms = _coerce_int(op.get("startMs"), default=0, min_val=0)
            duration_ms = _coerce_int(op.get("durationMs"), default=MIN_CLIP_DURATION_MS, min_val=MIN_CLIP_DURATION_MS, max_val=MAX_CLIP_DURATION_MS)
            normalized["startMs"] = start_ms
            normalized["durationMs"] = duration_ms
            if action == "move":
                target_track_id = str(op.get("targetTrackId") or "").strip()
                if not target_track_id:
                    log.warning("魔术剪辑 move 操作缺少 targetTrackId，已跳过: %s", op)
                    continue
                normalized["targetTrackId"] = target_track_id
        elif action == "split":
            split_at_ms = _coerce_int(op.get("splitAtMs"), default=0, min_val=1)
            if split_at_ms < 1:
                log.warning("魔术剪辑 split 操作 splitAtMs 无效，已跳过: %s", op)
                continue
            normalized["splitAtMs"] = split_at_ms
        parsed.append(normalized)

    if not parsed:
        return [], summary

    return parsed, summary


def apply_magic_cut_operations(
    workspace_service: WorkspaceService,
    timeline_id: str,
    operations: list[dict[str, object]],
) -> tuple[int, int, str]:
    """将解析后的操作应用到时间线。

    返回 (成功数, 失败数, 结果消息)。
    """
    applied = 0
    failed = 0
    messages: list[str] = []

    for op in operations:
        action = str(op.get("action") or "")
        clip_id = str(op.get("clipId") or "")
        try:
            if action == "delete":
                workspace_service.delete_clip(clip_id, timeline_id=timeline_id)
                applied += 1
                messages.append(f"已删除片段 {clip_id}")
            elif action == "trim":
                start_ms = int(op.get("startMs") or 0)
                duration_ms = int(op.get("durationMs") or MIN_CLIP_DURATION_MS)
                workspace_service.trim_clip(
                    clip_id,
                    {"startMs": start_ms, "durationMs": duration_ms},
                    timeline_id=timeline_id,
                )
                applied += 1
                messages.append(f"已裁剪片段 {clip_id}")
            elif action == "move":
                start_ms = int(op.get("startMs") or 0)
                target_track_id = str(op.get("targetTrackId") or "")
                workspace_service.move_clip(
                    clip_id,
                    {"startMs": start_ms, "targetTrackId": target_track_id},
                    timeline_id=timeline_id,
                )
                applied += 1
                messages.append(f"已移动片段 {clip_id}")
            elif action == "split":
                split_at_ms = int(op.get("splitAtMs") or 0)
                workspace_service.split_clip(clip_id, {"splitAtMs": split_at_ms}, timeline_id=timeline_id)
                applied += 1
                messages.append(f"已分割片段 {clip_id}")
            else:
                failed += 1
                messages.append(f"未知操作 {action}，跳过片段 {clip_id}")
        except Exception as exc:
            failed += 1
            log.warning("魔术剪辑操作失败 clip_id=%s action=%s: %s", clip_id, action, exc)
            messages.append(f"操作 {action} 失败（片段 {clip_id}）：{exc}")

    result_message = f"已应用 {applied} 个剪辑操作"
    if failed > 0:
        result_message += f"，{failed} 个操作失败"
    if messages:
        result_message += "。" + "；".join(messages[-5:])
    return applied, failed, result_message


def _extract_json(text: str) -> str:
    """从文本中提取 JSON，处理可能的 Markdown 代码块围栏。"""
    match = _JSON_FENCE_RE.search(text)
    if match:
        return match.group(1).strip()
    return text


def _coerce_int(
    value: object,
    *,
    default: int,
    min_val: int = 0,
    max_val: int | None = None,
) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        result = value
    elif isinstance(value, float):
        result = int(value)
    elif isinstance(value, str) and value.strip().lstrip("-").isdigit():
        result = int(value.strip())
    else:
        return default
    result = max(min_val, result)
    if max_val is not None:
        result = min(max_val, result)
    return result
