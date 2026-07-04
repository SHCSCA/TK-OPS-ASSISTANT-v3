# 项目级动效体系 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立 TK-OPS 完整的四层动效体系——设计 token、关键帧、Vue 过渡、组件 micro-interaction——确保全应用动效一致、可维护、可访问。

**Architecture:** 四层单向依赖：Token → Keyframes → Vue Transition → 组件 Micro-interaction。Token 层对齐 UI-DESIGN-PRD 文档并修复 doc-to-code drift。每层独立测试，CSS 变量优先，硬编码禁止。

**Tech Stack:** CSS Custom Properties + @keyframes + Vue `<transition>/<transition-group>` + CSS transitions。不加第三方动效库。

---

## Scope

实现内容：

- Layer 1：motion token 从 spacing.css 拆分为独立 motion.css，对齐文档值，清理/归类 18 个 keyframes。
- Layer 2：Vue transition 命名规范化，补齐缺失的过渡。
- Layer 3：组件 micro-interaction 矩阵逐组件补齐（hover/focus/active/enter/leave）。
- Layer 4：页面布局过渡确认与 token 化。
- Skeleton 组件、数字动效等缺失功能补齐。
- prefers-reduced-motion 硬编码 transition 审计与修复。
- 动效契约测试。

不做内容：

- 不做第三方动效库（Lottie/GSAP/Motion One）。
- 不做 Canvas/WebGL/Three.js 动效。
- 不做帧级视频时间线动画。
- 不修改功能行为，只修改表现层。

## File Map

### Layer 1 — Token + Keyframes

- Create: `apps/desktop/src/styles/tokens/motion.css`
- Modify: `apps/desktop/src/styles/tokens/spacing.css`（移除 motion 变量）
- Modify: `apps/desktop/src/styles/motion/keyframes.css`（清理+新增）
- Modify: `apps/desktop/src/styles/index.css`（import 顺序）
- Create: `apps/desktop/src/styles/motion/README.md`
- Modify: `docs/UI-DESIGN-PRD.md`（§7.4 easing 对齐）

### Layer 2 — Vue Transition

- Modify: `apps/desktop/src/modules/workspace/WorkspaceAssetRail.vue`（Tab 切换过渡）
- Modify: `apps/desktop/src/modules/workspace/WorkspaceInspector.vue`（Section 展开收起过渡）
- Modify: `apps/desktop/src/layouts/AppShell.vue`（sidebar nav items 过渡）
- Modify: `apps/desktop/src/components/ui/Toast/Toast.vue`（列表 enter/leave）

### Layer 3 — 组件 Micro-interaction

- Modify: `apps/desktop/src/components/ui/Chip/Chip.vue`
- Modify: `apps/desktop/src/components/ui/Card/Card.vue`
- Modify: `apps/desktop/src/components/ui/Input/Input.vue`
- Modify: `apps/desktop/src/components/ui/Select/Select.vue`
- Modify: `apps/desktop/src/components/ui/Switch/Switch.vue`
- Modify: `apps/desktop/src/components/ui/Checkbox/Checkbox.vue`
- Modify: `apps/desktop/src/components/ui/Radio/Radio.vue`
- Modify: `apps/desktop/src/components/ui/Progress/Progress.vue`
- Modify: `apps/desktop/src/components/ui/Badge/Badge.vue`
- Modify: `apps/desktop/src/components/ui/EmptyState/EmptyState.vue`

### Layer 4 — 页面布局过渡

- Modify: `apps/desktop/src/layouts/DetailPanel.vue`

### 新建组件

- Create: `apps/desktop/src/components/ui/Skeleton/Skeleton.vue`
- Create: `apps/desktop/src/composables/useCountUp.ts`

### 测试

- Create: `apps/desktop/tests/motion-contracts.spec.ts`（token 和 keyframes 契约测试）
- Create: `apps/desktop/tests/skeleton.spec.ts`
- Modify: `apps/desktop/tests/workspace-layout-contract.spec.ts`（动效相关场景）

### 文档

- Modify: `docs/superpowers/plans/2026-05-17-project-motion-system.md`
- Modify: `docs/UI-DESIGN-PRD.md`
- Modify: `CHANGELOG.md`

## Execution Record

