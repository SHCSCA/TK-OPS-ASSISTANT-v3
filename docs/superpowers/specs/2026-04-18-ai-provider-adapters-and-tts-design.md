# AI Provider 适配层与 TTS 接入设计

## 1. 背景与目标

当前 `apps/py-runtime` 的 AI 能力调用仍停留在服务层内嵌分支判断阶段：

- `AITextGenerationService` 只支持 `openai` 与 `openai_compatible` 两条硬编码路径。
- `apps/py-runtime/src/ai/providers/` 目录尚未承担真正的 Provider 适配职责。
- `VoiceService.generate_track()` 仍以 `blocked` 兼容路径为主，没有真实的 TTS Provider 调用与音频落盘链路。
- Provider 细粒度错误码还没有沿统一 envelope 回传给前端。

本轮目标是在**不改前端页面**、**不扩展新 HTTP 路由**、**不破坏当前 16 页主链**的前提下，完成以下后端落地：

1. 建立 `apps/py-runtime/src/ai/providers/` 统一 Provider 适配层。
2. 把文本生成改造成 `_PROTOCOL_MAP + adapter dispatch` 模式。
3. 落地 `openai`、`openai_compatible`、`anthropic`、`gemini`、`cohere` 五类文本 Provider 协议。
4. 落地 `tts_openai` 最小可用链路，并把 `VoiceService` 从纯 `blocked` 兼容升级为“有 TTS 配置时可真实生成，无配置时继续兼容”。
5. 打通细粒度 `error_code` 到统一 JSON envelope。
6. 回写 `docs/RUNTIME-API-CALLS.md` 第 21、24 节，使文档与后端实现闭环。

## 2. 范围与边界

### 2.1 本轮纳入范围

- `apps/py-runtime/src/ai/providers/` 目录及其子模块。
- `AITextGenerationService` 文本生成 dispatch 改造。
- `AICapabilityService` 的运行时 Provider 元数据扩展。
- `VoiceService` 的 OpenAI TTS 最小真实接入。
- `VoiceRepository` 的最小更新能力扩展。
- `app.factory` 中相关依赖注入与异常处理。
- `tests/runtime` 与 `tests/contracts` 中 AI/TTS/voice 相关测试。
- `docs/RUNTIME-API-CALLS.md` 第 21、24 节。

### 2.2 本轮明确不做

- 不改 `apps/desktop` 任意代码。
- 不新增新的 AI 设置页 HTTP 路由。
- 不实现 `tts_azure`、`tts_elevenlabs`、`tts_volcengine`、`tts_minimax` 的真实调用。
- 不把 `voice regenerate segment` 扩展成真实分段拼接与音频编辑引擎。
- 不重做模型目录、SecretStore、Settings UI 或任务总线结构。

## 3. 设计原则

### 3.1 保持现有主链稳定

当前产品主链是：

`Project -> Script -> Storyboard -> Timeline -> VoiceTrack -> SubtitleTrack -> RenderTask`

本轮改造只增强 AI 文本生成与配音生成，不改变主模型关系，不新增平行模型，不让 AI 调用层反向污染页面或路由结构。

### 3.2 小模块、单职责

根据仓库硬约束，本轮禁止把 Provider 实现继续堆进单一 service 文件。每个协议族、每个职责边界都拆成独立文件：

- 基类只定义契约。
- `_http.py` 只做通用 HTTP 通讯。
- 每个 provider 文件只实现单一协议。
- `AITextGenerationService` 只负责业务编排，不直接拼 HTTP。
- `VoiceService` 只负责配音业务，不直接散落音频文件写入逻辑。

### 3.3 默认兼容优先

对于已经存在前端消费的链路，本轮默认保守：

- 文本生成接口返回 DTO 与 envelope 不变。
- `voice generate` 在无可用 TTS dispatcher 时继续返回当前 `blocked` 行为。
- `voice regenerate segment` 保持当前 TaskBus 契约，不在本轮强行扩成真实段级音频重写。

## 4. 总体架构

### 4.1 文本生成调用层

改造后文本生成链路为：

`ScriptService / StoryboardService -> AITextGenerationService -> dispatch_text_generation -> 具体 TextGenerationAdapter -> Provider HTTP API`

职责划分如下：

- `ScriptService` / `StoryboardService`  
  继续只关心能力 ID、模板变量与持久化结果。
- `AITextGenerationService`  
  负责能力读取、Provider 运行时配置读取、Prompt 渲染、AIJob 生命周期、adapter dispatch。
