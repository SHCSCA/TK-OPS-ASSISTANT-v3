# 视频转录 Provider 接入设计

## 目标

为视频拆解中心补齐真实的“视频转录/语音识别”能力，使导入视频后可以通过统一 AI 能力配置选择转录 Provider。没有可用 Provider 时，系统必须明确提示缺少的是语音识别能力，而不是继续显示泛化的 Provider 错误。

## 设计原则

- 转录是独立能力，能力 ID 固定为 `video_transcription`，能力类型为 `speech_to_text`。
- 不允许用文本生成模型伪造转录结果。
- 所有配置继续经过 AI 能力配置总线，视频拆解服务只读取 Runtime 服务层能力。
- 现阶段先打通能力注册、检测、阶段状态和可扩展 Provider 边界；真实 ASR Provider 以 OpenAI Whisper 兼容接口作为首个可测实现，火山 ASR 作为后续 Provider 适配扩展位。
- 用户当前没有配置语音识别 Provider 时，页面显示“需配置视频转录 Provider”，分段继续保持阻塞。

## 能力矩阵

新增能力：

| 字段 | 值 |
|---|---|
| capabilityId | `video_transcription` |
| capabilityType | `speech_to_text` |
| 默认启用 | `false` |
| 默认 Provider | `openai` |
| 默认模型 | `whisper-1` |
| 输入模态 | `audio`, `video` |
| 输出模态 | `text`, `segments` |

支持矩阵新增模型：

- `openai / whisper-1`
- `openai_compatible / custom-transcription-model`
- `custom_transcription_provider / custom-transcription-model`

## Provider 边界

新增统一接口 `SpeechToTextProvider`：

- 输入：本地媒体文件路径、模型 ID、语言、提示词。
- 输出：全文文本、可选时间段列表、Provider 原始 ID、耗时。
- 错误：统一转换为 `provider.required`、`provider.transcription_failed`、`media.file_missing`。

首个实现为 OpenAI Whisper 兼容接口：

- endpoint 使用 `{base_url}/audio/transcriptions`。
- 使用 multipart 上传文件。
- 不支持的 Provider 不会被当作转录 Provider。

火山 ASR 需要单独确认接口、鉴权、音频上传和轮询方式，本阶段只在能力矩阵层面预留 `speech_to_text` 类型，不写假调用。

## 视频拆解流程

转录阶段状态规则：

- 未启用 `video_transcription`：返回 `provider_required`，错误文案为“当前未配置可用视频转录 Provider，转录已阻塞；请在 AI 与系统设置中配置语音识别能力后重试。”
- Provider 配置不完整：返回 `provider_required`，附带配置入口。
- 文件不存在：返回 `failed`，错误码 `media.file_missing`。
- Provider 调用失败：返回 `failed`，错误码 `provider.transcription_failed`。
- 转录成功：写入 `succeeded`，`result_summary` 显示转录字数，后续分段阶段解除阻塞。

## 前端展示

视频拆解中心：

- 阶段状态 `provider_required` 的标签从“需配置 Provider”改为“需配置转录 Provider”。
- 转录阶段错误文案使用 Runtime 返回内容。
- 分段阶段继续显示“视频转录尚未成功，分段已阻塞”。
- “配置 Provider”按钮仍跳转到 AI 与系统设置。

检测中心：

- 新增检测项“视频转录 Provider”。
- 状态来源为 `video_transcription` 能力配置和 Provider 健康状态。
- 未配置时不算系统失败，显示 warning，因为视频拆解转录功能不可用但 Runtime 主体仍可运行。

## 兼容迁移

已有数据库只有 7 项能力时，加载能力配置必须自动补齐 `video_transcription`，不能要求用户清空配置。保存能力配置时必须接受完整 8 项集合。

## 测试要求

- Runtime 能力配置返回 8 项，包含 `video_transcription`。
- 支持矩阵包含 `speech_to_text` 模型。
- 旧配置自动补齐新能力。
- 视频转录 Provider 未配置时，转录阶段返回准确中文提示。
- 视频转录成功时，阶段状态为 `succeeded`，分段不再因为转录缺失阻塞。
- 前端视频拆解页展示“需配置转录 Provider”。

## 非目标

- 不在本阶段实现火山 ASR 真实调用。
- 不下载本地 Whisper 模型。
- 不生成假转录内容。
- 不扩展视频拆解 UI 为复杂剪辑工作台。
