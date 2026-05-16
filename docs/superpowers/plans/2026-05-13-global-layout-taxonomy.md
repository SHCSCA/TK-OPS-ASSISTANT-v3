# 全局页面布局分型 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立全局页面布局分型，修复工作流页面在宽屏下大面积留白的问题，同时避免设置页和普通表单被误伤。

**Architecture:** 不修改全局 `.page-container` 默认行为，而是在 AppShell 基于现有路由 `pageType` 下发宽度策略：`editor / workspace / queue / management` 铺满内容宿主，`dashboard` 和 `settings` 放宽到 1680px。M05 继续使用独立工作台根容器，作为全高工作台样板；账号和设备改为管理页栅格，避免误归类为设置页后被 1360px 上限截断。

**Tech Stack:** Vue 3 + TypeScript + Vue Router route manifest + CSS Variables + Container Queries + Vitest + Vite build。

---

## 影响边界

本轮必须避免以下风险：

- 不全局取消 `--density-page-max-width`，避免普通内容页突然拉宽。
- 不直接改所有 `.page-container`，避免表格、卡片和表单在宽屏下变形；需要全宽的页面通过 `pageType` 显式进入对应策略。
- 不改变 Runtime 数据契约，本轮只处理壳层与页面布局。
- 不增加第 17 个页面，不改变现有路由树。
- 不把旧壳或假数据逻辑带回页面。

本轮允许改动：

- 给壳层内容区增加页面类型相关的布局钩子。
- 在壳层按 `pageType` 覆盖页面容器宽度，避免逐页散落重复规则。
- 将桌面主窗口下限定为 `1680 × 900`，默认高度保留 `960`，避免工作台、右侧抽屉和状态栏在继续缩小时挤压变形。
- 右侧 Detail Panel 打开且窗口宽度不超过 `1859px` 时，壳层自动进入有效折叠侧栏，优先保护中间工作台宽度。
- 将账号管理、设备与工作区管理从 `settings` 分型迁到 `management` 分型。
- 放宽 AI 与系统设置到 1680px，但保留设置页内部左侧分区和内容列的局部约束。
- 给 M05 页面根容器更换为工作台语义类。
- 把 M05 顶部从内容页头部压缩成工作台工具栏。
- 让 M05 主体使用全宽、全高、可收缩的三栏 + 底部时间线结构。
- 增加布局回归测试，覆盖宽屏和紧凑窗口。

## 布局分型规则

全局保留五类页面策略：

| 类型 | 使用范围 | 宽度策略 | 高度策略 |
| --- | --- | --- | --- |
| 内容页 | 创作总览 | `max-width: min(1680px, 100%)` | 自然滚动 |
| 编辑流 | 脚本、分镜、配音、字幕 | 全宽，面板自行控制列宽 | 页面或局部滚动 |
| 管理页 | 账号、设备 | 全宽内容宿主，左侧对象列表 320-420px，右侧详情自适应 | 自然滚动或局部滚动 |
| 设置页 | AI 与系统设置 | 放宽到 `min(1680px, 100%)`，内部设置分区继续控宽 | 自然滚动 |
| 队列页 | 自动化、渲染、发布 | 全宽，列表优先 | 局部滚动 |
| 工作台页 | M05、视频拆解、资产、复盘 | 全宽，M05 额外全高工作台 | 页面内部滚动，避免外层横向滚动 |

## 文件地图

- Modify: `apps/desktop/src/app/router/route-manifest.ts`
  - 将账号管理、设备与工作区管理的 `pageType` 改为 `management`。
- Modify: `apps/desktop/src/layouts/AppShell.vue`
  - 使用已存在的 `data-page-type` 作为样式入口。
  - `dashboard` 页面容器放宽到 1680px。
  - `editor / workspace / queue / management` 页面容器取消最大宽度并左对齐。
  - `settings` 的 `.settings-console` 放宽到 1680px，设置页内部列宽继续由页面样式控制。
- Modify: `apps/desktop/src/pages/accounts/AccountManagementPage.css`
  - 补齐管理页根容器、概览卡、对象列表、详情区、抽屉的响应式约束。
- Modify: `apps/desktop/src/pages/devices/DeviceWorkspaceManagementPage.css`
  - 对齐管理页左列宽度和右侧详情自适应策略。
