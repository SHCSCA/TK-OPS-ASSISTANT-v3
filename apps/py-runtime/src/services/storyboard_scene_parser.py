from __future__ import annotations

import json
import logging
from uuid import uuid4

from fastapi import HTTPException

log = logging.getLogger(__name__)

_HEADER_FIELD_MAP = {
    '镜头': 'shotLabel',
    '序号': 'shotLabel',
    '时间': 'time',
    '时间点': 'time',
    '景别': 'shotSize',
    '画面': 'visualContent',
    '画面内容': 'visualContent',
    '画面描述': 'visualContent',
    '人物动作': 'action',
    '动作': 'action',
    '镜头角度': 'cameraAngle',
    '镜头机位': 'cameraAngle',
    '机位': 'cameraAngle',
    '运镜方式': 'cameraMovement',
    '运镜': 'cameraMovement',
    '口播文案': 'voiceover',
    '口播内容': 'voiceover',
    '字幕台词': 'voiceover',
    '字幕台词英文': 'voiceover',
    '屏幕字幕': 'subtitle',
    '字幕': 'subtitle',
    '音效BGM': 'audio',
    '音效音乐': 'audio',
    '音效': 'audio',
    '音乐': 'audio',
    '转场方式': 'transition',
    '转场': 'transition',
    '拍摄注意': 'shootingNote',
    '拍摄注意事项': 'shootingNote',
    'AI画面提示词': 'visualPrompt',
    '视觉提示词': 'visualPrompt',
}


def parse_storyboard_scenes(raw_text: str) -> list[dict[str, str]]:
    normalized = _extract_json_payload(raw_text)
    try:
        payload = json.loads(normalized)
    except json.JSONDecodeError as exc:
        scenes = _parse_markdown_scenes(raw_text)
        if scenes:
            return scenes
        log.exception('分镜 Provider 返回了无效 JSON。')
        raise HTTPException(status_code=502, detail='分镜 Provider 返回了无效 JSON。') from exc

    if isinstance(payload, dict):
        payload = payload.get('scenes') or payload.get('shots') or payload.get('storyboard')

    if not isinstance(payload, list) or not payload:
        raise HTTPException(status_code=502, detail='分镜 Provider 未返回镜头列表。')

    scenes = [_json_item_to_scene(item, index) for index, item in enumerate(payload, start=1) if isinstance(item, dict)]
    if not scenes:
        raise HTTPException(status_code=502, detail='分镜 Provider 返回了空镜头。')
    return scenes


def _json_item_to_scene(item: dict[str, object], index: int) -> dict[str, str]:
    shot_label = _string_value(item, 'shotLabel') or _string_value(item, 'shot') or f'镜头{index}'
    title = _string_value(item, 'title') or shot_label
    summary = _string_value(item, 'summary') or _string_value(item, 'visualContent')
    visual_prompt = _string_value(item, 'visualPrompt') or _string_value(item, 'aiPrompt')
    return {
        'sceneId': _string_value(item, 'sceneId') or uuid4().hex,
        'title': title,
        'summary': summary,
        'visualPrompt': visual_prompt,
        'action': _string_value(item, 'action'),
        'audio': _string_value(item, 'audio'),
        'cameraAngle': _string_value(item, 'cameraAngle'),
        'cameraMovement': _string_value(item, 'cameraMovement'),
        'shootingNote': _string_value(item, 'shootingNote'),
        'shotLabel': shot_label,
        'shotSize': _string_value(item, 'shotSize'),
        'subtitle': _string_value(item, 'subtitle'),
        'time': _string_value(item, 'time'),
        'transition': _string_value(item, 'transition'),
        'visualContent': _string_value(item, 'visualContent') or summary,
        'voiceover': _string_value(item, 'voiceover'),
    }


def _string_value(item: dict[str, object], key: str) -> str:
    value = item.get(key)
    return '' if value is None else str(value).strip()


def _extract_json_payload(raw_text: str) -> str:
    normalized = raw_text.strip()
    fenced = _extract_fenced_json(normalized)
    if fenced is not None:
        return fenced
    array_payload = _extract_balanced_json(normalized, '[', ']')
    if array_payload is not None:
        return array_payload
    object_payload = _extract_balanced_json(normalized, '{', '}')
    if object_payload is not None:
        return object_payload
    return normalized


def _extract_fenced_json(text: str) -> str | None:
    fence_start = text.find('```')
    while fence_start != -1:
        line_end = text.find('\n', fence_start + 3)
        if line_end == -1:
            return None
        fence_end = text.find('```', line_end + 1)
        if fence_end == -1:
            return None
        info = text[fence_start + 3:line_end].strip().lower()
        content = text[line_end + 1:fence_end].strip()
        if info in {'', 'json'} and content:
            return content
        fence_start = text.find('```', fence_end + 3)
    return None


def _extract_balanced_json(text: str, open_char: str, close_char: str) -> str | None:
    start = text.find(open_char)
    if start == -1:
        return None

    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == open_char:
            depth += 1
        elif char == close_char:
            depth -= 1
            if depth == 0:
                return text[start:index + 1].strip()
    return None


def _parse_markdown_scenes(raw_text: str) -> list[dict[str, str]]:
    table_scenes = _parse_markdown_table_scenes(raw_text)
    if table_scenes:
        return table_scenes
    return _parse_markdown_heading_scenes(raw_text)


