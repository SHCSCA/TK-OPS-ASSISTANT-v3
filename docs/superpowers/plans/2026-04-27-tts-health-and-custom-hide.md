# TTS 健康检查与自定义入口隐藏 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修正语音 Provider 被文本模型健康检查误判的问题，并暂时隐藏 AI 设置页里的自定义 Provider 入口。

**Architecture:** Runtime 保留自定义 Provider 注册表以维持兼容，但设置页只展示当前产品阶段开放的模型平台和媒体专项 Provider。Provider 健康检查按能力类型分支处理：文本 Provider 继续走真实文本连通性探测，TTS Provider 走语音合成专项就绪检查。

**Tech Stack:** Python FastAPI Runtime + Vue 3 + TypeScript + Vitest + Pytest。

---

### Task 1: 写失败测试

**Files:**
- Modify: `tests/runtime/test_ai_capabilities.py`
- Modify: `apps/desktop/tests/ai-system-settings.spec.ts`
- Modify: `apps/desktop/tests/ai-settings-layout-contract.spec.ts`

- [ ] **Step 1: Runtime 测试 TTS Provider 健康检查**

给 `volcengine_tts` 写入 API Key 后调用 `/api/settings/ai-capabilities/providers/volcengine_tts/health-check`，期望返回 `ready`，文案包含“语音合成”，且不包含“文本模型连通性检测”。

- [ ] **Step 2: 前端测试隐藏自定义入口**

Provider Hub 不再展示“自定义接入”分组和“新增自定义”按钮，Provider 下拉不包含 `custom_*` 和 `openai_compatible`。

- [ ] **Step 3: 运行测试确认失败**

Run: `venv\Scripts\python.exe -m pytest tests/runtime/test_ai_capabilities.py -q`

Run: `npm --prefix apps/desktop run test -- ai-system-settings.spec.ts ai-settings-layout-contract.spec.ts`

Expected: FAIL。

### Task 2: 修正 Runtime 健康检查

**Files:**
- Modify: `apps/py-runtime/src/services/ai_capability_service.py`

- [ ] **Step 1: 调整健康检查顺序**

先检查 Base URL 和 API Key，再根据 Provider capability 选择检查路径。

- [ ] **Step 2: 增加 TTS 专项就绪检查**

TTS Provider 使用 `required_capability_type="tts"` 解析模型；模型存在且支持 `tts` 时返回 ready，文案说明“语音合成 Provider 已配置，可用于配音生成”。

- [ ] **Step 3: 保留文本 Provider 真实连通性检查**

`text_generation` Provider 继续走 `_probe_provider_connectivity`，不改变已有无权限模型屏蔽逻辑。

### Task 3: 隐藏自定义 Provider UI

**Files:**
- Modify: `apps/desktop/src/pages/settings/AISystemSettingsPage.vue`
- Modify: `apps/desktop/src/modules/settings/components/ProviderCatalogPanel.vue`

- [ ] **Step 1: 页面层计算可见 Provider**

新增 `visibleProviderCatalog`，过滤掉 `region=custom`、`category=custom`、`kind=custom`、`openai_compatible`、`custom_*`、`*_provider` 等暂未开放的自定义项。

- [ ] **Step 2: Provider Panel 移除自定义入口**

去掉“新增自定义”按钮，分组顺序仅保留“模型平台 / 媒体专项”。

### Task 4: 验证

- [ ] **Step 1:** `npm --prefix apps/desktop run test -- ai-system-settings.spec.ts ai-settings-layout-contract.spec.ts`
- [ ] **Step 2:** `venv\Scripts\python.exe -m pytest tests/runtime/test_ai_capabilities.py tests/contracts/test_ai_capabilities_contract.py -q`
- [ ] **Step 3:** `npm --prefix apps/desktop run build`
- [ ] **Step 4:** `git diff --check`