- `ai/providers/__init__.py`  
  维护 provider 到协议族的注册与分发。
- `ai/providers/*.py`  
  负责具体 Provider 请求组装、响应解析和异常映射。

### 4.2 TTS 调用层

改造后 TTS 链路为：

`VoiceService.generate_track -> dispatch_tts -> TTSAdapter -> Provider HTTP API -> VoiceArtifactStore -> VoiceRepository.update_track`

职责划分如下：

- `VoiceService`  
  负责文本切段、VoiceTrack 创建、任务提交、状态推进。
- `dispatch_tts`  
  根据 `ProviderRuntimeConfig` 与 `VoiceProfile.provider` 选择对应 TTS adapter。
- `tts_openai.py`  
  负责 OpenAI TTS 调用。
- `VoiceArtifactStore`  
  负责本地目录准备与音频文件写入。
- `VoiceRepository.update_track()`  
  负责写回 `file_path`、`status`、`provider`。

## 5. Provider 适配层设计

### 5.1 目录结构

本轮目标目录结构为：

```text
apps/py-runtime/src/ai/providers/
  __init__.py
  base.py
  _http.py
  errors.py
  openai_responses.py
  openai_chat.py
  anthropic_messages.py
  gemini_generate.py
  cohere_chat.py
  tts_openai.py
```

### 5.2 基类契约

`base.py` 定义四个 dataclass 与两个抽象基类：

- `TextGenerationRequest`
- `TextGenerationResponse`
- `TTSRequest`
- `TTSResponse`
- `TextGenerationAdapter`
- `TTSAdapter`

这些类型只承载协议无关字段，不承载业务语义。业务侧字段如 `capability_id`、`project_id` 继续留在 service 与 repository。

### 5.3 公共 HTTP 层

`_http.py` 负责：

- JSON POST
- 二进制 POST
- 自定义 header 注入
- query param key 认证
- timeout
- JSON 解码与响应体读取
- 统一转换为 `ProviderHTTPException`

这样做的原因是文档 21.3 里五类 Provider 的差异主要在于：

- URL 结构
- 认证方式
- 请求体字段
- 响应解析

而不是 HTTP 底层传输方式本身。

### 5.4 错误对象

`errors.py` 定义带 `error_code` 的 `ProviderHTTPException`，继承 `fastapi.HTTPException`。  
这样可以在 `app.factory` 的统一异常处理器里直接拿到精细化 `error_code`，而不是一律退化成按状态码粗映射。

## 6. 文本 Provider dispatch 设计

### 6.1 `_PROTOCOL_MAP`

`AITextGenerationService` 不再直接判断 Provider 分支，而是先把 Provider 映射为协议族：

- `openai` -> `openai_responses`
- `anthropic` -> `anthropic_messages`
- `gemini` -> `gemini_generate`
- `cohere` -> `cohere_chat`
- `openai_compatible`、`deepseek`、`qwen`、`kimi`、`zhipu`、`minimax`、`doubao`、`baidu_qianfan`、`hunyuan`、`xai`、`mistral`、`openrouter`、`ollama`、`lm_studio`、`vllm`、`localai` -> `openai_chat`

此映射与文档第 21.4、21.6 保持一致。

### 6.2 `dispatch_text_generation`

`dispatch_text_generation(...)` 输入：

- `ProviderRuntimeConfig`
- `TextGenerationRequest`

输出：

- `TextGenerationResponse`

它内部只负责：

1. 根据 `protocol_family` 查 adapter
2. 调用 `adapter.generate(...)`
3. 返回统一响应对象

它不做：

- Prompt 渲染
- AIJob 写库
- 业务能力选择

### 6.3 现有 service 改造策略

`AITextGenerationService.generate_text()` 继续保留：

- 能力是否启用校验
- API Key / Base URL 校验
- 模板渲染
- `AIJobRepository.create_running`
- 成功 / 失败的 job 状态更新

只把底层 HTTP 调用替换为：

`dispatch_text_generation(runtime_config, request)`

这样业务侧回归面最小，`ScriptService` 和 `StoryboardService` 不需要感知新的 Provider 架构。

## 7. 文本 Provider 协议实现

### 7.1 `openai_responses.py`

迁移当前 `_call_openai_responses` 逻辑，保持行为不变：

- URL 继续使用 `provider_runtime.base_url`
- Bearer 鉴权
- `model`、`instructions`、`input`
- 解析 `output_text` 与 `output[].content[]`

