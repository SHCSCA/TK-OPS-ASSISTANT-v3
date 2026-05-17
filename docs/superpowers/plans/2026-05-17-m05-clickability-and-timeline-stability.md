# M05 可点击性与时间线稳定性 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复真实浏览器复核中发现的 M05 剪辑工作台可点击性、时间线定位、工具按钮可用性和紧凑布局问题。

**Architecture:** 本次只在 M05 前端边界内收口，不变更 Runtime API。页面继续通过 Pinia store 与 Runtime 适配层通信，组件只负责展示和事件转发；时间线坐标与按钮可用性抽到纯函数，避免继续膨胀页面组件。

**Tech Stack:** Vue 3 + Pinia + TypeScript + Vitest；Vite 构建；Browser 真机交互复核。

---

## Scope

实现内容：

- 素材池来源列表点击后必须同步选中时间线片段、播放器和右侧属性面板。
- 时间尺点击坐标必须与轨道片段坐标一致，点击片段上方时间尺时播放头落在对应片段时间范围内。
- 时间线工具栏必须在当前片段无法左移、右移或分割时提前禁用对应按钮，并给出清晰状态文案。
- 1280x800 紧凑窗口和右侧属性抽屉展开时，播放器区域不得被压缩到不可用尺寸。
- 保留当前 Runtime 作为唯一业务规则入口，失败仍由 Runtime 回传并在 UI 展示。

不做内容：

- 不做撤销、重做、多选、跨轨拖拽、真实媒体渲染。
- 不新增 Runtime 接口、不改数据模型、不新增假素材。
- 不扩展到 M05 之外的 15 个页面。
- 不提交交接中列出的既有未跟踪文件。

## File Map

- Create: `docs/superpowers/plans/2026-05-17-m05-clickability-and-timeline-stability.md`
- Create: `docs/superpowers/specs/2026-05-17-m05-clickability-and-timeline-stability-design.md`
- Create: `apps/desktop/src/modules/workspace/workspaceTimelineActions.ts`
- Modify: `apps/desktop/src/modules/workspace/WorkspaceAssetRail.vue`
- Modify: `apps/desktop/src/modules/workspace/WorkspaceTimeline.vue`
- Modify: `apps/desktop/src/modules/workspace/WorkspaceTimelineToolbar.vue`
- Modify: `apps/desktop/src/pages/workspace/AIEditingWorkspacePage.vue`
- Modify: `apps/desktop/src/pages/workspace/AIEditingWorkspacePage.css`
- Test: `apps/desktop/tests/ai-editing-workspace-page.spec.ts`
- Test: `apps/desktop/tests/workspace-timeline-actions.spec.ts`

## Root Cause Notes

- 素材池来源项发出 `select-source-clip` 后，页面层虽然转给 store，但现有测试没有覆盖组件装配行为，真实浏览器里出现“按钮能点但选中态不更新”的缺口。
- 时间尺在整条时间线容器上计算百分比，轨道片段在去掉 144px 轨道标签后的 lane 内计算百分比，两者坐标基准不同。
- 工具栏只按“是否选中片段”启用移动按钮，连续相邻片段场景中按钮可点但 Runtime 必然报重叠。
- 三栏舞台布局在高度较低或属性栏展开时仍强制三列，播放器列会被压缩到不可用。

## Task 0: 文档与基线

**Files:**

- Create: `docs/superpowers/plans/2026-05-17-m05-clickability-and-timeline-stability.md`
- Create: `docs/superpowers/specs/2026-05-17-m05-clickability-and-timeline-stability-design.md`

- [ ] **Step 1: 保存计划与设计文档**

  写入本计划和对应设计文档，明确范围、文件地图、测试和浏览器复核步骤。

- [ ] **Step 2: 文档检查**

  Run: `git diff --check`

  Expected: exit 0，无空白错误。

## Task 1: 素材池来源点击选中链路

**Files:**

- Modify: `apps/desktop/src/modules/workspace/WorkspaceAssetRail.vue`
- Modify: `apps/desktop/src/pages/workspace/AIEditingWorkspacePage.vue`
- Test: `apps/desktop/tests/ai-editing-workspace-page.spec.ts`

- [ ] **Step 1: 写失败测试**

  在页面测试中切到“分镜”来源，点击第一个来源项，断言素材池项出现 active 状态、时间线选中对应片段、页面文本显示该片段详情。