| Task | Commit | Status |
|------|--------|--------|
| Task 0 计划与设计 | 待提交 | 已完成 |
| Task 1 Token 拆分与对齐 | 待提交 | **已完成（5 级速度系统替代原 4 级）** |
| Task 2 Keyframes 治理 | 待提交 | 已完成（16 活跃 + 7 future-use + 1 删除） |
| Task 3 Vue Transition 补齐 | 待提交 | 已完成（AssetRail/Inspector/AppShell/Toast） |
| Task 4 组件 Micro-interaction（C/D 级） | 待提交 | 已完成（Chip focus-visible + active） |
| Task 5 组件 Micro-interaction（A/B 级微调） | 待提交 | 已完成（Progress enter） |
| Task 6 Skeleton + CountUp | 待提交 | 已完成 |
| Task 7 Reduced-motion 硬编码审计 | 待提交 | 已完成（11 处硬编码全部替换） |
| Task 8 验证与文档 | 待提交 | 已完成（284 测试全通过） |
| Task 9 全量回归与发布号 | 待提交 | 待定 |

### M05 深度自查结果

**日期：** 2026-05-17
**范围：** AIEditingWorkspacePage + 全部 15 个 workspace 模块文件

**已完成确认项：**
- 页面布局：三栏 workspace-stage（素材池 270-330px | 播放器 520px-1fr | 基础属性 280-340px）+ 底部时间线
- 响应式：container query 1040px / 860px + max-height 860px 短屏适配
- 状态覆盖：loading / empty / error / blocked / ready / saving 全部覆盖
- 测试覆盖：12 个 M05 测试文件，含端到端测试（ai-editing-workspace-page.spec.ts）
- 动效过渡：page-fade / tab-fade / msg-fade / issue-slide / clip-list / track-list
- 无障碍：aria-label / role=tab / aria-selected / sr-only / aria-busy / tabindex
- 预检联动：Inspector 展示预检问题 + 点击定位到片段
- 智能粗剪：入队反馈 + TaskBus 联动（commit d4e7547）
- 基础工具：选择 / 左移 / 右移 / 裁剪 / 分割 / 删除 / 磁吸
- 素材池：资产 Tab + 来源 Tab + 加入时间线 + 替换片段
- 时间线拖拽：移动 / 裁剪 / 磁吸
- Detail Panel 上下文联动
- 无 TODO / FIXME 残留
- 无硬编码 transition duration
- 动效 token 全部使用 CSS 变量

**已修复问题：**
- WorkspaceAssetRail focus-visible 缺少可见焦点环 → 添加 outline: 2px solid var(--brand-primary)

**V1 合理 Feature Gap（非 bug）：**
- 播放器按钮全部 disabled（上一段 / 播放 / 下一步）— 无真实播放引擎
- 预览进度条始终 0% — 无真实播放
- 时间线缩放指示器纯装饰 — 功能未实现
- 资产缩略图为 icon 占位 — thumbnailStatus.missing
- AI 替换旁白 / 重对齐字幕按钮 disabled — Provider 未接入
- WorkspaceToolbar 中创建时间线 / 保存草稿按钮与 page header 功能冗余

> **设计变更说明**：实际实现了 **5 级速度系统**（Haptic 150ms / Instant 280ms / Content 500ms / Scene 900ms / Celebration 1500ms），替代了计划中原有的 4 级系统。旧 token 名（`--motion-fast/default/base/slow/lazy`）作为向后兼容别名保留。
> 普通加载 spinner 独立为 `--motion-spinner: 2400ms`，避免等待态旋转过快。详见设计 spec 文档。

## Task 0: 计划、设计与分支基线

**Files:**

- Create: `docs/superpowers/specs/2026-05-17-project-motion-system-design.md`
- Create: `docs/superpowers/plans/2026-05-17-project-motion-system.md`

- [ ] **Step 1: Create branch**

Run:

```powershell
git checkout -b codex/project-motion-system
```

Expected: branch is `codex/project-motion-system`.

- [ ] **Step 2: Save design and implementation plan**

The spec and plan must define scope, architecture, file map, task order, verification and commit policy.

- [ ] **Step 3: Verify documentation-only diff**

Run:

```powershell
git diff --check
git status --short --branch
```

Expected: only the two new M05 docs are staged or modified.

- [ ] **Step 4: Commit Task 0**

```powershell
git add docs/superpowers/specs/2026-05-17-project-motion-system-design.md docs/superpowers/plans/2026-05-17-project-motion-system.md
git commit -m "docs: 规划项目级动效体系"
```