目标是先完成“迁移但不改行为”。

### 7.2 `openai_chat.py`

迁移当前 `_call_openai_compatible_chat` 逻辑：

- `base_url.rstrip("/") + "/chat/completions"`
- `messages=[system,user]`
- 兼容 `message.content` 为字符串或数组

这既服务 `openai_compatible`，也服务文档定义的多数 OpenAI-compatible Provider。

### 7.3 `anthropic_messages.py`

严格按文档第 21.3.3：

- `x-api-key`
- `anthropic-version: 2023-06-01`
- `system + messages`
- 解析 `content[].text`

### 7.4 `gemini_generate.py`

严格按文档第 21.3.4：

- endpoint 为 `{base_url}/{urlencode(model)}:generateContent?key={api_key}`
- `systemInstruction`
- `contents.parts`
- 解析 `candidates[0].content.parts[].text`

### 7.5 `cohere_chat.py`

严格按文档第 21.3.5：

- endpoint `/chat`
- Bearer 鉴权
- `messages=[system,user]`
- 解析 `message.content`

## 8. TTS 设计

### 8.1 本轮只落地 `tts_openai`

文档 21.5.2 列了多个 TTS Provider，但本轮只实现：

- `tts_openai.py`

原因：

1. 风险最低
2. 可以验证完整 TTS adapter 机制
3. 不会把范围扩到不可控

其他 TTS Provider 本轮只保留为后续扩展点，不写空实现。

### 8.2 `dispatch_tts`

`dispatch_tts(...)` 根据：

- `ProviderRuntimeConfig.provider`
- `ProviderRuntimeConfig.supports_tts`
- `TTSRequest`

返回：

- `TTSResponse`

若 provider 不支持 TTS，则由 service 层决定回退到 `blocked` 兼容路径，而不是在 dispatch 层伪造响应。

### 8.3 `tts_openai.py`

严格按文档第 21.5.2：

- URL：`{base_url}/audio/speech`
- Bearer 鉴权
- 请求体：`model`、`input`、`voice`、`speed`、`response_format`
- 响应：二进制音频流

返回的 `TTSResponse` 至少包含：

- `audio_bytes`
- `content_type`
- `duration_ms=None`

### 8.4 `VoiceArtifactStore`

独立新增 `voice_artifact_store.py`，负责：

- 从 settings/runtime 配置推导语音输出目录
- 目录规则：`{workspace_root}/voice/{track_id}.{format}`
- 创建目录
- 写入音频文件
- 返回最终文件路径

这样做的原因是：

- 避免 `VoiceService` 同时承担业务编排和文件 IO
- 后续更容易替换成更复杂的音频缓存/版本目录结构

## 9. `VoiceService` 改造设计

### 9.1 兼容目标

`VoiceService.generate_track()` 本轮要兼容两种运行模式：

1. **无可用 TTS dispatcher**  
   与当前行为一致：创建 `status="blocked"` 的 `VoiceTrack`，返回 `task=None`。
2. **有可用 OpenAI TTS dispatcher**  
   创建 `status="processing"` 的 `VoiceTrack`，提交 `ai-voice` 长任务；任务执行时调用 TTS、落盘、更新为 `status="ready"`。

### 9.2 任务行为

任务流程：

1. 创建 track
2. 提交 TaskBus 任务
3. 任务中调 `dispatch_tts`
4. 调 `VoiceArtifactStore.write_audio(...)`
5. 调 `VoiceRepository.update_track(...)`
6. 完成后任务状态变更为 `succeeded`

### 9.3 本轮不做的段级真实重生成

`regenerate_segment()` 当前已经满足 TaskBus 契约，本轮不要求把某一段文本真正合成并回写到整体音轨文件中。  
否则会引入额外的音频拼接、切段时间轴和格式处理复杂度，超出本轮边界。

## 10. `ProviderRuntimeConfig` 扩展设计

当前 `ProviderRuntimeConfig` 只有：

- `provider`
- `label`
- `api_key`
- `base_url`
- `secret_source`
- `supports_text_generation`

本轮按文档第 24 节扩展为至少包含：

- `supports_tts: bool`
- `protocol_family: str`

用途：

- `AITextGenerationService` 根据 `protocol_family` 决定文本 dispatch
- `VoiceService` 根据 `supports_tts` 与 provider 决定是否走真实 TTS