- Modify: `apps/desktop/src/pages/settings/AISystemSettingsPage.css`
  - 设置页根容器放宽到 1680px。
- Modify: `apps/desktop/src/pages/workspace/AIEditingWorkspacePage.vue`
  - 将根容器从通用内容页语义改为工作台语义，例如 `editing-workspace-page h-full`。
  - 顶部保留项目、状态和动作，但压缩成工具栏。
- Modify: `apps/desktop/src/pages/workspace/AIEditingWorkspacePage.css`
  - 删除本页对 `.page-container` 的覆盖，避免污染同名全局模式。
  - 新增 M05 专用工作台根、工具栏、主工作区、三栏区、时间线区样式。
  - 保留容器查询，在宽度不足时折叠为单列或两列。
- Modify: `apps/desktop/tests/ai-editing-workspace-page.spec.ts`
  - 覆盖 M05 根容器类、按钮状态和工作台区域存在。
- Add: `apps/desktop/tests/workspace-layout-contract.spec.ts`
  - 覆盖宽屏下 M05 不再被 `max-width` 居中限制。
  - 覆盖 9:16 预览窗口比例。
  - 覆盖紧凑宽度下三栏折叠后不产生页面横向溢出。
- Add: `apps/desktop/tests/management-layout-contract.spec.ts`
  - 覆盖账号、设备的 `management` 分型和内部栅格约束。
- Modify: `docs/UI-DESIGN-PRD.md`
  - 补充页面布局分型规则，明确工作台页不能复用内容页最大宽度。
- Modify: `docs/PROJECT-STATUS.md`
  - 记录 M05 工作台布局分型状态。

## 实施任务

### Task 1: 写布局回归测试

**Files:**

- Add: `apps/desktop/tests/workspace-layout-contract.spec.ts`
- Modify: `apps/desktop/tests/ai-editing-workspace-page.spec.ts`

- [ ] **Step 1: 新增宽屏工作台测试**

新增测试断言：

```ts
expect(root.classList.contains("editing-workspace-page")).toBe(true);
expect(root.classList.contains("page-container")).toBe(false);
```

并通过 DOM 尺寸断言 M05 根容器宽度接近内容宿主宽度，而不是小于等于 `1360px`。

- [ ] **Step 2: 新增紧凑窗口测试**

模拟较窄容器，断言工作台区域没有横向溢出：

```ts
expect(root.scrollWidth).toBeLessThanOrEqual(root.clientWidth + 1);
```

- [ ] **Step 3: 运行前端相关测试并确认先失败**

Run:

```powershell
npm --prefix apps/desktop run test -- ai-editing-workspace-page.spec.ts workspace-layout-contract.spec.ts management-layout-contract.spec.ts
```

Expected: 新增布局断言失败，因为 M05 仍使用 `.page-container`。

### Task 2: 引入 M05 专用工作台容器

**Files:**

- Modify: `apps/desktop/src/pages/workspace/AIEditingWorkspacePage.vue`
- Modify: `apps/desktop/src/pages/workspace/AIEditingWorkspacePage.css`

- [ ] **Step 1: 替换根容器语义**

把页面根容器改为：

```vue
<div class="editing-workspace-page h-full">
```

不要继续使用 `.page-container`，避免沿用内容页最大宽度。

- [ ] **Step 2: 新增工作台根布局**

在 M05 CSS 中定义：

```css
.editing-workspace-page {
  box-sizing: border-box;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  height: 100%;
  min-height: 0;
  min-width: 0;
  overflow: hidden;
  padding: var(--space-4);
  width: 100%;
}
```

### Task 3: 压缩 M05 顶部为工作台工具栏

**Files:**

- Modify: `apps/desktop/src/pages/workspace/AIEditingWorkspacePage.vue`
- Modify: `apps/desktop/src/pages/workspace/AIEditingWorkspacePage.css`

- [ ] **Step 1: 保留标题和动作，减少垂直占用**

保留当前按钮语义，调整为单行优先、必要时换行的工具栏；状态 chip 保持但不撑开主区域。

- [ ] **Step 2: 补齐按钮换行与紧凑态**

