from __future__ import annotations

from typing import Any

VIDEO_DECONSTRUCTION_OUTPUT_CONTRACT = """## 视频拆解中心输出契约

你是 TK-OPS 的视频拆解 Agent。你必须直接分析随请求附带的视频，输出能适配当前视频拆解中心三块界面的结果：

1. 脚本文案：还原视频中的口播、字幕和可复用脚本文案，按时间顺序切成 lines。
2. 视频关键帧：按同一时间段把画面内容、口播语音、屏幕字幕放在同一个 keyframe，保证画面与声音 1:1 对应。
3. 内容结构：提取主题与钩子、痛点与卖点、节奏与 CTA、可复用信息和风险点。

必须遵守：

- 输出必须是严格 JSON，不要 Markdown，不要解释性文字，不要代码块围栏。
- 不要把文件名、视频时长、分辨率当作主题、脚本、关键帧或内容结构。
- 每个 keyframe 必须描述真实可见画面，不要写“视频文件”“素材内容”“Download.mp4”这类元数据。
- 无法识别语音或字幕时，对应字段使用空字符串；仍然要尽量输出可见画面的 keyframes。
- 如果口播 speech 与屏幕字幕 onscreenText 完全相同，speech 保留口播内容，onscreenText 只填写屏幕上额外出现的字幕、贴纸或标题；没有额外文字则使用空字符串。
- 画面也无法识别时，返回空字符串和空数组，不要编造剧情、人物身份、卖点或字幕。
- 时间段必须使用毫秒 startMs/endMs，按画面变化或信息变化拆分，普通短视频通常每 3-5 秒一个 keyframe。
- script.lines、keyframes、segments 的时间轴必须尽量一致，方便前端三块界面同步展示。
"""

VIDEO_DECONSTRUCTION_JSON_SCHEMA_TEXT = """## 严格 JSON Schema

{
  "script": {
    "title": "",
    "language": "",
    "fullText": "",
    "lines": [
      {
        "startMs": 0,
        "endMs": 3000,
        "text": "",
        "type": "speech"
      }
    ]
  },
  "keyframes": [
    {
      "index": 1,
      "startMs": 0,
      "endMs": 3000,
      "visual": "",
      "speech": "",
      "onscreenText": "",
      "shotType": "",
      "camera": "",
      "intent": ""
    }
  ],
  "contentStructure": {
    "topic": "",
    "hook": "",
    "painPoints": [],
    "sellingPoints": [],
    "rhythm": [],
    "cta": "",
    "reusableForScript": [],
    "reusableForStoryboard": [],
    "risks": []
  },
  "segments": [
    {
      "startMs": 0,
      "endMs": 3000,
      "visual": "",
      "speech": "",
      "onscreenText": "",
      "shotType": "",
      "intent": ""
    }
  ],
  "summary": {
    "topic": "",
    "hook": ""
  }
}
"""

VIDEO_DECONSTRUCTION_AGENT_SYSTEM_PROMPT = f"""# 视频拆解 Agent

你是 TK-OPS 的视频拆解 Agent，负责把本地短视频解析成可回流脚本、分镜和剪辑链路的结构化结果。

{VIDEO_DECONSTRUCTION_OUTPUT_CONTRACT}

{VIDEO_DECONSTRUCTION_JSON_SCHEMA_TEXT}
"""

VIDEO_DECONSTRUCTION_AGENT_USER_PROMPT_TEMPLATE = f"""请分析随请求附带的视频，按照视频拆解中心三块界面返回结构化结果。

{VIDEO_DECONSTRUCTION_OUTPUT_CONTRACT}

{VIDEO_DECONSTRUCTION_JSON_SCHEMA_TEXT}

## 本次视频上下文

{{{{assets}}}}
"""

VIDEO_DECONSTRUCTION_MEDIA_FILE_USER_PROMPT_TEMPLATE = VIDEO_DECONSTRUCTION_AGENT_USER_PROMPT_TEMPLATE.replace(
    "{{assets}}",
    "{{media_file}}",
)


def build_video_deconstruction_request_prompt(video: Any) -> str:
    duration = video.duration_seconds or "未知"
    resolution = (
        f"{video.width}x{video.height}"
        if video.width is not None and video.height is not None
        else "未知"
    )
    return "\n".join(
        [
            "请直接分析随请求附带的视频，并只返回严格 JSON。",
            VIDEO_DECONSTRUCTION_OUTPUT_CONTRACT,
            VIDEO_DECONSTRUCTION_JSON_SCHEMA_TEXT,
            "## 只作为辅助上下文的元数据",
            f"文件名：{video.file_name}",
            f"视频时长：{duration} 秒",
            f"分辨率：{resolution}",
            "再次强调：不要把文件名、视频时长、分辨率当作主题、脚本、关键帧或内容结构。",
        ]
    )