## Task 1: Token 拆分与文档对齐

**Files:**

- Create: `apps/desktop/src/styles/tokens/motion.css`
- Modify: `apps/desktop/src/styles/tokens/spacing.css`
- Modify: `apps/desktop/src/styles/index.css`
- Modify: `docs/UI-DESIGN-PRD.md`

- [ ] **Step 1: 创建 motion.css**

从 spacing.css 拆分出完整的 motion token：

```css
/* === Motion Tokens === */
/* Duration */
--motion-haptic: 150ms;
--motion-instant: 280ms;
--motion-content: 500ms;
--motion-scene: 900ms;
--motion-celebration: 1500ms;
--motion-spinner: 2400ms;  /* 普通加载 spinner，约 2.4 秒/圈 */
--motion-spin: 3s;         /* 装饰性旋转，不用于普通加载 */

/* Easing */
--ease-standard: cubic-bezier(0.4, 0.0, 0.2, 1);
--ease-decelerate: cubic-bezier(0.0, 0.0, 0.2, 1);
--ease-accelerate: cubic-bezier(0.4, 0.0, 1.0, 1);
--ease-spring: cubic-bezier(0.22, 1, 0.36, 1);
--ease-bounce: cubic-bezier(0.18, 1.25, 0.4, 1);

/* Transition shorthand helpers */
--transition-fast: all var(--motion-instant) var(--ease-standard);
--transition-base: all var(--motion-content) var(--ease-standard);
--transition-slow: all var(--motion-scene) var(--ease-standard);
--transition-spring: all var(--motion-content) var(--ease-spring);

/* Reduced motion */
:root[data-reduced-motion="true"] {
  --motion-haptic: 1ms;
  --motion-instant: 1ms;
  --motion-content: 1ms;
  --motion-scene: 1ms;
  --motion-celebration: 1ms;
  --motion-spinner: 8s;
  --motion-spin: 6s;
}
```

- [ ] **Step 2: 清理 spacing.css**

移除 `--motion-*` 和 `--ease-*` 相关变量，确保 spacing.css 只保留 spacing 和 layout 定义。

- [ ] **Step 3: 更新 index.css import**

```css
@import './tokens/motion.css';
@import './tokens/spacing.css';   /* spacing.css 不再包含 motion */
```

Import 顺序：motion.css 必须在 spacing.css 之前（motion 更基础，被 spacing 和其他层依赖）。

- [ ] **Step 4: 更新 UI-DESIGN-PRD.md §7.4**

将 easing 曲线描述从 `(0.2,0.8,0.2,1)` 更新为 `(0.4,0.0,0.2,1)`，并将 duration 文档值同步为当前 5 级速度系统。

- [ ] **Step 5: 验证**

```powershell
npm --prefix apps/desktop run test
rg "transition:.*\dms" apps/desktop/src --include '*.css' --include '*.vue' | measure -line
```

Expected: 所有测试通过，硬编码 duration 列表数量被记录（Task 7 处理）。

- [ ] **Step 6: Commit**

```powershell
git add apps/desktop/src/styles/tokens/motion.css apps/desktop/src/styles/tokens/spacing.css apps/desktop/src/styles/index.css docs/UI-DESIGN-PRD.md
git commit -m "feat: 拆分 motion token 并对齐文档值"
```

## Task 2: Keyframes 治理

**Files:**

- Modify: `apps/desktop/src/styles/motion/keyframes.css`
- Create: `apps/desktop/src/styles/motion/README.md`

- [ ] **Step 1: 审计 18 个 keyframes**

逐条验证消费者：

| Keyframe | 消费者存在？ | 决策 |
|----------|-------------|------|
| `fade-in` | ✓ | 保留 |
| `fade-out` | ✓ | 保留 |
| `slide-up` | ✓ | 保留 |
| `slide-down` | ✓ | 保留 |
| `scale-in` | ✓ | 保留 |
| `scale-out` | ✓ | 保留 |
| `spin` | ✓ | 保留 |
| `pulse-badge` | ✓ | 保留 |
| `pulse-dot` | ✓ | 保留 |
| `exception-breathe` | ✓ | 保留 |
| `toast-slide-up` | ✓ | 保留 |
| `number-count-up` | ✗ | 保留（Task 6 消费） |
| `modal-enter` | ✗ | 删除（Modal 使用 Vue transition，不用此 keyframe） |
| `clip-gen-grow` | ✗ | 删除（片段生成动效未实现，将来需重做） |
| `pipeline-node-pulse` | ✗ | 删除（pipeline 节点动效已取消） |
| `voice-wave-play` | ✗ | 保留并注释用途（语音播放波形动效，等待 Voice 模块完善） |
| `subtitle-align-scan` | ✗ | 删除（字幕对齐扫描动效未使用） |
| `render-complete-glow` | ✗ | 删除（渲染完成发光动效未使用） |
| `provider-test-shake` | ✗ | 删除（Provider 测试抖动仅为开发调试用） |

