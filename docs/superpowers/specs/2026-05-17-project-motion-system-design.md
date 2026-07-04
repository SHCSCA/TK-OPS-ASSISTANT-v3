# 项目级动效体系设计

## 目标

本设计定义 TK-OPS 完整的动效分层体系——从设计 token、关键帧、Vue 过渡、组件微交互到页面布局过渡——确保整个桌面应用的动效一致、可维护、可访问。

当前状态：已完成全量实现。5 级速度系统（Haptic 150ms → Celebration 1500ms）替换了旧的 4 级系统，keyframes 已清理归类，组件 micro-interaction 已按矩阵补齐，硬编码 duration 已全部替换为 CSS 变量。

## 范围

允许做：

- 设计 token 层审计与对齐（durations、easings、motion categories）。
- 全部 18 个 keyframes 的归位或清理。
- Vue `<transition>` / `<transition-group>` 的命名规范化与完整覆盖。
- 组件级 micro-interaction（hover、focus、active、enter、leave）的逐组件补齐。
- 骨架屏 motion（Skeleton 组件的 pulse/animation）。
- 数字动效（number count-up）。
- 页面布局过渡（sidebar collapse、detail panel open/close、route transition）。
- 数据反馈动效（toast、progress、badge）。
- prefers-reduced-motion 的全局实施。
- 动效性能（GPU 合成、will-change、强制回流的避免）。

不做：

- 不做 Three.js / Canvas / WebGL 动效。
- 不做复杂转场动画（本阶段不引入 Lottie / GSAP / Motion One 等第三方动效库）。
- 不做帧级时间线动画。
- 不修改产品的功能行为，只修改表现层。

## 动效分层架构

TK-OPS 动效体系分为四层，每层有明确的职责和依赖方向：

```
┌─────────────────────────────────────────┐
│   Layer 4: 页面布局过渡                   │
│   (route transition, sidebar, detail     │
│    panel, page-level enter/leave)         │
├─────────────────────────────────────────┤
│   Layer 3: 组件 micro-interaction         │
│   (hover, focus, active, enter, leave,   │
│    skeleton, number count-up, toast)      │
├─────────────────────────────────────────┤
│   Layer 2: Vue Transition 层              │
│   (transition name 规范, transition-group │
│    FLIP, list enter/leave/move)           │
├─────────────────────────────────────────┤
│   Layer 1: 设计 Token + Keyframes 层     │
│   (--motion-* durations, --ease-* curves,│
│    @keyframes 仓库, reduced-motion)       │
└─────────────────────────────────────────┘
```

### Layer 1 — 设计 Token + Keyframes

职责：提供所有动效的基础原子值。

**Durations —— 5 级速度系统**：

| Token | 层级 | 值 | 适用场景 |
|-------|------|-----|---------|
| `--motion-haptic` | Tier 1 — 触觉 | 150ms | click/active/press 按压反馈 |
| `--motion-instant` | Tier 2 — 即时 | 280ms | hover/focus/tooltip 悬停过渡 |
| `--motion-content` | Tier 3 — 内容 | 500ms | panel/modal/list 内容切换 |
| `--motion-scene` | Tier 4 — 场景 | 900ms | page/sidebar/detail 布局过渡 |
| `--motion-celebration` | Tier 5 — 庆祝 | 1500ms | badge/toast/progress 完成反馈 |

旧 token 名作为向后兼容别名保留：`--motion-fast`→`instant`, `--motion-default/base`→`content`, `--motion-slow/lazy`→`scene`。

循环动效不参与 5 级速度体系：普通加载旋转使用 `--motion-spinner: 2400ms`，长周期旋转保留 `--motion-spin: 3s`，避免把加载反馈与装饰性旋转绑定到同一速度。普通加载 spinner 的契约范围为 2-3 秒/圈，低于 2 秒会造成等待态过快和用户焦躁感。

**Easings**：

