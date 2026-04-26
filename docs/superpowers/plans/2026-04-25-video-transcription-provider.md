# 视频转录 Provider 接入计划

## 目标

把视频拆解中心当前写死的“转录 Provider 未接入”改造成真实、可配置、可诊断、可重试的视频转录能力。新增能力必须进入统一 AI 能力配置与配置总线，视频拆解中心只消费 Runtime 返回的阶段状态，不在前端伪造转录结果。

## 背景

当前 FFprobe 已可用，视频导入元数据解析链路正常。视频拆解中心仍阻塞在“转录”阶段，是因为 Runtime 目前没有 `video_transcription` 或 `speech_to_text` 能力，也没有真实 ASR Provider 适配层。`VideoDeconstructionService` 在转录阶段直接写入 `provider_required`，后续“分段”阶段因此被阻塞。

## 范围

- Runtime AI 能力矩阵新增 `video_transcription`，能力类型为 `speech_to_text`。
- AI Provider 目录新增语音识别 Provider 适配边界，先支持一个真实 Provider，后续可扩展。
- 视频拆解转录阶段改为从配置总线读取 `video_transcription` 能力并执行真实转录。
- 设置中心能力配置、支持矩阵、检测中心展示该能力是否可用。
- 视频拆解中心错误提示从“Provider”泛化描述改为“视频转录/语音识别 Provider”。
- 补齐 Runtime、契约和前端关键测试。

## 不做

- 不用文本模型或多模态模型伪造音频转录。
- 不生成看起来像真实转录的假字幕或假脚本。
- 不新增第 17 个页面，所有配置仍落在“AI 与系统设置”内。
- 不引入大模型本地权重或大二进制文件进 Git。
- 不把视频拆解扩展成完整剪辑流水线，本阶段只打通转录阶段和后续分段的真实输入。

## 推荐方案

### 方案 A：优先接入火山语音识别

优点：当前项目已经配置火山方舟/火山 Provider，用户已有可用密钥上下文；对中文和短视频场景更贴近。
风险：火山 ASR 接口与方舟文本模型接口不是同一套，需要单独确认请求格式、鉴权和音频上传方式。

### 方案 B：优先接入 OpenAI Whisper 兼容接口

优点：接口形态清晰，适合先建立统一 `SpeechToTextProvider` 适配层。
风险：当前用户主要可用的是 DeepSeek 和火山，不一定已有 OpenAI 音频转录权限。

### 方案 C：先做本地 Whisper 扩展位

优点：离线、本地优先，符合桌面工具方向。
风险：模型体积大、首次准备复杂，不适合当前快速打通真实链路。

建议采用方案 A 作为首选，方案 B 作为接口设计兼容方向，方案 C 只保留配置与适配扩展位，不在本阶段落地。

## 文件地图

- 修改：`apps/py-runtime/src/services/ai_capability_service.py`
  - 新增 `video_transcription` 能力、能力类型、默认 Provider/模型映射、支持矩阵。
- 修改：`apps/py-runtime/src/services/ai_default_prompts.py`
  - 如果当前默认 Agent 配置中没有转录能力，补充非生成型能力占位说明。
- 新增：`apps/py-runtime/src/ai/providers/speech_to_text_base.py`
  - 定义统一语音识别 Provider 接口、结果结构、错误类型。
- 新增：`apps/py-runtime/src/ai/providers/volcengine_asr.py`
  - 接入火山语音识别 Provider，所有异常记录日志并转换为中文错误。
- 新增或修改：`apps/py-runtime/src/services/video_transcription_service.py`
  - 从配置总线解析能力，执行音频/视频文件转录，返回文本和片段。
- 修改：`apps/py-runtime/src/services/video_deconstruction_service.py`
  - 转录阶段不再写死 `provider_required`，改为调用转录服务；失败时保留可见阶段错误和重试路径。
- 修改：`apps/py-runtime/src/app/dependencies.py` 或当前依赖注入入口
  - 注入视频转录服务，避免页面或路由直接拼接 Provider。
- 修改：`apps/py-runtime/src/schemas/video_deconstruction.py`
  - 补齐转录结果字段，确保后续分段可以读取真实文本。