- [ ] **Step 2: 运行测试确认失败**

  Run: `npm --prefix apps/desktop run test -- tests/ai-editing-workspace-page.spec.ts`

  Expected: 新增用例失败，失败点指向来源点击没有稳定更新选中态。

- [ ] **Step 3: 最小实现**

  给来源项补稳定 `data-testid` 和 `aria-pressed`，页面层处理来源点击时同步播放头到片段起点，确保素材池、时间线、播放器和属性面板拿到同一个 store 状态。

- [ ] **Step 4: 运行测试确认通过**

  Run: `npm --prefix apps/desktop run test -- tests/ai-editing-workspace-page.spec.ts`

  Expected: 页面测试通过。

## Task 2: 时间尺坐标与操作按钮可用性

**Files:**

- Create: `apps/desktop/src/modules/workspace/workspaceTimelineActions.ts`
- Modify: `apps/desktop/src/modules/workspace/WorkspaceTimeline.vue`
- Modify: `apps/desktop/src/modules/workspace/WorkspaceTimelineToolbar.vue`
- Modify: `apps/desktop/src/pages/workspace/AIEditingWorkspacePage.vue`
- Test: `apps/desktop/tests/workspace-timeline-actions.spec.ts`
- Test: `apps/desktop/tests/ai-editing-workspace-page.spec.ts`

- [ ] **Step 1: 写失败测试**

  新增纯函数测试，覆盖相邻片段下左移、右移、分割的可用性；新增页面测试覆盖工具栏按钮禁用文案。

- [ ] **Step 2: 运行测试确认失败**

  Run: `npm --prefix apps/desktop run test -- tests/workspace-timeline-actions.spec.ts tests/ai-editing-workspace-page.spec.ts`

  Expected: 新纯函数模块不存在或禁用状态断言失败。

- [ ] **Step 3: 最小实现**

  新增 `workspaceTimelineActions.ts`，由当前时间线、选中片段和播放头计算 `canMoveLeft`、`canMoveRight`、`canSplit`、`canTrim`、`reason`。时间尺点击改用轨道 lane 的坐标基准；没有 lane 时回退到自身宽度。

- [ ] **Step 4: 运行测试确认通过**

  Run: `npm --prefix apps/desktop run test -- tests/workspace-timeline-actions.spec.ts tests/ai-editing-workspace-page.spec.ts`

  Expected: 相关测试通过。

## Task 3: 紧凑窗口播放器稳定布局

**Files:**

- Modify: `apps/desktop/src/pages/workspace/AIEditingWorkspacePage.css`
- Test: `apps/desktop/tests/ai-editing-workspace-page.spec.ts`

- [ ] **Step 1: 写布局契约测试**

  在页面测试中断言 M05 根容器具备紧凑布局标记，播放器、素材池、属性栏和时间线区域具备稳定 class 与可查询结构。

- [ ] **Step 2: 运行测试确认失败**

  Run: `npm --prefix apps/desktop run test -- tests/ai-editing-workspace-page.spec.ts`

  Expected: 新布局标记断言失败。

- [ ] **Step 3: 最小实现**

  调整 CSS grid：宽屏保持三栏，紧凑宽度改为播放器优先的两栏/单栏；给播放器列设定更稳定 `minmax`，避免属性栏展开时压缩到不可用。

- [ ] **Step 4: 运行测试确认通过**

  Run: `npm --prefix apps/desktop run test -- tests/ai-editing-workspace-page.spec.ts`

  Expected: 页面测试通过。

## Task 4: 全量验证与真实浏览器复核

**Files:**

- No planned source changes.

- [ ] **Step 1: 运行桌面单测**

  Run: `npm --prefix apps/desktop test`

  Expected: exit 0。

- [ ] **Step 2: 运行构建和空白检查**

  Run:

  ```powershell
  npm --prefix apps/desktop run build
  npm run version:check
  git diff --check
  ```

  Expected: 三条命令 exit 0。

- [ ] **Step 3: 浏览器复核 M05**

  用 Browser 打开 `http://127.0.0.1:1420/workspace/editing`，真实点击：

  - 分镜、配音、字幕、资产 Tab。
  - 每个来源列表项。
  - 时间尺、时间线片段、轨道标签。
  - 左移、右移、分割、删除、左裁、右裁按钮的启用和禁用状态。
  - 1280x800 视口下右侧属性栏展开场景。

  Expected: 可点击项都有可见反馈；禁用项不可提交无效 Runtime 请求；播放器不被压缩到不可用尺寸。