紧凑窗口下动作区允许换行，不允许按钮文本溢出或覆盖。

### Task 4: 改造 M05 主体为全宽工作台

**Files:**

- Modify: `apps/desktop/src/pages/workspace/AIEditingWorkspacePage.css`

- [ ] **Step 1: 主编辑区吃满剩余高度**

让 `.workspace-editor` 使用：

```css
.workspace-editor {
  display: grid;
  grid-template-rows: minmax(0, 1fr) auto minmax(220px, 32vh);
  min-height: 0;
  overflow: hidden;
}
```

- [ ] **Step 2: 宽屏三栏按用途分配**

宽屏下使用：

```css
.workspace-stage {
  grid-template-columns: minmax(240px, 320px) minmax(420px, 1fr) minmax(260px, 340px);
}
```

- [ ] **Step 3: 中屏和窄屏降级**

中屏改两列，窄屏改单列；任何断点下都不能出现外层横向滚动。

### Task 5: 壳层按页面类型下发宽度策略

**Files:**

- Modify: `apps/desktop/src/layouts/AppShell.vue`
- Test: `apps/desktop/tests/workspace-layout-contract.spec.ts`

- [ ] **Step 1: 不在壳层统一隐藏 workspace 滚动**

`pageType="workspace"` 当前同时覆盖 M05、视频拆解、资产中心和复盘页。本阶段不在 `AppShell.vue` 上增加 `.app-shell[data-page-type="workspace"] .app-shell__content { overflow: hidden; }`，避免影响这些页面的既有滚动。M05 的工作台滚动全部由 `editing-workspace-page` 内部负责。

- [ ] **Step 2: 按 pageType 覆盖页面容器最大宽度**

在 `AppShell.vue` 中追加：

```css
.app-shell[data-page-type="dashboard"] .app-shell__content :deep(.page-container) {
  max-width: min(1680px, 100%);
}

.app-shell[data-page-type="editor"] .app-shell__content :deep(.page-container),
.app-shell[data-page-type="workspace"] .app-shell__content :deep(.page-container),
.app-shell[data-page-type="queue"] .app-shell__content :deep(.page-container) {
  margin-left: 0;
  margin-right: 0;
  max-width: none;
}
```

同时为 `management` 写同类覆盖，让账号和设备从壳层层面进入管理页全宽策略；`settings` 只覆盖 `.settings-console` 到 1680px，避免把设置页内部表单无边界拉伸。

### Task 6: 文档更新

**Files:**

- Modify: `docs/UI-DESIGN-PRD.md`
- Modify: `docs/PROJECT-STATUS.md`

- [ ] **Step 1: 追加布局分型说明**

说明内容页、管理页、设置页、队列页、工作台页的宽高策略。

- [ ] **Step 2: 标记 M05 为工作台布局样板**

记录第一阶段只迁移 M05，M07/M08 后续按同一规范迁移。

### Task 7: 验证

**Files:**

- Test only.

- [ ] **Step 1: 跑前端测试**

Run:

```powershell
npm --prefix apps/desktop run test -- ai-editing-workspace-page.spec.ts workspace-layout-contract.spec.ts management-layout-contract.spec.ts
```

Expected: PASS。

- [ ] **Step 2: 跑构建**

Run:

```powershell
npm --prefix apps/desktop run build
```

Expected: PASS。

- [ ] **Step 3: 做宽屏和紧凑窗口截图检查**

使用本地页面检查：

- 宽屏：M05 不再居中留大空白。
- 紧凑：素材池、播放器、基础属性、时间线不重叠。
- 预览：9:16 手机窗口比例不变。
- 普通页面：至少抽查创作总览、AI 设置页，确认最大宽度策略仍保留。

## 回退点

如果 M05 改造导致页面无法使用，只回退以下文件即可：

- `apps/desktop/src/pages/workspace/AIEditingWorkspacePage.vue`
- `apps/desktop/src/pages/workspace/AIEditingWorkspacePage.css`
- `apps/desktop/tests/workspace-layout-contract.spec.ts`

如果壳层 `workspace` 滚动约束影响其他 workspace 类型页面，则先撤回 `AppShell.vue` 的工作台页约束，仅保留 M05 页面内部布局。