- 修改：`apps/desktop/src/types/runtime.ts`
  - 增加 `video_transcription` 能力类型与视频转录阶段错误码类型。
- 修改：`apps/desktop/src/pages/video/VideoDeconstructionCenterPage.vue`
  - 更新转录阶段中文提示、重试按钮说明、阻塞原因展示。
- 修改：`apps/desktop/src/modules/settings/components/SettingsDiagnosticsCenter.vue`
  - 检测中心展示语音识别 Provider 可用性。
- 修改：`apps/desktop/tests/video-deconstruction.spec.ts`
  - 覆盖转录 Provider 缺失、转录成功后分段解锁两个状态。
- 修改：`tests/runtime/test_ai_capabilities.py`
  - 断言能力矩阵包含 `video_transcription`。
- 修改：`tests/runtime/test_video_deconstruction_runtime_api.py`
  - 覆盖转录成功、Provider 缺失、转录失败可重试。
- 修改：`tests/contracts/test_ai_capabilities_contract.py`
  - 更新能力契约。
- 修改：`tests/contracts/test_video_deconstruction_api.py`
  - 更新视频拆解转录契约。
- 新增：`tests/runtime/test_video_transcription_service.py`
  - 覆盖 Provider 选择、异常转换、真实结果落库。

## 阶段

1. 固定设计规格：确认首个真实 ASR Provider、配置字段、返回结构、错误码和 UI 文案。
2. 能力矩阵接入：新增 `video_transcription`，保证设置中心、支持矩阵、健康检查都能识别。
3. Provider 适配层：新增统一 `SpeechToTextProvider` 接口和首个真实 Provider。
4. 视频拆解集成：转录阶段调用真实服务，成功后写入文本，分段阶段读取转录文本。
5. 前端状态适配：视频拆解中心展示准确的“语音识别 Provider”状态和重试动作。
6. 检测中心补齐：把转录能力纳入一键检测结果。
7. 测试与回归：覆盖 Runtime、契约、前端交互和主链路回归。

## 验证方式

- Runtime：
  - `video_transcription` 出现在 `/api/settings/ai-capabilities`。
  - 支持矩阵包含至少一个 `speech_to_text` 模型。
  - 未配置转录 Provider 时，转录阶段返回明确中文错误，不影响 FFprobe 诊断。
  - 配置可用 Provider 后，转录阶段写入真实文本，分段阶段解除阻塞。
- 前端：
  - 视频拆解中心不再显示泛化的“需配置 Provider”，而是显示“需配置视频转录 Provider”。
  - 转录成功后分段按钮/阶段状态正常推进。
  - 检测中心能看到视频转录能力状态和修复入口。
- 回归：
  - `tests/runtime/test_ai_capabilities.py`
  - `tests/runtime/test_video_deconstruction_runtime_api.py`
  - `tests/contracts/test_ai_capabilities_contract.py`
  - `tests/contracts/test_video_deconstruction_api.py`
  - `apps/desktop/tests/video-deconstruction.spec.ts`
  - `npm --prefix apps/desktop run build`

## 风险与回退

- ASR Provider 接口不稳定：保留 `provider_required` 和 `failed` 两类状态，前端给出重试和配置入口。
- 视频文件过大：转录服务必须设置超时、文件大小提示和日志，不在 UI 中静默等待。
- 音频抽取失败：沿用 FFmpeg/FFprobe 诊断入口，不把媒体错误误报为 Provider 错误。
- Provider 不支持视频直传：在服务层抽取音频后上传，前端不感知实现细节。
- 配置迁移风险：新增能力必须兼容已有 7 项能力配置，旧配置加载时自动补齐第 8 项。

## 验收标准

- 当前视频拆解中心不再因为硬编码逻辑永久停留在“转录 Provider 未接入”。
- 没有视频转录 Provider 时，页面明确说明缺的是“语音识别/转录 Provider”。
- 配置真实转录 Provider 后，导入视频可以从“导入”推进到“转录成功”，并允许继续“分段”。
- 所有新增异常均有日志记录、中文可见反馈和重试路径。
- 能力配置、检测中心、视频拆解状态三处展示一致。