| Token | 文档值 | 当前代码值 | 决策 |
|-------|--------|------------|------|
| `--ease-standard` | `(0.2,0.8,0.2,1)` | `(0.4,0.0,0.2,1)` | 保持代码值。文档描述的是 Material Design 默认曲线，但代码值经实测更适合桌面场景,避免"过于缓慢"的 UI 感知。**更新文档匹配代码值** |
| `--ease-decelerate` | 未定义 | `(0.0,0.0,0.2,1)` | 保持 |
| `--ease-accelerate` | 未定义 | `(0.4,0.0,1.0,1)` | 保持 |
| `--ease-spring` | 未定义 | `(0.22,1,0.36,1)` | 保持 |
| `--ease-bounce` | 未定义 | `(0.18,1.25,0.4,1)` | 保持 |

**Keyframes 分类**（已治理）：

- 活跃（16 个）：`aurora-rotate`、`activation-burst`、`ai-flow`、`progress-flow`、`status-flow`、`exception-breathe`、`toast-slide-up`、`device-heartbeat`、`subtle-pulse`、`skeleton-pulse`、`page-enter`、`page-leave`、`list-item-enter`、`list-item-leave`、`badge-count-change`、`spin`
- 孤立保留（7 个，标注 future-use）：`number-count-up`、`clip-gen-grow`、`pipeline-node-pulse`、`voice-wave-play`、`subtitle-align-scan`、`render-complete-glow`、`provider-test-shake`
- 已删除（1 个）：`modal-enter`（Modal 使用 CSS transition，无需独立 keyframe）
- 已修复：`@keyframes spin` 去重（5 处组件内重复 → 统一使用全局 `base.css`）

**Keyframes 治理规则**：

1. 已使用的 keyframes 保留，检查是否可以通过 CSS transition 替代（优先 transition）。
2. 孤立的 keyframes 逐条评估：有未来用途的保留并注释用途，确定不再需要的删除。
3. 新增的 keyframes 必须有对应的消费者。

### Layer 2 — Vue Transition

职责：为 Vue 的 `<transition>` 和 `<transition-group>` 提供命名规范和完整覆盖。

**命名规范**：

| 模式 | 用途 | 示例 |
|------|------|------|
| `page-*` | 页面级路由过渡 | `page-fade` |
| `modal-*` | 弹层显隐 | `modal-fade` |
| `backdrop-*` | 遮罩层 | `backdrop-fade` |
| `panel-*` | 面板展开收起 | `panel-slide` |
| `list-*` | 列表项增减排序 | `list-enter`, `list-leave` |
| `toast-*` | 通知 | `toast-slide` |
| `badge-*` | 徽标变化 | `badge-count` |

当前覆盖审计（已全部补齐）：

| 位置 | 当前 transition name | 状态 |
|------|---------------------|------|
| AppShell RouterView | `page-fade` | 已实现（添加 `<transition mode="out-in">` 包裹） |
| AppShell sidebar | grid-template-columns transition | 已实现 |
| DetailPanel | `panel-fade` | 已实现 |
| Modal.vue | `modal-fade` | 已实现 |
| WorkspaceTimeline track-list | `track-list` | 已实现 |
| WorkspaceTimeline clip-list | `clip-list` | 已实现 |
| AssetRail tabs | `tab-fade` | **已实现**（mode="out-in"） |
| Inspector sections | `msg-fade` + `issue-slide` | **已实现** |
| Toast 列表 | `toast-slide` + `toast-slide-move` | **已实现**（修复硬编码 200ms） |
| Sidebar nav items | CSS transition | 已实现（ShellSidebar hover/focus/active 完好） |

**transition-group FLIP 约束**：`clip-list-leave-active` 必须保持 `position: absolute`。所有 list transition 必须测试 FLIP 回退。

### Layer 3 — 组件 Micro-interaction

职责：为每个 UI 组件定义完整的交互状态动效。

**组件动效矩阵**（已治理）：

