# Agent 提示词补强设计

## 设计原则

当前脚本生成、脚本改写、分镜生成已经以 JSON 文档作为系统真源。Excel 配置中的 Markdown 结构适合作为角色规则来源，但不适合作为 Runtime 的最终输出契约。因此本次设计采用“规则吸收，契约不变”的方式。

## 能力设计

### 脚本生成

- 继续输出 `script_document_v1`。
- 强化输入补全、前 3 秒强钩子、每 5-8 秒留存刺激点、手机竖屏可拍摄、短句口播、移动端字幕、自然 CTA 和合规改写。
- `segments` 继续使用稳定 `S01`、`S02` 编号，给分镜、配音、字幕保留映射依据。
- `handoff` 继续声明下游可用状态和交接信息。

### 脚本改写

- 继续输出完整新版 `script_document_v1`，不输出局部片段。
- 保留主题、目标用户、核心逻辑和段落编号。
- 增加 `rewriteSummary`、`changedSegments`、`requiresStoryboardRegeneration` 等可选交接字段要求，方便后续联动判断。
- 要求同步更新 `voiceoverFull`、`subtitles` 与 `handoff`。

### 分镜生成

- 继续输出 `storyboard_document_v1`。
- 要求每个 `shot` 必须绑定来源 `segmentId`，并使用 `SH01`、`SH02` 递增编号。
- 强化 TikTok 9:16、前 3 秒视觉冲击、每 3-5 秒视觉变化、手机可拍、真实实拍 / AI 视频镜头区分。
- 保持 `voiceover`、`subtitle`、`visualPrompt` 与视频生成交接字段完整。

## 不变项

- TTS、字幕、视频生成、质量检查的 Excel 配置与当前默认基本一致，暂不改动。
- `asset_analysis` 和 `video_transcription` 继续使用视频拆解 JSON 契约，避免回退为旧版素材分析 Markdown。
