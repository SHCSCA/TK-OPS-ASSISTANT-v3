# Provider Hub V2 设计说明

> 对应计划：`docs/superpowers/plans/2026-04-24-provider-hub-v2.md`  
> 设计状态：用户已确认 V2 方向。

## 1. 体验原则

Provider 配置不是供应商陈列页，而是一个接入工作台。主工作区优先服务当前要配置和验证的 Provider，模板库作为选择入口收纳在侧区，避免占用模型目录和凭据编辑空间。

## 2. Runtime 契约

`AIProviderCatalogItemDto` 在原字段基础上新增：

- `region`：`domestic`、`global`、`local`、`custom`。
- `category`：`model_hub`、`text`、`video`、`tts`、`aggregator`、`local`、`custom` 等字符串。
- `protocol`：`openai_responses`、`openai_chat`、`anthropic_messages`、`gemini_generate`、`cohere_chat`、`tts_openai`、`manual_catalog`。
- `modelSyncMode`：`remote`、`static`、`manual`。
- `tags`：中文标签，用于模板库检索和能力概览。

返回中仍禁止暴露明文 API Key。

## 3. Provider 注册表

首批模板覆盖：

- 国际：OpenAI、Anthropic、Google Gemini、Cohere、OpenRouter、ElevenLabs、Azure Speech。
- 本地：Ollama。
- 国内文本/多模态：DeepSeek、通义千问、Kimi、智谱 GLM、火山方舟、百度千帆、腾讯混元、讯飞星火、MiniMax、百川、零一万物、阶跃星辰、商汤日日新。
- 国内视频：可灵、即梦、通义万相、Vidu、海螺。
- 国内语音：阿里云语音、腾讯云语音、百度智能语音、讯飞开放平台语音。
- 自定义：自定义 OpenAI 兼容、自定义视频 Provider、自定义 TTS Provider。

这些模板只是接入入口。只有保存密钥和 Base URL 后，状态才可以进入已配置或已就绪。

## 4. 模型目录

模型目录使用同一 `AIModelCatalogItemDto`：

- `capabilityTypes` 标注 `text_generation`、`vision`、`video_generation`、`tts`、`asset_analysis` 等能力。
- `inputModalities` 标注 `text`、`image`、`audio`、`video`。
- `outputModalities` 标注 `text`、`audio`、`video`。
- 静态目录只作为内置注册表；远端刷新成功后用 Runtime 存储的模型覆盖同 Provider/Model ID。
- OpenAI 兼容类远端目录如果没有返回 modalities，Runtime 使用模型 ID / 展示名做保守推断：`seedance`、`kling`、`wanx`、`vidu`、`hailuo` 等归入视频输出，`tts`、`speech`、`voice` 等归入音频输出，`vl`、`vision` 等归入视觉输入。
- 健康检查返回 404、模型不存在或无权限时，Runtime 将该模型标记为停用覆盖；Provider 模型目录和能力矩阵只返回启用模型。

模型目录展示约束：

- 同一时间最多渲染 10 条模型记录。
- 模型列表上方提供搜索框，支持按展示名和 Model ID 过滤。
- 模型列表上方提供能力筛选，支持文本、视觉、视频、TTS、资产等能力。
- 翻页控件显示当前范围和总数，例如 `1-10 / 247`，并提供上一页/下一页。
- 搜索词或能力筛选变化时回到第一页。

## 5. Provider Hub 布局

主区结构：

```text
顶部：Provider Hub 标题、已配置数量、可远端同步数量
左列：已接入 Provider 列表 + 当前 Provider 选择
中列：模板库 + 当前 Provider 模型目录
右列：当前 Provider 凭据 Inspector
```

设计要求：

- 已接入列表只显示 configured Provider；无 configured 时显示当前 Provider 和引导态。
- 模板库按区域分组，卡片紧凑显示名称、Provider ID、能力标签、同步模式。
- 自定义入口不弹浏览器 prompt，点击后切换到对应自定义模板，由 Inspector 配置 Base URL 与密钥。
- 模型能力标签使用中文显示：文本、视觉、视频、TTS、ASR、字幕、资产。
- 模型目录最多显示 10 条，更多模型通过翻页和筛选定位，不让主工作区被远端大目录撑开。
- 宽屏三列，1080px 以下降级为两列，720px 以下单列。
- 视频生成 Provider 和资产分析 Provider 需要显示 API Key / Base URL 配置，并允许走远端模型同步；不能只作为“默认 Provider”占位。
- 能力矩阵的模型来源按能力语义匹配：字幕对齐可使用文本生成模型，资产分析可使用视觉输入且输出文本的模型，视频生成只使用视频输出模型。

## 6. 状态

- Loading：保留页面级加载态。
- Empty：Provider catalog 为空时显示中性空态。
- Not configured：模板存在但缺少密钥或 Base URL。
- Static catalog：不可远端刷新的 Provider 显示“内置目录”。
- Remote sync：支持刷新时显示“远端同步”，失败走 Runtime 错误提示。
- Ready：凭据保存且连接检查通过后在 Inspector 和右侧 Detail Panel 同步显示。
- Model blocked：连接检查发现模型无权限或不存在时，Inspector 展示中文原因，模型目录和能力选择立即刷新并隐藏该模型。

## 7. 验收

- Provider 区不再出现全量供应商大卡片墙。
- 国内模板和自定义模板在同一个模板库中可见。
- 当前 Provider 的模型目录用中文能力标签标注文本、视觉、视频、TTS 等类型。
- 当前 Provider 模型目录同时最多显示 10 条记录，几百个模型也不会撑破工作区。
- 保存凭据、刷新模型、连接检查仍走 Runtime，不出现 UI 层伪成功。
- `doubao-seedance-*` 等视频模型不能被标成纯文本模型。
- 字幕对齐、视频生成、资产分析三个能力都能从 Runtime 支持矩阵拿到符合能力语义的 Provider 和模型。
