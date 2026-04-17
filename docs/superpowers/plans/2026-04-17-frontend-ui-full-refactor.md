# TK-OPS 前端 UI 全量重构与 Runtime 接线 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 重构 `apps/desktop` 的 AppShell 与 16 页界面层，并统一接入现有 Runtime API，不改后端契约。

**Architecture:** 先重建共享设计层，再按页面组并行推进。所有页面继续通过 `apps/desktop/src/app/runtime-client.ts` 与 Pinia store 消费 Runtime 数据；未接通后端的能力只能表现为空态、禁用态或 `blocked`，不得伪造业务结果。

**Tech Stack:** Vue 3、TypeScript、Pinia、Vite、Vitest、Tauri 2、CSS Variables、现有 Runtime JSON 信封。

---

## Status

- 状态：Completed，已完成实现、集成与唯一一轮最终验证（2026-04-17）。
- 范围：只包含前端 UI 重构与前端 API 接线，不修改 Python Runtime、数据库、接口路径或 `docs/RUNTIME-API-CALLS.md` 的后端真源定义。
- 共享层优先，页面分波并行。
- 主代理只负责审核、集成和最终一轮验证；实现主要由子代理完成。

## Scope

### In Scope

- 重写共享设计层：tokens、motion、AppShell、统一 UI Kit、`shell-ui` 状态总线。
- 重构全部 16 页的布局、视觉层次、状态反馈和页面拆分结构。
- 把仍残留在页面中的本地状态、`alert`、mock 数据和直写逻辑替换为 store + `runtime-client` 消费。
- 补齐前端测试到与改动对应的页面、store、client 层。

### Out Of Scope

- Python Runtime、FastAPI route、schema、repository、service、数据库迁移。
- 新增 Runtime 接口、修改既有接口路径或字段。
- 伪造 AI 结果、伪造任务进度、伪造媒体分析结果。

## File Map

### 共享层

- Modify: `apps/desktop/src/styles/base.css`
- Modify: `apps/desktop/src/styles/index.css`
- Replace: `apps/desktop/src/styles/tokens.css`
- Create: `apps/desktop/src/styles/tokens/colors.css`
- Create: `apps/desktop/src/styles/tokens/typography.css`
- Create: `apps/desktop/src/styles/tokens/spacing.css`
- Create: `apps/desktop/src/styles/tokens/index.css`
- Create: `apps/desktop/src/styles/motion/keyframes.css`
- Modify: `apps/desktop/src/layouts/AppShell.vue`
- Modify: `apps/desktop/src/layouts/shell/ShellTitleBar.vue`
- Modify: `apps/desktop/src/layouts/shell/ShellSidebar.vue`
- Modify: `apps/desktop/src/layouts/shell/ShellStatusBar.vue`
- Modify: `apps/desktop/src/layouts/shell/ShellDetailPanel.vue`
- Modify: `apps/desktop/src/stores/shell-ui.ts`
- Create: `apps/desktop/src/components/ui/Button/Button.vue`
- Create: `apps/desktop/src/components/ui/Input/Input.vue`
- Create: `apps/desktop/src/components/ui/Card/Card.vue`
- Create: `apps/desktop/src/components/ui/Chip/Chip.vue`
- Create: `apps/desktop/src/components/ui/Progress/Progress.vue`
- Create: `apps/desktop/src/components/ui/Tab/Tab.vue`
- Create: `apps/desktop/src/components/ui/Dropdown/Dropdown.vue`

### 页面组 A

- Modify: `apps/desktop/src/pages/setup/**`
- Modify: `apps/desktop/src/pages/dashboard/**`
- Modify: `apps/desktop/src/pages/scripts/**`
- Modify: `apps/desktop/src/pages/storyboards/**`
- Modify: `apps/desktop/tests/setup-license-wizard.spec.ts`
- Modify: `apps/desktop/tests/creator-dashboard.spec.ts`
- Modify: `apps/desktop/tests/script-topic-center.spec.ts`
- Modify: `apps/desktop/tests/storyboard-planning-center.spec.ts`

### 页面组 B

- Modify: `apps/desktop/src/pages/workspace/**`
- Modify: `apps/desktop/src/pages/video/**`
- Modify: `apps/desktop/src/pages/voice/**`
- Modify: `apps/desktop/src/pages/subtitles/**`
- Modify: `apps/desktop/src/modules/workspace/**`
- Modify: `apps/desktop/src/modules/voice/**`
- Modify: `apps/desktop/src/modules/subtitles/**`
- Modify: `apps/desktop/tests/ai-editing-workspace-page.spec.ts`
- Modify: `apps/desktop/tests/editing-workspace-store.spec.ts`
- Modify: `apps/desktop/tests/video-deconstruction.spec.ts`
- Modify: `apps/desktop/tests/voice-studio-page.spec.ts`
- Modify: `apps/desktop/tests/voice-studio-store.spec.ts`
- Modify: `apps/desktop/tests/subtitle-alignment-page.spec.ts`
- Modify: `apps/desktop/tests/subtitle-alignment-store.spec.ts`

### 页面组 C

- Modify: `apps/desktop/src/pages/assets/**`
- Modify: `apps/desktop/src/pages/accounts/**`
- Modify: `apps/desktop/src/pages/devices/**`
- Modify: `apps/desktop/tests/asset-library.spec.ts`

### 页面组 D

- Modify: `apps/desktop/src/pages/automation/**`
- Modify: `apps/desktop/src/pages/publishing/**`
- Modify: `apps/desktop/src/pages/renders/**`
- Modify: `apps/desktop/src/pages/review/**`
- Modify: `apps/desktop/src/pages/settings/**`
- Modify: `apps/desktop/src/modules/settings/**`
- Modify: `apps/desktop/tests/ai-system-settings.spec.ts`

## Execution Order

1. 写入本 plan 与对应 design spec。
2. 完成共享层与 AppShell，锁定公共状态与样式接口。
3. 共享层冻结后，按四个页面组并行实施。
4. 审核子代理产出，解决共享样式冲突与状态不一致。
5. 统一运行一轮 `npm --prefix apps/desktop run test` 和 `npm --prefix apps/desktop run build`。

## Acceptance Gates

- 所有页面继续通过 store 与 `runtime-client.ts` 消费 Runtime 数据。
- 页面必须覆盖真实 `loading / empty / ready / error`，需要时覆盖 `blocked / disabled / saving / checking`。
- AppShell、主题、侧栏、Detail Panel、Status Bar 与蓝图尺寸和行为一致。
- 不允许页面内直写 `fetch`、`alert`、假业务数据、假 AI 结果。
- 最终前端测试与构建各运行一轮，并以结果为准汇报状态。

## Completion Notes

- 已完成共享层重建：AppShell、Sidebar、Status Bar、Detail Panel、`shell-ui`、`styles/tokens/`、`styles/motion/` 与统一 UI Kit 已落地到 `apps/desktop/src/`。
- 已完成 16 页界面重构，并把页面状态统一回收到 store + `runtime-client.ts`，移除页面内直写请求、局部 `alert` 与演示型假数据。
- 已完成工作台、资产、账号、设备、设置等页面的 Detail Panel 全局上下文联动，并按蓝图重写主工作区节奏。
- 已补齐本轮前端相关测试，主代理完成唯一一轮总验证：
  - `npm --prefix apps/desktop run test`：通过，`83` 项测试全部通过。
  - `npm --prefix apps/desktop run build`：通过。
- 构建阶段保留一条现存字体资源提示：`material-symbols.woff2` 在构建时未解析，当前按运行时路径处理；未阻塞本轮交付。