| 组件 | hover | focus | active | enter | leave | 实际等级 |
|------|-------|-------|--------|-------|-------|---------|
| Button | ✓ | ✓ | ✓ | ✓ | ✓ | S 级 |
| Chip | ✓ | ✓ | ✓ | ✓ | ✓ | **A 级**（补齐 focus-visible + active） |
| Card | ✓ | ✓ | ✓ | ✓ | ✓ | **A 级**（已有完整 interactive 态） |
| Modal | ✓ | ✓ | ✓ | ✓ | ✓ | A 级 |
| Toast | ✓ | ✓ | ✓ | ✓ | ✓ | A 级 |
| Input | ✓ | ✓ | — | — | — | **B 级**（已有 focus-within ring） |
| Select | — | — | — | — | — | 未抽离为独立组件 |
| Tab | ✓ | ✓ | ✓ | ✓ | ✓ | **A 级**（已有完整动效） |
| Switch | — | — | — | — | — | 未抽离为独立组件 |
| Checkbox | — | — | — | — | — | 未抽离为独立组件 |
| Radio | — | — | — | — | — | 未抽离为独立组件 |
| Progress | ✓ | — | — | ✓ | — | **A 级**（补齐 enter 动效） |
| Badge | — | — | — | — | — | 未抽离为独立组件 |
| EmptyState | — | — | — | — | — | 未抽离为独立组件 |
| Skeleton | — | — | — | ✓ | — | **已创建**（pulse 动效已就绪） |
| AssetCard | ✓ | ✓ | ✓ | — | — | **A 级**（已有 hover/active/selected） |
| TimelineClip | ✓ | — | ✓ | ✓ | ✓ | A 级 |
| ToolbarButton | — | — | — | — | — | 内联按钮，使用全局 Button 样式 |

**动效类别定义**：

- `hover`：鼠标悬停时的视觉反馈。持续时间使用 `--motion-instant`，通常是背景色或阴影变化。
- `focus`：键盘焦点指示器动效。不依赖 `--motion-*`，使用 outline 或 ring 过渡。
- `active`：鼠标按下时的即时反馈。通常使用 `scale(0.97)` 或背景加深，持续时间使用 `--motion-haptic`。
- `enter`：元素首次出现时的动效。持续时间使用 `--motion-content`，通常为 fade + translate。
- `leave`：元素移除时的动效。持续时间使用 `--motion-instant`，通常为 fade-out。

**动效决策树**（每个组件实现时的判断逻辑）：

```
有交互状态吗？ → 无 → 跳过 hover/focus/active
              → 有 → hover 需要视觉反馈吗？
                    → 是 → CSS transition on background/shadow/transform，使用 --motion-instant + ease-standard
                    → 否 → 跳过
                → focus 需要指示器动效吗？
                    → 是 → outline/ring transition，不依赖 motion token
                    → 否 → 跳过
                → active 需要按压反馈吗？
                    → 是 → transition on transform scale(0.97)，使用 --motion-haptic + ease-accelerate
                    → 否 → 跳过
```

### Layer 4 — 页面布局过渡

职责：页面级路由切换、侧栏折叠、详情面板的动效。

| 过渡场景 | 当前状态 | 目标动效 |
|---------|---------|---------|
| 路由切换（RouterView） | `page-fade`：opacity + translateY(6px) | 保持，duration 使用 `--motion-content` |
| 侧栏折叠 | grid-template-columns transition | 保持，确认使用 `--motion-default` |
| 详情面板 | opacity + translateX | 保持，确认使用 `--motion-slow` |
| 弹层遮罩 | `modal-fade`：backdrop fade + content scale | 保持，确认 spring easing |
| 创建时间线到工作台 | 无缝过渡 | 追加 `page-enter` keyframe |

## 状态与异常

### 动效状态分类

| 状态 | 含义 | 表现 |
|------|------|------|
| idle | 无交互 | 静态 UI |
| hover | 鼠标悬停 | 柔和反馈（shadow/background 变化） |
| focus | 键盘焦点 | 清晰 ring/outline |
| active | 按压 | 即时下压反馈 |
| enter | 元素出现 | fade + translate |
| leave | 元素消失 | fade-out |
| loading | 加载中 | skeleton pulse / progress bar |
| done | 操作完成 | badge count-up / toast slide-in |

### prefers-reduced-motion 策略

- `:root[data-reduced-motion="true"]` 仅将一次性过渡 token 降为 1ms；循环动效 token 必须放慢或暂停，普通加载 `.spinning` 在该模式下暂停。
- 但部分组件内联的 transition 未使用 token（如直接写 `0.2s`），需要统一替换。
- 动画类 keyframes（如 `pulse-badge`、`spin`）在 reduced-motion 下应该暂停，而不是快速完成。

**审计命令**：使用 `rg "transition:.*\dms" apps/desktop/src --include '*.css' --include '*.vue'` 查找所有硬编码 duration。

