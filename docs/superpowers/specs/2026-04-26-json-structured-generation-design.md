# JSON 真源与组件化展示设计

## 数据契约

### 脚本版本

- `format`: `json_v1 | legacy_markdown`
- `documentJson`: 新脚本文档真源，包含 `metadata`、`segments`、`voiceoverFull`、`subtitles`、`cta`、`storyboardBrief` 等字段。
- `content`: 仅保留为兼容文本和复制兜底，不作为新前端渲染真源。

### 分镜版本

- `format`: `json_v1 | legacy_markdown`
- `storyboardJson`: 新分镜文档真源，包含 `metadata`、`overview`、`shots`、`visualPrompts`、`executionNotes` 等字段。
- `scenes`: 由 `storyboardJson.shots` 派生，继续服务旧卡片和列表兼容。

## Runtime 设计

- 脚本生成、脚本改写和分镜生成调用模型后先做 JSON 提取与校验。
- 校验通过后保存结构化 JSON，并生成可读纯文本用于复制与旧链路兜底。
- 校验失败时返回中文错误，日志记录原始响应摘要，避免前端出现空白或误解析。
- AI 能力保存接口只接受 `capabilityId`、`enabled`、`provider`、`model`，提示词来自系统默认配置。

## 前端设计

- 脚本页通过 `documentJson` 构造 ViewModel，渲染标题、信息表、段落表、口播稿、字幕稿和 CTA。
- 分镜页通过 `storyboardJson` 构造 ViewModel，列表视图、大纲视图和预览模式共用同一份结构化数据。
- 配音中心优先读取 `voiceoverFull`，其次读取段落 `voiceover`，最后降级旧 Markdown。
- 字幕对齐中心优先读取 `subtitles`，其次读取段落 `subtitle`，最后降级旧 Markdown。
- 复制功能由 JSON 生成可读纯文本，不复制内部 JSON。

## 兼容策略

- 历史 Markdown 版本继续展示 Markdown 预览。
- 历史 Markdown 仍可通过旧解析器进入配音和字幕下游。
- 新版本优先使用 JSON；仅当 JSON 缺失时进入旧兼容路径。

## 风险控制

- 严格校验模型输出，失败时直接阻断保存并提示修正模型输出。
- 前后端字段保持可选，避免旧数据打开失败。
- 分镜 `shots` 是唯一新真源，避免再次出现错误拆段和错列。