- [ ] **Step 2: 清理 keyframes.css**

删除标记为删除的 keyframes，为保留的 keyframes 添加注释说明消费者位置。

- [ ] **Step 3: 新增 keyframes**

添加：
- `skeleton-pulse`：骨架屏脉冲动效，opacity 0.4 → 1.0 循环
- `page-enter`：页面进入动效，fade + translateY(8px) → identity
- `page-leave`：页面离开动效，fade-out + translateY(-4px)
- `list-item-enter`：列表项进入，fade + translateX(-8px) → identity
- `list-item-leave`：列表项离开，fade + scale(0.95)
- `badge-count-change`：徽标数字变化，scale(1.2) → identity

- [ ] **Step 4: 创建 keyframes README 索引**

`apps/desktop/src/styles/motion/README.md`：

```markdown
# Motion Keyframes Index

## Core Transitions
- `fade-in` / `fade-out` — 通用显隐
- `slide-up` / `slide-down` — 上下滑入滑出
- `scale-in` / `scale-out` — 缩放显隐

## Component Keyframes
- `skeleton-pulse` — Skeleton.vue 加载脉冲
- `pulse-badge` — Badge/StatusDot 状态脉冲
- `pulse-dot` — Bootstrap 加载脉冲
- `exception-breathe` — BootstrapErrorScreen 呼吸动效
- `toast-slide-up` — Toast 滑入
- `badge-count-change` — Badge 数字变化
- `number-count-up` — useCountUp 数字累加（暂未使用）

## Animation / Decorative
- `spin` — 加载旋转（Button AI variant 等）
- `voice-wave-play` — 保留，语音播放波形动效
```

- [ ] **Step 5: 验证**

```powershell
npm --prefix apps/desktop run test -- tests/layout-contract*       # 无回归
grep -r "clip-gen-grow\|pipeline-node-pulse\|subtitle-align-scan\|render-complete-glow\|provider-test-shake" apps/desktop/src    # 确认无残留引用
```

- [ ] **Step 6: Commit**

```powershell
git add apps/desktop/src/styles/motion/keyframes.css apps/desktop/src/styles/motion/README.md
git commit -m "feat: 治理 keyframes — 清理孤立项、分类管理"
```

## Task 3: Vue Transition 补齐

**Files:**

- Modify: `apps/desktop/src/modules/workspace/WorkspaceAssetRail.vue`
- Modify: `apps/desktop/src/modules/workspace/WorkspaceInspector.vue`
- Modify: `apps/desktop/src/layouts/AppShell.vue`
- Modify: `apps/desktop/src/components/ui/Toast/Toast.vue`

- [ ] **Step 1: AssetRail Tab 切换过渡**

WorkspaceAssetRail 的 Tab 切换（"素材" / "模板" / "我的"）使用 `<transition name="tab-fade" mode="out-in">`：

```css
.tab-fade-enter-active,
.tab-fade-leave-active {
  transition: opacity var(--motion-fast) var(--ease-standard);
}
.tab-fade-enter-from,
.tab-fade-leave-to {
  opacity: 0;
}
```

- [ ] **Step 2: Inspector Section 展开收起**

WorkspaceInspector 的折叠面板使用 `<transition name="section-collapse">`：

```css
.section-collapse-enter-active,
.section-collapse-leave-active {
  transition: grid-template-rows var(--motion-base) var(--ease-standard);
}
.section-collapse-enter-from,
.section-collapse-leave-to {
  grid-template-rows: 0fr;
}
```

- [ ] **Step 3: AppShell Sidebar Nav Items**

Sidebar 导航项使用 `<transition-group name="nav-item">` 为 enter/leave 添加动效（用户显隐导航项时）。

- [ ] **Step 4: Toast 列表过渡**

Toast 容器使用 `<transition-group name="toast-list">`：

