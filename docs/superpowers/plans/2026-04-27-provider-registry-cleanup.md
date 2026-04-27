# Provider 注册表清理 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 清理 AI 与系统设置里的 Provider 展示和选择逻辑，让模型平台、媒体专项和自定义接入分组展示，并让能力绑定只显示当前能力可用的 Provider。

**Architecture:** Runtime 继续保留完整 Provider 注册表，前端按 Provider 的 `category`、`kind`、`region`、`capabilities` 做展示分组。能力 Inspector 使用 Runtime support matrix 做过滤，只允许当前能力支持的 Provider 进入下拉，同时保留已绑定的历史 Provider 以便用户迁移。

**Tech Stack:** Vue 3 + TypeScript + Vitest + Python Runtime Provider Catalog。

---

### Task 1: 锁定 Provider 展示契约

**Files:**
- Modify: `apps/desktop/tests/runtime-helpers.ts`
- Modify: `apps/desktop/tests/ai-system-settings.spec.ts`
- Modify: `apps/desktop/tests/ai-settings-layout-contract.spec.ts`

- [ ] **Step 1: 扩充测试夹具**

在 `runtimeFixtures.aiProviderCatalog` 中加入媒体专项和自定义专项 Provider，用于验证它们不会混入通用模型能力选择器。

- [ ] **Step 2: 写能力过滤失败测试**

在 “加载集中式 AI 能力配置，并通过能力总线保存更新” 测试中断言 `script_generation` 的 Provider 下拉只包含 support matrix 推荐的 Provider，不包含 `volcengine_tts`、`custom_tts_provider`、`custom_openai_compatible` 等不属于该能力的 Provider。

- [ ] **Step 3: 写 Provider Hub 分组测试**

在 Provider 配置测试中断言当前 Provider 下拉存在 “模型平台 / 媒体专项 / 自定义接入” 分组，并且媒体专项 Provider 仍可在 Provider Hub 中被找到。

- [ ] **Step 4: 运行测试确认失败**

Run: `npm --prefix apps/desktop run test -- ai-system-settings.spec.ts ai-settings-layout-contract.spec.ts`

Expected: FAIL，因为现有 UI 仍然平铺 Provider，能力 Inspector 仍然全量开放。

### Task 2: 实现能力级 Provider 过滤

**Files:**
- Modify: `apps/desktop/src/modules/settings/components/AICapabilityInspector.vue`

- [ ] **Step 1: 使用 support matrix 过滤 Provider**

`providerOptions` 改为仅保留 `supportItem.providers` 中的 Provider；如果当前能力已有 Provider 绑定但不在推荐列表中，则临时保留它用于迁移。

- [ ] **Step 2: 保持模型选择逻辑不变**

继续优先使用当前 Provider 已加载模型目录，未加载时回退到 support matrix 的模型选项。

### Task 3: 实现 Provider Hub 分组

**Files:**
- Modify: `apps/desktop/src/modules/settings/components/ProviderCatalogPanel.vue`

- [ ] **Step 1: 定义分组规则**

新增 `providerGroup()`：`custom`/`region=custom` 进入自定义接入；`tts`、`speech_to_text`、`video_generation`、`asset_analysis` 或媒体 category 进入媒体专项；其余进入模型平台。

- [ ] **Step 2: 下拉和模板库按分组展示**

当前 Provider 下拉使用 `optgroup`；模板库 tabs 从地域改为 Provider 分组。

- [ ] **Step 3: 更新文案**

明确说明 Provider Hub 按模型平台、媒体专项、自定义接入分组；能力绑定会按可用 Provider 收敛。

### Task 4: 验证

**Files:**
- Test: `apps/desktop/tests/ai-system-settings.spec.ts`
- Test: `apps/desktop/tests/ai-settings-layout-contract.spec.ts`

- [ ] **Step 1: 运行前端测试**

Run: `npm --prefix apps/desktop run test -- ai-system-settings.spec.ts ai-settings-layout-contract.spec.ts`

Expected: PASS。

- [ ] **Step 2: 运行前端构建**

Run: `npm --prefix apps/desktop run build`

Expected: PASS。

- [ ] **Step 3: 检查补丁空白错误**

Run: `git diff --check`

Expected: 无新增空白错误。
