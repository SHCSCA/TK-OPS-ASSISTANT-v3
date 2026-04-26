from __future__ import annotations

import json
import logging
import re
from typing import Any

from fastapi import HTTPException

log = logging.getLogger(__name__)

JsonObject = dict[str, Any]


def parse_script_document_json(raw_text: str) -> JsonObject:
    payload = _extract_json_object(raw_text, error_detail='脚本 Provider 未返回有效 JSON。')
    document = _unwrap_script_document(payload)
    _require_json_object(document, '脚本 JSON 根节点必须是对象。')
    segments = document.get('segments')
    if not isinstance(segments, list) or not segments:
        log.warning('脚本 JSON 缺少 segments 字段 raw=%s', raw_text[:500])
        raise HTTPException(status_code=502, detail='脚本 Provider 返回 JSON 但缺少有效分段脚本。')
    document.setdefault('schemaVersion', 'script_document_v1')
    return document


def build_script_display_text(document: JsonObject) -> str:
    title = _as_text(document.get('title')) or 'TikTok 短视频脚本'
    lines = [title]

    for segment in _as_list(document.get('segments')):
        if not isinstance(segment, dict):
            continue
        segment_id = _as_text(segment.get('segmentId')) or _as_text(segment.get('id')) or 'S'
        time = _as_text(segment.get('time'))
        voiceover = _as_text(segment.get('voiceover') or segment.get('spokenText') or segment.get('口播文案'))
        subtitle = _as_text(segment.get('subtitle') or segment.get('screenText') or segment.get('屏幕字幕'))
        body = voiceover or subtitle or _as_text(segment.get('goal'))
        prefix = f"{segment_id} {time}".strip()
        if body:
            lines.append(f"{prefix} {body}".strip())

    voiceover_full = _as_text(document.get('voiceoverFull') or document.get('fullVoiceover'))
    if voiceover_full:
        lines.append(voiceover_full)
    return '\n'.join(_dedupe_lines(lines)).strip()


def parse_storyboard_document_json(raw_text: str) -> JsonObject:
    payload = _extract_json_object(raw_text, error_detail='分镜 Provider 未返回有效 JSON。')
    document = _unwrap_storyboard_document(payload)
    _require_json_object(document, '分镜 JSON 根节点必须是对象。')
    shots = document.get('shots')
    if not isinstance(shots, list) or not shots:
        log.warning('分镜 JSON 缺少 shots 字段 raw=%s', raw_text[:500])
        raise HTTPException(status_code=502, detail='分镜 Provider 返回 JSON 但缺少有效镜头列表。')
    document.setdefault('schemaVersion', 'storyboard_document_v1')
    return document


def build_storyboard_scenes_from_json(document: JsonObject) -> list[dict[str, str]]:
    scenes: list[dict[str, str]] = []
    for index, shot in enumerate(_as_list(document.get('shots')), start=1):
        if not isinstance(shot, dict):
            continue
        shot_id = _as_text(shot.get('shotId') or shot.get('sceneId')) or f'SH{index:02d}'
        segment_id = _as_text(shot.get('segmentId'))
        visual_content = _as_text(
            shot.get('visualContent') or shot.get('summary') or shot.get('visual') or shot.get('画面内容')
        )
        visual_prompt = _as_text(shot.get('visualPrompt')) or visual_content
        title = _as_text(shot.get('title')) or ' · '.join(item for item in (shot_id, segment_id) if item)
        scenes.append(
            {
                'sceneId': shot_id,
                'title': title,
                'summary': visual_content or visual_prompt or title,
                'visualPrompt': visual_prompt or visual_content or title,
                'action': _as_text(shot.get('action') or shot.get('人物动作')),
                'audio': _as_text(shot.get('audio') or shot.get('音效/BGM')),
                'cameraAngle': _as_text(shot.get('cameraAngle') or shot.get('镜头角度')),
                'cameraMovement': _as_text(shot.get('cameraMovement') or shot.get('运镜')),
                'shootingNote': _as_text(shot.get('shootingNote') or shot.get('拍摄注意')),
                'shotLabel': segment_id,
                'shotSize': _as_text(shot.get('shotSize') or shot.get('景别')),
                'subtitle': _as_text(shot.get('subtitle') or shot.get('字幕')),
                'time': _as_text(shot.get('time') or shot.get('时间')),
                'transition': _as_text(shot.get('transition') or shot.get('转场方式')),
                'visualContent': visual_content,
                'voiceover': _as_text(shot.get('voiceover') or shot.get('口播')),
            }
        )
    return scenes


def _extract_json_object(raw_text: str, *, error_detail: str) -> JsonObject:
    normalized = raw_text.strip()
    if not normalized:
        raise HTTPException(status_code=502, detail=error_detail)

    candidates = [normalized, *_fenced_json_blocks(normalized)]
    for candidate in candidates:
        candidate = _strip_json_prefix(candidate)
        try:
            loaded = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(loaded, dict):
            return loaded
        if isinstance(loaded, list):
            return {'shots': loaded}

    log.warning('AI JSON 提取失败 raw=%s', normalized[:500])
    raise HTTPException(status_code=502, detail=error_detail)


def _fenced_json_blocks(text: str) -> list[str]:
    return [match.group(1).strip() for match in re.finditer(r'```(?:json)?\s*([\s\S]*?)```', text, re.I)]


def _strip_json_prefix(text: str) -> str:
    start_positions = [pos for pos in (text.find('{'), text.find('[')) if pos >= 0]
    if not start_positions:
        return text
    return text[min(start_positions):].strip()


def _unwrap_script_document(payload: JsonObject) -> JsonObject:
    for key in ('scriptDocument', 'document', 'rewrittenScript', 'script'):
        value = payload.get(key)
        if isinstance(value, dict) and isinstance(value.get('segments'), list):
            return value
    return payload


def _unwrap_storyboard_document(payload: JsonObject) -> JsonObject:
    for key in ('storyboardDocument', 'storyboard', 'document'):
        value = payload.get(key)
        if isinstance(value, dict) and isinstance(value.get('shots'), list):
            return value
    return payload


def _require_json_object(value: object, detail: str) -> None:
    if not isinstance(value, dict):
        raise HTTPException(status_code=502, detail=detail)


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _as_text(value: object) -> str:
    if value is None:
        return ''
    if isinstance(value, (str, int, float, bool)):
        return str(value).strip()
    return ''


def _dedupe_lines(lines: list[str]) -> list[str]:
    result: list[str] = []
    for line in lines:
        normalized = line.strip()
        if normalized and normalized not in result:
            result.append(normalized)
    return result