```css
.toast-list-enter-active {
  transition: all var(--motion-base) var(--ease-spring);
}
.toast-list-leave-active {
  transition: all var(--motion-fast) var(--ease-standard);
}
.toast-list-enter-from {
  opacity: 0;
  transform: translateX(100%);
}
.toast-list-leave-to {
  opacity: 0;
  transform: scale(0.8);
}
.toast-list-move {
  transition: transform var(--motion-base) var(--ease-standard);
}
```

- [ ] **Step 5: 验证**

```powershell
npm --prefix apps/desktop run test
```

- [ ] **Step 6: Commit**

```powershell
git add apps/desktop/src/modules/workspace/WorkspaceAssetRail.vue apps/desktop/src/modules/workspace/WorkspaceInspector.vue apps/desktop/src/layouts/AppShell.vue apps/desktop/src/components/ui/Toast/Toast.vue
git commit -m "feat: 补齐 Vue Transition — AssetRail / Inspector / Sidebar / Toast"
```

## Task 4: 组件 Micro-interaction（C/D 级组件）

本次任务补齐交互状态完全缺失的组件——从 D 级（Input, Select, Switch, Checkbox, Radio）到 C 级（Chip, Card, Tab, Badge, EmptyState）。

**Files:**

- Modify: `apps/desktop/src/components/ui/Input/Input.vue`
- Modify: `apps/desktop/src/components/ui/Select/Select.vue`
- Modify: `apps/desktop/src/components/ui/Switch/Switch.vue`
- Modify: `apps/desktop/src/components/ui/Checkbox/Checkbox.vue`
- Modify: `apps/desktop/src/components/ui/Radio/Radio.vue`
- Modify: `apps/desktop/src/components/ui/Chip/Chip.vue`
- Modify: `apps/desktop/src/components/ui/Card/Card.vue`
- Modify: `apps/desktop/src/components/ui/Badge/Badge.vue`
- Modify: `apps/desktop/src/components/ui/EmptyState/EmptyState.vue`

- [ ] **Step 1: Form 控件基础动效**

每个 Input/Select/Switch/Checkbox/Radio 至少：

- focus：border-color + box-shadow ring 过渡，`--motion-fast`。
- 状态切换：checked/unchecked 使用 `--motion-base` + spring easing。
- Switch knob：translateX 过渡。

```css
/* 通用 focus ring 模式 */
.input-base:focus-visible {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-soft);
  transition:
    border-color var(--motion-fast) var(--ease-standard),
    box-shadow var(--motion-fast) var(--ease-standard);
}
```

- [ ] **Step 2: Chip hover/focus/active**

- hover：背景色加深 + 轻微 scale(1.02)
- active：scale(0.98)
- 所有 transition 使用 `--motion-fast`

- [ ] **Step 3: Card hover**

- hover：box-shadow 提升 + translateY(-2px)
- transition 使用 `--motion-base` + `--ease-standard`
- card 容器本身不加 active，内部 button 由 Button 组件处理

- [ ] **Step 4: Badge count-change**

- 数字变化时触发 scale pulse（使用 `badge-count-change` keyframe）
- enter：scale(0) → scale(1) with spring

- [ ] **Step 5: EmptyState enter**

- `<transition name="empty-fade">`：
  - enter：opacity 0 → 1，translateY(12px) → 0，`--motion-slow`
  - leave：opacity 1 → 0，`--motion-fast`

- [ ] **Step 6: 验证**

```powershell
npm --prefix apps/desktop run test
```

- [ ] **Step 7: Commit**

```powershell
git add apps/desktop/src/components/ui/Input/Input.vue apps/desktop/src/components/ui/Select/Select.vue apps/desktop/src/components/ui/Switch/Switch.vue apps/desktop/src/components/ui/Checkbox/Checkbox.vue apps/desktop/src/components/ui/Radio/Radio.vue apps/desktop/src/components/ui/Chip/Chip.vue apps/desktop/src/components/ui/Card/Card.vue apps/desktop/src/components/ui/Badge/Badge.vue apps/desktop/src/components/ui/EmptyState/EmptyState.vue
git commit -m "feat: 补齐 C/D 级组件 micro-interaction 动效"
```

## Task 5: 组件 Micro-interaction（A/B 级微调）

A/B 级组件已有基本动效，本次只做微调确保使用 token 变量。

**Files:**