### 10.1 是否对外暴露

默认不把这两个字段直接加到当前 HTTP DTO，除非测试或后端契约明确要求。  
原因是本轮目标是完善后端内部运行时能力，不是扩展前端接口字段面。

## 11. 错误处理与日志设计

### 11.1 错误码

本轮要优先支持文档 21.7 中与本轮直接相关的错误码：

- `ai_capability_disabled`
- `ai_provider_not_configured`
- `ai_provider_base_url_missing`
- `ai_provider_unsupported`
- `ai_provider_auth_failed`
- `ai_provider_rate_limited`
- `ai_provider_overloaded`
- `ai_provider_server_error`
- `ai_provider_empty_response`
- `ai_provider_timeout`
- `ai_provider_unreachable`
- `tts_provider_not_available`

### 11.2 异常处理链

Provider adapter 抛出 `ProviderHTTPException`  
-> `app.factory` 的 `HTTPException` handler 检查 `exc.error_code`  
-> `error_response(message, error_code=...)`

这样能保持：

- 统一 envelope
- 中文错误信息
- 精细 `error_code`

### 11.3 日志

所有 Provider 调用失败、音频落盘失败、TTS 任务失败都必须：

- 使用 `log.exception(...)`
- 保持中文错误信息
- 不向用户暴露 traceback

## 12. 测试设计

### 12.1 运行时单测

新增：

- `tests/runtime/test_ai_providers.py`
- `tests/runtime/test_ai_text_generation_service.py`

覆盖：

- request/response 基类
- provider response 解析
- URL 组装
- `_PROTOCOL_MAP` dispatch
- 细粒度错误码

扩展：

- `tests/runtime/test_ai_capabilities.py`
- `tests/runtime/test_voice_service.py`

覆盖：

- `ProviderRuntimeConfig.protocol_family`
- `ProviderRuntimeConfig.supports_tts`
- `voice generate` 的 blocked / processing 双路径

### 12.2 契约测试

扩展：

- `tests/contracts/test_ai_capabilities_contract.py`
- `tests/contracts/test_voice_runtime_contract.py`
- 必要时回归 `tests/contracts/test_scripts_contract.py`
- 必要时回归 `tests/contracts/test_storyboards_contract.py`

目标是确认：

- HTTP 契约未回退
- `voice` 任务对象结构仍兼容
- AI 相关接口继续走统一 envelope

## 13. 分阶段执行策略

执行顺序固定：

1. 文本 Provider 基础设施
2. OpenAI / OpenAI-compatible 迁移
3. Anthropic / Gemini / Cohere
4. `ProviderRuntimeConfig` 扩展
5. OpenAI TTS + `VoiceService`
6. 文档与总回归

这样安排的原因是：

- 文本 Provider 层是 TTS 的先决抽象
- `VoiceService` 依赖已经稳定的 dispatcher 与错误处理模式
- 风险最高的 TTS 文件写入链路放在最后，便于独立回退

## 14. 风险与回退策略

### 14.1 风险

1. 迁移 `AITextGenerationService` 后，脚本/分镜调用可能出现隐性回归。
2. Provider 错误码细化后，部分旧测试可能仍按状态码粗映射断言。
3. OpenAI TTS 落盘路径若直接绑定错误目录，可能污染工作树或临时目录。

### 14.2 回退点

- 若文本 dispatch 迁移导致 `script_service` / `storyboard_service` 回归失败，则先回退 service 层调用逻辑，但保留 provider 文件与单测。
- 若 TTS 落盘链路不稳定，则保留 `tts_openai.py` 与 dispatcher，但 `VoiceService.generate_track()` 回退到 `blocked` 路径，不把半成品文件写入链路带入主干。

## 15. 验收标准

本轮完成时必须满足：

1. `apps/py-runtime/src/ai/providers/` 不再为空目录。
2. `AITextGenerationService` 不再仅靠硬编码 `if provider == ...` 分支。
3. 至少五种文本 Provider 协议实现落地。
4. `ProviderRuntimeConfig` 具备 `supports_tts` 与 `protocol_family`。
5. `VoiceService.generate_track()` 在可用 OpenAI TTS 配置下返回真实任务链路，在不可用时继续兼容 `blocked`。
6. Provider 细粒度 `error_code` 能通过统一 envelope 返回。
7. `docs/RUNTIME-API-CALLS.md` 第 21、24 节与实现一致。
8. 本轮相关 runtime / contract 测试通过。
