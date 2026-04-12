# 离线永久授权与独立前置启动流程 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把现有首启授权实现重构为独立前置启动流程，确保应用先完成加载、授权和初始化，再进入主工作台。

**Architecture:** 保留现有离线授权 Runtime 契约与授权机工具，桌面端新增独立 `BootstrapGate` 状态聚合层，把启动加载、授权页、初始化页从 `AppShell` 中拆出。`AppShell` 只在前置流程完成后渲染，避免用户先看到主界面壳层。

**Tech Stack:** Vue 3、Pinia、Vue Router、Vite、Vitest、FastAPI、SQLite、Pytest

---

### Task 1: 更新真源文档

**Files:**
- Modify: `docs/superpowers/specs/2026-04-12-license-offline-design.md`
- Modify: `docs/superpowers/plans/2026-04-12-license-offline.md`

- [ ] 把“主壳遮罩式加载”更新为“独立前置启动流程”
- [ ] 明确四个前置状态：加载、错误、授权、初始化
- [ ] 明确主工作台只在前置流程完成后渲染

### Task 2: 为独立前置流程补失败测试

**Files:**
- Create: `apps/desktop/tests/bootstrap-gate.spec.ts`
- Modify: `apps/desktop/tests/setup-license-wizard.spec.ts`

- [ ] 先写 `bootstrap-gate.spec.ts`，断言未授权时不渲染 `AppShell` 的主导航
- [ ] 断言授权前显示独立授权页，且首屏可见授权码输入框
- [ ] 断言授权成功后进入初始化页
- [ ] 断言初始化完成后才进入 `/dashboard`
- [ ] 运行 `npm --prefix apps/desktop run test -- bootstrap-gate.spec.ts`
- [ ] 确认当前实现红灯

### Task 3: 拆分前置启动流程页面

**Files:**
- Create: `apps/desktop/src/bootstrap/BootstrapGate.vue`
- Create: `apps/desktop/src/bootstrap/BootstrapLoadingScreen.vue`
- Create: `apps/desktop/src/bootstrap/BootstrapErrorScreen.vue`
- Create: `apps/desktop/src/bootstrap/BootstrapLicenseScreen.vue`
- Create: `apps/desktop/src/bootstrap/BootstrapInitializationScreen.vue`
- Modify: `apps/desktop/src/App.vue`
- Modify: `apps/desktop/src/pages/setup/SetupLicenseWizardPage.vue`

- [ ] 新建独立前置页面组件，每个文件只负责一个阶段
- [ ] `App.vue` 改为先渲染 `BootstrapGate`
- [ ] `SetupLicenseWizardPage.vue` 退化为兼容页或轻包装，不再承担整个前置流程
- [ ] 确保授权页把机器码、授权码输入框、授权按钮放在首屏

### Task 4: 新增前置状态聚合 Store

**Files:**
- Create: `apps/desktop/src/stores/bootstrap.ts`
- Modify: `apps/desktop/src/stores/config-bus.ts`
- Modify: `apps/desktop/src/stores/license.ts`
- Modify: `apps/desktop/src/types/runtime.ts`

- [ ] 写新的 `BootstrapStore`，统一聚合 Runtime、配置、授权、初始化状态
- [ ] 初始化完成标记与“配置已读取”分离
- [ ] 提供统一入口：`load()`、`retry()`、`completeInitialization()`
- [ ] 保持错误结构继续复用统一 Runtime 错误类型

### Task 5: 简化主壳职责

**Files:**
- Modify: `apps/desktop/src/layouts/AppShell.vue`
- Modify: `apps/desktop/src/app/router/index.ts`
- Modify: `apps/desktop/src/app/router/route-manifest.ts`

- [ ] 移除 `AppShell` 内的启动阻塞遮罩
- [ ] `AppShell` 只处理已进入工作台后的布局
- [ ] 路由守卫改为信任 `BootstrapGate` 的前置判定
- [ ] 保留许可证路由兼容，但正常启动不应先落到主壳

### Task 6: 前置流程样式与中文文案收口

**Files:**
- Modify: `apps/desktop/src/styles/base.css`
- Modify: `apps/desktop/src/components/bootstrap/BootstrapLoadingOverlay.vue`

- [ ] 清掉残留的占位式首启样式依赖
- [ ] 把前置页面样式集中到独立区域
- [ ] 确保所有前置流程文案为中文、无开发者语气

### Task 7: 全量验证

**Files:**
- Modify: `README.md`
- Modify: `apps/desktop/README.md`

- [ ] 运行 `npm --prefix apps/desktop run test`
- [ ] 运行 `npm --prefix apps/desktop run build`
- [ ] 运行 `npm run version:check`
- [ ] 运行 `venv\\Scripts\\python.exe -m pytest tests/runtime -q`
- [ ] 运行 `venv\\Scripts\\python.exe -m pytest tests/contracts -q`
- [ ] 运行 `npm run app:dev`
- [ ] 目测确认：启动先显示独立前置流程，不先显示主工作台壳层