- Modify: `apps/desktop/src/components/ui/Button/Button.vue`（确认已 token 化，只检查不修改）
- Modify: `apps/desktop/src/components/ui/Modal/Modal.vue`（确认已 token 化）
- Modify: `apps/desktop/src/components/ui/Progress/Progress.vue`（追加 enter 动效）
- Modify: `apps/desktop/src/components/ui/Tab/Tab.vue`（追加 active indicator 过渡）

- [ ] **Step 1: Progress enter 动效**

- 进度条首次出现时宽度从 0 过渡到目标值
- transition: `width var(--motion-slow) var(--ease-decelerate)`

- [ ] **Step 2: Tab active indicator 过渡**

- Tab 选中指示器（下划线或高亮）位置切换使用 `--motion-base` + spring
- 使用 CSS `left` + `width` 过渡

- [ ] **Step 3: 验证**

```powershell
npm --prefix apps/desktop run test
```

- [ ] **Step 4: Commit**

```powershell
git add apps/desktop/src/components/ui/Progress/Progress.vue apps/desktop/src/components/ui/Tab/Tab.vue
git commit -m "feat: 微调 A/B 级组件动效 — Progress enter + Tab indicator"
```

## Task 6: Skeleton + CountUp

**Files:**

- Create: `apps/desktop/src/components/ui/Skeleton/Skeleton.vue`
- Create: `apps/desktop/src/composables/useCountUp.ts`
- Create: `apps/desktop/tests/skeleton.spec.ts`

- [ ] **Step 1: 实现 Skeleton 组件**

```vue
<template>
  <div
    class="skeleton"
    :class="[`skeleton--${variant}`, `skeleton--${size}`]"
    :style="skeletonStyle"
    aria-hidden="true"
  />
</template>
```

variants: `text`（块状行）、`circle`（圆形）、`rect`（矩形，用于图片占位）、`chip`（标签占位）。

样式使用 `skeleton-pulse` keyframe：

```css
.skeleton {
  background: var(--color-surface-2);
  border-radius: var(--radius-sm);
  animation: skeleton-pulse 1.5s var(--ease-standard) infinite;
}
.skeleton--text { height: 1em; width: 100%; }
.skeleton--circle { border-radius: 50%; }
.skeleton--rect { aspect-ratio: 16/9; }
.skeleton--chip { height: 28px; width: 60px; border-radius: var(--radius-full); }
```

- [ ] **Step 2: 实现 useCountUp composable**

```typescript
export function useCountUp(options?: {
  duration?: number;         // 默认 900ms，对齐 --motion-scene
  easing?: (t: number) => number;  // 默认 easeOutExpo
}) => {
  const value = ref(0);
  const display = ref("0");
  const isAnimating = ref(false);

  function animateTo(target: number, overrides?: { duration?: number }) {
    // requestAnimationFrame 驱动，从当前值到目标值
    // 更新 display 为格式化字符串
  }

  return { value, display, isAnimating, animateTo };
}
```

- [ ] **Step 3: 添加 skeleton 测试**

覆盖：
- 各 variant 渲染正确 className
- aria-hidden 存在
- animation CSS property 存在

- [ ] **Step 4: 验证**

```powershell
npm --prefix apps/desktop run test -- tests/skeleton.spec.ts
```

- [ ] **Step 5: Commit**

```powershell
git add apps/desktop/src/components/ui/Skeleton/Skeleton.vue apps/desktop/src/composables/useCountUp.ts apps/desktop/tests/skeleton.spec.ts
git commit -m "feat: 新增 Skeleton 组件与 useCountUp composable"
```

## Task 7: Reduced-motion 硬编码审计

**Files:**

- 无固定修改列表——由审计结果决定

- [ ] **Step 1: 硬编码 duration 审计**

```powershell
rg "transition:.*\dms" apps/desktop/src --include '*.css' --include '*.vue' -n
```

逐条检查：
- 如果是 `0.2s` / `200ms` 等接近 `--motion-fast` / `--motion-base` 的，替换为 CSS 变量。
- 如果是动效库或第三方组件的 internal transition，记录并跳过。

- [ ] **Step 2: 硬编码 animation-duration 审计**

```powershell
rg "animation.*\dms" apps/desktop/src --include '*.css' --include '*.vue' -n
```

- animation-duration 硬编码的，确保受 reduced-motion 控制（animation 在 reduced-motion 下暂停）。

```css
:root[data-reduced-motion="true"] .pulsing-element {
  animation-play-state: paused;
}
```