def _parse_markdown_table_scenes(raw_text: str) -> list[dict[str, str]]:
    scenes: list[dict[str, str]] = []
    header: list[str] = []
    for line in raw_text.splitlines():
        cells = _split_markdown_table_row(line)
        if not cells:
            continue
        if _is_table_header(cells):
            header = cells
            continue
        if _is_table_separator(cells):
            continue
        if not _is_storyboard_table(header):
            continue
        scene = _markdown_cells_to_scene(cells, len(scenes) + 1, header)
        if scene is not None:
            scenes.append(scene)
    return scenes


def _split_markdown_table_row(line: str) -> list[str]:
    stripped = line.strip()
    if not stripped.startswith('|') or stripped.count('|') < 2:
        return []
    return [_clean_markdown_cell(cell) for cell in stripped.strip('|').split('|')]


def _clean_markdown_cell(value: str) -> str:
    return value.strip().strip('*').strip()


def _is_table_separator(cells: list[str]) -> bool:
    return all(cell and set(cell) <= {'-', ':'} for cell in cells)


def _is_table_header(cells: list[str]) -> bool:
    return any(_normalize_header(cell) in _HEADER_FIELD_MAP for cell in cells)


def _is_storyboard_table(header: list[str]) -> bool:
    normalized = {_normalize_header(cell) for cell in header}
    has_visual = '画面内容' in normalized or '画面描述' in normalized or '画面' in normalized
    has_timing_or_shot = bool({'镜头', '序号', '时间', '时间点'} & normalized)
    return has_visual and has_timing_or_shot


def _markdown_cells_to_scene(
    cells: list[str],
    index: int,
    header: list[str],
) -> dict[str, str] | None:
    values = [cell for cell in cells if cell]
    if not values:
        return None

    mapped = _map_table_cells(header, cells)
    shot_label = mapped.get('shotLabel') or f'镜头{index}'
    time = mapped.get('time', '')
    title = f'{shot_label} {time}'.strip()
    visual_content = mapped.get('visualContent') or '；'.join(values)
    visual_prompt = mapped.get('visualPrompt') or _build_visual_prompt(mapped, values)
    return {
        'sceneId': uuid4().hex,
        'title': title,
        'summary': visual_content,
        'visualPrompt': visual_prompt,
        'action': mapped.get('action', ''),
        'audio': mapped.get('audio', ''),
        'cameraAngle': mapped.get('cameraAngle', ''),
        'cameraMovement': mapped.get('cameraMovement', ''),
        'shootingNote': mapped.get('shootingNote', ''),
        'shotLabel': shot_label,
        'shotSize': mapped.get('shotSize', ''),
        'subtitle': mapped.get('subtitle', ''),
        'time': time,
        'transition': mapped.get('transition', ''),
        'visualContent': visual_content,
        'voiceover': mapped.get('voiceover', ''),
    }


def _map_table_cells(header: list[str], cells: list[str]) -> dict[str, str]:
    mapped: dict[str, str] = {}
    for header_cell, value in zip(header, cells, strict=False):
        field = _HEADER_FIELD_MAP.get(_normalize_header(header_cell))
        if field and value:
            mapped[field] = value
    if 'subtitle' not in mapped and 'voiceover' in mapped:
        mapped['subtitle'] = mapped['voiceover']
    return mapped


def _build_visual_prompt(mapped: dict[str, str], values: list[str]) -> str:
    parts = [
        mapped.get('visualContent', ''),
        mapped.get('action', ''),
        mapped.get('cameraAngle', ''),
        mapped.get('cameraMovement', ''),
        mapped.get('shotSize', ''),
    ]
    compact = [item for item in parts if item]
    return '；'.join(compact or values)


def _normalize_header(value: str) -> str:
    return value.replace(' ', '').replace('/', '').replace('／', '').replace('(', '').replace(')', '').strip()


def _parse_markdown_heading_scenes(raw_text: str) -> list[dict[str, str]]:
    scenes: list[dict[str, str]] = []
    current_title: str | None = None
    current_lines: list[str] = []

    for line in raw_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith('#'):
            if current_title is not None:
                scene = _markdown_section_to_scene(current_title, current_lines, len(scenes) + 1)
                if scene is not None:
                    scenes.append(scene)
            current_title = stripped.lstrip('#').strip()
            current_lines = []
        elif current_title is not None:
            current_lines.append(stripped)

    if current_title is not None:
        scene = _markdown_section_to_scene(current_title, current_lines, len(scenes) + 1)
        if scene is not None:
            scenes.append(scene)
    return scenes


def _markdown_section_to_scene(
    title: str,
    lines: list[str],
    index: int,
) -> dict[str, str] | None:
    normalized_title = title.strip()
    if not normalized_title or not _is_storyboard_heading(normalized_title):
        return None
    summary = '；'.join(_clean_markdown_cell(line) for line in lines if line.strip())
    return {
        'sceneId': uuid4().hex,
        'title': normalized_title[:32] or f'镜头{index}',
        'summary': summary or normalized_title,
        'visualPrompt': summary or normalized_title,
        'action': '',
        'audio': '',
        'cameraAngle': '',
        'cameraMovement': '',
        'shootingNote': '',
        'shotLabel': f'镜头{index}',
        'shotSize': '',
        'subtitle': '',
        'time': '',
        'transition': '',
        'visualContent': summary or normalized_title,
        'voiceover': '',
    }


def _is_storyboard_heading(title: str) -> bool:
    normalized = title.lower().replace(' ', '')
    if any(marker in normalized for marker in ('镜头', '分镜', 'shot', 'scene')):
        return True
    return normalized.startswith('s') and normalized[1:3].isdigit()
