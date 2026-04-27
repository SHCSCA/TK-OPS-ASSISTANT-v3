# 当前可用 Provider 收敛 Implementation Plan

## Goal

把 AI 与系统设置、能力绑定、模型目录和配音中心收敛到当前真实可用的 Provider 范围：

- 文本/视觉/资产等通用 AI：OpenAI、DeepSeek、火山。
- 语音合成：仅火山豆包语音。
- 其他 Provider 暂不展示、不参与能力选择、不作为语音生成候选。

## Scope

- Runtime Provider Catalog 只对外返回当前支持的 Provider。
- 支持矩阵只暴露当前支持 Provider 的模型。
- 配音中心音色仅使用火山豆包语音音色。
- 豆包语音没有 OpenAPI AK/SK 时，使用官方文档音色列表作为内置回退；有 AK/SK 时继续调用 `ListSpeakers`。

## Files

- `apps/py-runtime/src/services/ai_capability_service.py`
- `apps/py-runtime/src/services/voice_profile_sources.py`
- `apps/py-runtime/src/services/voice_service.py`
- `apps/desktop/src/pages/settings/AISystemSettingsPage.vue`
- `apps/desktop/src/modules/settings/components/ProviderCatalogPanel.vue`
- `apps/desktop/tests/runtime-helpers.ts`
- `apps/desktop/tests/ai-system-settings.spec.ts`
- `tests/runtime/test_ai_capabilities.py`
- `tests/contracts/test_ai_capabilities_contract.py`
- `tests/runtime/test_voice_service.py`

## Tasks

- [x] 锁定 Runtime Provider Catalog 只返回 OpenAI、DeepSeek、火山、火山豆包语音。
- [x] 锁定支持矩阵不再暴露 Ollama、Gemini、Qwen、Cohere、Azure Speech、ElevenLabs 等未接入 Provider。
- [x] 配音音色列表只保留 `volcengine_tts`，并同步官方豆包语音音色目录。
- [x] 前端 Provider Hub 和能力绑定下拉只展示当前支持 Provider。
- [x] 运行 Runtime、前端设置页、配音链路相关测试和构建。

## Verification

- `venv\Scripts\python.exe -m pytest tests/runtime/test_ai_capabilities.py tests/contracts/test_ai_capabilities_contract.py tests/runtime/test_voice_service.py tests/contracts/test_voice_runtime_contract.py tests/runtime/test_ai_providers.py tests/runtime/test_settings_diagnostics.py -q`
- `npm --prefix apps/desktop run test -- ai-system-settings.spec.ts ai-capability-store.spec.ts runtime-client-settings.spec.ts core-runtime-store.spec.ts bootstrap-gate.spec.ts app-shell.spec.ts project-context-guard.spec.ts setup-license-wizard.spec.ts`
- `npm --prefix apps/desktop run build`
- `git diff --check`