- [ ] **Step 3: 修正发现的硬编码**

对每条硬编码 transition：
1. 改为对应的 `--motion-*` 变量
2. 如果 100% 确定语义（全部是 fast/normal/slow），直接替换
3. 如果不确定，使用最接近的语义 token

- [ ] **Step 4: 验证**

```powershell
rg "transition:.*\dms" apps/desktop/src --include '*.css' --include '*.vue'
```

Expected: 0 条结果（确认所有 transition duration 都已 token 化）。

- [ ] **Step 5: Commit**

```powershell
git add <修正后的文件...>
git commit -m "fix: 消除硬编码 transition duration，全部使用 motion token"
```

## Task 8: 动效契约测试

**Files:**

- Create: `apps/desktop/tests/motion-contracts.spec.ts`
- Modify: `apps/desktop/tests/workspace-layout-contract.spec.ts`

- [ ] **Step 1: 创建 motion 契约测试**

覆盖：
1. 5 级速度 token 与文档一致。
2. `--motion-spinner` 保持 2-3 秒/圈，避免普通加载动效过快。
3. `--motion-spin` 保持 3 秒/圈，只用于装饰性旋转。
4. `--ease-standard` 值与文档一致。
5. `:root[data-reduced-motion="true"]` 下，一次性过渡降为 1ms，循环动效放慢或暂停。
6. 关键 keyframes 存在（`fade-in`、`skeleton-pulse` 等）。

- [ ] **Step 2: 扩展 layout contract 测试**

在已有 layout-contract 测试中加入动效相关场景：
- timeline clip 选中态 transition property 存在
- button active scale transform 存在

- [ ] **Step 3: 验证**

```powershell
npm --prefix apps/desktop run test -- tests/motion-contracts.spec.ts tests/workspace-layout-contract.spec.ts
```

- [ ] **Step 4: Commit**

```powershell
git add apps/desktop/tests/motion-contracts.spec.ts apps/desktop/tests/workspace-layout-contract.spec.ts
git commit -m "test: 动效契约测试 — token 值及 reduced-motion"
```

## Task 9: 全量回归与发布号

**Files:**

- Modify: `docs/superpowers/plans/2026-05-17-project-motion-system.md`
- Modify: `CHANGELOG.md`
- Modify: `package.json`
- Modify via `npm run version:sync`: apps/desktop/src-tauri/Cargo.toml
- Modify via `npm run version:sync`: apps/desktop/src-tauri/tauri.conf.json
- Modify via `npm run version:sync`: apps/py-runtime/pyproject.toml

- [ ] **Step 1: 全量验证**

```powershell
npm --prefix apps/desktop run test
pytest tests/runtime -q
pytest tests/contracts -q
npm --prefix apps/desktop run build
git diff --check
```

Expected:
- Desktop Vitest: 245+ 全部通过。
- Runtime pytest: 全部通过。
- Vite build: 退出 0。
- `git diff --check`：无空白错误。

- [ ] **Step 2: 硬编码零确认**

```powershell
rg "transition:.*\dms" apps/desktop/src --include '*.css' --include '*.vue'
```

Expected: 0 条结果。

- [ ] **Step 3: 更新 changelog**

添加动效体系条目，覆盖 token 拆分、keyframes 治理、Vue transition 补齐、组件 micro-interaction、Skeleton、count-up。

- [ ] **Step 4: 同步版本号**

```powershell
npm run version:sync
```

- [ ] **Step 5: Commit Task 9**

```powershell
git add CHANGELOG.md docs/superpowers/plans/2026-05-17-project-motion-system.md package.json apps/desktop/src-tauri/Cargo.toml apps/desktop/src-tauri/tauri.conf.json apps/py-runtime/pyproject.toml
git commit -m "docs: 动效体系全量回归与版本号"
```

- [ ] **Step 6: Final verify**

```powershell
git status --short --branch
git log --oneline -5
```

## Execution Policy

- 每完成一个任务，必须汇报状态、测试结果和提交 SHA。
- 每个任务提交前必须运行该任务列出的测试和 `git diff --check`。
- `.superpowers/` 与未确认的 V2 参考方案文档不纳入提交。
- 子代理可以实现独立任务；主代理必须进行范围复核、测试复核和提交复核。
- 动效改动只影响表现层，不得修改功能行为。如果发现修改涉及功能逻辑，必须拆分提交。
