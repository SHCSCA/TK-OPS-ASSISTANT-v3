# 2026-05-11 火山豆包 TTS 2.0 OpenAPI 凭据与音色同步改造计划

## 背景

配音中心当前已存在 `volcengine_tts` 供应商与 `seed-tts-2.0` 音色同步链路，但配置界面仍以通用 `API Key / Base URL` 为主，无法清晰维护火山 OpenAPI 的 `Access Key ID` 与 `Secret Access Key`。同时历史代码中仍保留 `seed-tts-1.0` 兼容逻辑，可能导致模型选择、音色分类和调用路径不够精准。

本次改造只接入 `seed-tts-2.0`，不接入 `seed-tts-1.0`。官方音色列表以火山引擎 OpenAPI `ListSpeakers` 为准，请求业务参数固定为：

```json
{
  "ResourceIDs": ["seed-tts-2.0"]
}
```

已通过官方接口验证到 `seed-tts-2.0` 当前返回 103 个唯一音色，分类包含通用场景、角色扮演、视频配音、有声阅读、客服场景、多语种、美式英语、教学场景、未分类。分类字段存在嵌套结构，实现时必须按真实结构解析，不能只按扁平字符串处理。

## 目标

1. 在统一 AI 供应商配置入口中为 `volcengine_tts` 增加 OpenAPI `Access Key ID` 与 `Secret Access Key` 配置。
2. 保留并明确合成调用所需的火山 TTS 凭据，避免把 OpenAPI AK/SK 误当成合成 Access Token。
3. 配音中心同步音色时只请求 `seed-tts-2.0`，并准确落库音色、分类、预览地址、标签、语言、性别、年龄等官方字段。
4. 配音中心生成语音时根据选中的 `seed-tts-2.0` 音色调用 `volcengine_tts`，禁止回退到 `seed-tts-1.0`。
5. 所有配置、异常、日志、Runtime 信封和前端状态反馈保持全局一致。

## 非目标

- 不接入 `seed-tts-1.0`。
- 不在仓库写入任何真实密钥。
- 不新增脱离现有 16 页范围的新页面。
- 不把配音中心改造成独立后台或绕过 Runtime 的前端直连接口。

## 阶段安排

### 阶段一：配置契约梳理

- 扩展 `volcengine_tts` 的供应商密钥输入结构，支持：
  - 合成凭据：`accessToken` / `appId` 等当前合成链路需要字段。
  - OpenAPI 凭据：`openApiAccessKey`、`openApiSecretKey`。
  - 可选区域：默认 `cn-beijing`。
- 后端统一把字段归一化后写入现有配置总线/密钥存储，不让页面自行拼接业务规则。
- 前端保存后只显示掩码状态，不回显真实密钥。

### 阶段二：官方音色同步链路

- 保持 `ListSpeakers` 请求只带 `ResourceIDs: ["seed-tts-2.0"]`。
- 使用统一 OpenAPI 签名与异常日志。
- 修正分类解析，兼容官方返回的嵌套 `Categories` 结构。
- 同步结果写入现有 voice profile 存储，确保配音中心可按分类、标签、语言等维度展示。
- OpenAPI 凭据缺失或接口失败时返回明确中文错误和可重试状态，不静默吞错。

### 阶段三：TTS 2.0 调用收敛

- 移除或封禁 `seed-tts-1.0` 在 `volcengine_tts` 链路中的自动回退。
- 供应商能力目录只暴露 `seed-tts-2.0` 给配音中心。
- 生成语音时使用选中音色的 `VoiceType` 和 `seed-tts-2.0` 模型信息。
- 调用失败记录日志、耗时、错误原因，并通过 Runtime 信封返回中文可见错误。

### 阶段四：前端配音中心状态与交互

- 设置页为 `volcengine_tts` 展示专用字段：
  - Access Token / App ID（合成）
  - Access Key ID / Secret Access Key（OpenAPI 音色同步）
- 配音中心同步音色时展示加载中、成功数量、错误提示和重试入口。
- 音色列表使用真实 Runtime 数据；无数据时显示中性空态和配置引导。
- 不在组件内直接 fetch，继续走 Runtime adapter 与 store。

### 阶段五：测试与验证

- 后端测试：
  - 供应商密钥输入归一化与掩码。
  - `ListSpeakers` 参数固定为 `seed-tts-2.0`。
  - 嵌套分类解析与 1.0 禁用逻辑。
  - OpenAPI 失败时的中文错误与日志路径。
- 前端测试：
  - `volcengine_tts` 专用配置字段保存请求。
  - 配音中心音色刷新加载、空态、错误态。
- 回归验证：
  - AI 设置页保存供应商配置。
  - 配音中心刷新音色并选择音色生成任务。

## 文件地图

预计涉及以下边界内文件，最终以实现前核对为准：

- `apps/py-runtime/src/schemas/ai_capabilities.py`
- `apps/py-runtime/src/api/routes/ai_capabilities.py`
- `apps/py-runtime/src/services/ai_capability_service.py`
- `apps/py-runtime/src/services/voice_profile_sources.py`
- `apps/py-runtime/src/services/voice_service.py`
- `apps/py-runtime/src/ai/providers/tts_volcengine.py`
- `apps/desktop/src/types/runtime.ts`
- `apps/desktop/src/app/runtime-client.ts`
- `apps/desktop/src/pages/settings/AISystemSettingsPage.vue`
- `apps/desktop/src/pages/settings/components/ProviderConfigDrawer.vue`
- `apps/desktop/src/modules/settings/components/ProviderCatalogPanel.vue`
- `apps/desktop/src/stores/voice-studio.ts`
- `tests/`
- `docs/`

## 架构边界

- 配置必须走现有 AI Provider 配置与 Runtime 服务层，不允许页面直接持久化密钥。
- 配音中心只通过 Runtime adapter 调用刷新和合成接口。
- `volcengine_tts` 的密钥存储可以继续复用现有 provider secret 槽位，但字段归一化必须由后端统一处理。
- 不新增真实密钥到源码、测试快照或文档示例。
- 所有新增注释使用中文，并只解释复杂边界。

## 回退点

1. 若 OpenAPI 音色同步改造出现问题，可回退到旧的内置 `seed-tts-2.0` 最小音色列表，但 UI 必须提示“未完成官方同步”，不能伪装成完整音色库。
2. 若前端专用配置字段影响其他供应商，可只对 `providerId === "volcengine_tts"` 启用新字段，其他供应商维持原通用配置。
3. 若测试环境无法访问外网，使用签名客户端 mock 验证请求参数与解析逻辑，真实联调单独记录。

## 验收标准

- 设置页能配置并保存火山合成凭据与 OpenAPI AK/SK，真实密钥不回显。
- 后端通过官方 `ListSpeakers` 只请求 `seed-tts-2.0`。
- 配音中心能刷新到官方 `seed-tts-2.0` 音色，并展示真实分类。
- 生成语音调用不再自动回退到 `seed-tts-1.0`。
- 相关异常有日志、Runtime 错误信封和中文 UI 反馈。
- 至少完成改动相关测试与一条主链路回归验证。

