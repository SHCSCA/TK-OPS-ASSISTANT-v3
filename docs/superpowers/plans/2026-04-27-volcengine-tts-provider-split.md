# 2026-04-27 火山豆包语音 Provider 分离计划

## 背景

火山方舟模型 Provider 与火山豆包语音合成 Provider 当前存在混用风险：配音链路可能用 `volcengine` 的方舟配置去调用语音合成，导致 API Key、Base URL、模型资源和音色来源都不稳定。用户要求火山 TTS 与火山方舟分开配置，并且配音链路能获取音色，不能只写死一个音色。

## 目标

- 新增独立 `volcengine_tts` Provider，用于豆包语音合成 API Key 与语音接口配置。
- 从火山方舟 `volcengine` Provider 中移除 TTS 能力，避免模型目录和配音链路误用。
- 配音生成和片段重生成统一走 TTS Provider 归一化逻辑，历史 `volcengine` 音色兼容迁移到 `volcengine_tts`。
- 增加音色刷新服务与 Runtime API，支持从服务层同步 Provider 音色并 upsert 到本地音色表。
- 前端配音中心提供音色同步入口，通过 Runtime client 调用真实接口。

## 文件地图

- Runtime Provider：`apps/py-runtime/src/services/ai_capability_service.py`
- TTS 调度：`apps/py-runtime/src/ai/providers/__init__.py`
- 火山 TTS 适配：`apps/py-runtime/src/ai/providers/tts_volcengine.py`
- 配音服务：`apps/py-runtime/src/services/voice_service.py`
- 音色仓库：`apps/py-runtime/src/repositories/voice_profile_repository.py`
- Voice API：`apps/py-runtime/src/api/routes/voice.py`
- Voice schema：`apps/py-runtime/src/schemas/voice.py`
- 前端 Runtime client/store/UI：`apps/desktop/src/app/runtime-client.ts`、`apps/desktop/src/stores/voice-studio.ts`、`apps/desktop/src/modules/voice/VoiceProfileRail.vue`、`apps/desktop/src/pages/voice/VoiceStudioPage.vue`
- 测试：`tests/runtime/test_voice_service.py`、`tests/runtime/test_ai_providers.py`、`tests/runtime/test_ai_capabilities.py`、`tests/contracts/test_voice_runtime_contract.py`、`tests/contracts/test_ai_capabilities_contract.py`

## 验证方式

- 先补失败测试，覆盖 Provider 分离、音色刷新、配音链路调用 `volcengine_tts`。
- 运行 Runtime 相关测试与 Voice 合约测试。
- 前端改动运行 TypeScript/Vite 构建。
- 做 `git diff --check`，避免空白和编码问题。

## 边界

- 不写入真实 API Key，不把截图里的密钥固化到代码。
- 不新增数据库迁移字段，只复用现有 `voice_profiles` 表。
- 不把方舟文本/视频 Provider 改成 TTS 调用入口。
- 不实现供应商控制台授权开通流程，只提供配置后的调用和音色同步入口。

## 回退点

- 若音色远端来源不可用，Runtime API 返回中文错误并保留本地已有音色。
- 若 `volcengine_tts` 未配置，配音轨仍生成阻断草稿，不静默失败。