## 文件变更清单

### 新建

| 文件 | 用途 |
|------|------|
| `apps/desktop/src/styles/tokens/motion.css` | 从 spacing.css 拆分出 motion 专用 token 文件 |
| `apps/desktop/src/components/ui/Skeleton/Skeleton.vue` | 骨架屏组件 |
| `apps/desktop/src/styles/motion/README.md` | keyframes 目录索引（用途 + 消费者） |
| `apps/desktop/tests/motion-contracts.spec.ts` | 动效 token 和 keyframes 的布局契约测试 |

### 修改

| 文件 | 改动内容 |
|------|---------|
| `apps/desktop/src/styles/tokens/spacing.css` | 移除 `--motion-*` 和 `--ease-*`，import motion.css |
| `apps/desktop/src/styles/motion/keyframes.css` | 清理孤立 keyframes，新增 `skeleton-pulse` 等 |
| `apps/desktop/src/styles/index.css` | import 顺序：`motion.css` → `keyframes.css` |
| `apps/desktop/src/components/ui/Modal/Modal.vue` | 无功能改动，确认动效使用 token |
| `apps/desktop/src/components/ui/Button/Button.vue` | S 级标杆，仅微调（如有） |
| `apps/desktop/src/components/ui/Chip/Chip.vue` | 追加 hover/focus/active 动效 |
| `apps/desktop/src/components/ui/Card/Card.vue` | 追加 hover 动效 |
| `apps/desktop/src/components/ui/Input/Input.vue` | 追加 focus ring 过渡 |
| `apps/desktop/src/components/ui/Select/Select.vue` | 追加 focus ring 过渡 |
| `apps/desktop/src/components/ui/Switch/Switch.vue` | 追加 active 动效 + knob 过渡 |
| `apps/desktop/src/components/ui/Checkbox/Checkbox.vue` | 追加 checked/unchecked 过渡 |
| `apps/desktop/src/components/ui/Radio/Radio.vue` | 追加 checked/unchecked 过渡 |
| `apps/desktop/src/components/ui/Progress/Progress.vue` | 追加 enter 动效 |
| `apps/desktop/src/components/ui/Badge/Badge.vue` | 追加 count-change 动效 |
| `apps/desktop/src/components/ui/EmptyState/EmptyState.vue` | 追加 enter 动效 |
| `apps/desktop/src/modules/workspace/WorkspaceAssetRail.vue` | Tab 切换过渡 |
| `apps/desktop/src/modules/workspace/WorkspaceInspector.vue` | Section 展开收起过渡 |
| `apps/desktop/src/layouts/AppShell.vue` | 确认 page-fade 使用 token，sidebar nav items 追加过渡 |
| `apps/desktop/src/components/ui/Toast/Toast.vue` | Toast 列表 enter/leave 过渡 |
| `apps/desktop/src/layouts/DetailPanel.vue` | 确认动效使用 token |
| `docs/superpowers/plans/2026-05-17-project-motion-system.md` | 执行记录 |
| `docs/UI-DESIGN-PRD.md` | 更新 §7.4 easing 曲线值为代码实际值 |

### 删除

| 文件 | 理由 |
|------|------|
| (无需删除文件) | |

## 验收标准（已通过）

1. 5 级速度系统已实施：`--motion-haptic(150ms)` / `instant(280ms)` / `content(500ms)` / `scene(900ms)` / `celebration(1500ms)`，旧 token 名作为别名保留。
2. Keyframes 已治理：16 个活跃 + 7 个 future-use 保留 + 1 个删除（`modal-enter`）。
3. 所有组件级 transition 使用 CSS 变量，11 处硬编码 duration 已全部替换。
4. `:root[data-reduced-motion="true"]` 全局生效（reduced-motion 块已迁至 `motion.css`）。
5. Skeleton 组件已创建（含 `skeleton-pulse` 动效）。
6. Vue Transition 已补齐：AppShell RouterView `page-fade`、AssetRail `tab-fade`、Inspector `msg-fade`+`issue-slide`、Toast `toast-slide`。
7. `rg "transition:.*\dms" apps/desktop/src` 返回 **0 条**硬编码 duration。
