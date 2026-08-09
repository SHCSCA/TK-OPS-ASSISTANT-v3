# Superdesign 可抽取组件目录

> 2026-07-19 原型覆盖：当前 React 原型已具有稳定壳层，设计草稿优先把 `Brand`、`AppSidebar`、`AccountSwitcher`、`TopBar`、`DetailPanel` 和 `PageSection` 作为可复用布局模式；基础按钮、状态标签、表格和表单继续内联，不为本轮创建重复组件体系。

本目录用于在创建草稿前选择可复用 DraftComponent。优先抽取布局组件；基础原语在草稿中以内联 HTML 表达。

## Layout Components

### TkopsBrandMark
- Source: `apps/desktop/src/components/brand/TkopsBrandMark.vue`
- Category: layout
- Description: TK-OPS 真实品牌标记。
- Extractable props: 无。
- Hardcoded: SVG path、品牌色变量、图形比例与样式。

### ShellTitleBar
- Source: `apps/desktop/src/layouts/shell/ShellTitleBar.vue`
- Category: layout
- Description: 全局标题栏，包含品牌、项目 / 页面上下文、Runtime / AI / 许可状态和窗口控制。
- Extractable props: detailOpen (boolean, default: true), isCollapsed (boolean, default: false), reducedMotion (boolean, default: false), showDetailToggle (boolean, default: true), showSidebarToggle (boolean, default: true), theme (string, default: "dark")
- Hardcoded: TK-OPS 标记、示例项目与页面文案、Material Symbols 图标、所有 CSS、窗口操作图标。

### ShellSidebar
- Source: `apps/desktop/src/layouts/shell/ShellSidebar.vue`
- Category: layout
- Description: 五组正式导航、当前项目与折叠控制。
- Extractable props: activeItem (string, default: "ai_editing_workspace"), isCollapsed (boolean, default: false), hasProject (boolean, default: true), dashboardHref (string, default: "#dashboard"), workspaceHref (string, default: "#workspace"), settingsHref (string, default: "#settings")
- Hardcoded: 五组导航名称、16 页标签、Material Symbols 图标、品牌区、所有 CSS。

### ShellDetailPanel
- Source: `apps/desktop/src/layouts/shell/ShellDetailPanel.vue`
- Category: layout
- Description: 详情、属性、资产、绑定、日志和系统诊断的上下文面板。
- Extractable props: open (boolean, default: true), currentTab (string, default: "contextual")
- Hardcoded: 详情标签、关闭图标、默认上下文内容、所有 CSS。

### ShellStatusBar
- Source: `apps/desktop/src/layouts/shell/ShellStatusBar.vue`
- Category: layout
- Description: Runtime、AI、项目、同步、运行任务和队列的持续反馈条。
- Extractable props: detailOpen (boolean, default: true), runtimeStatus (string, default: "online"), runningTaskCount (number, default: 1), queuedTaskCount (number, default: 2)
- Hardcoded: 示例状态文案、状态图标、页面模式标签、所有 CSS。

### AppShell
- Source: `apps/desktop/src/layouts/AppShell.vue`
- Category: layout
- Description: Title Bar + Sidebar + Content Host + Detail Panel + Status Bar 的桌面壳。
- Extractable props: isSidebarCollapsed (boolean, default: false), isDetailOpen (boolean, default: true), theme (string, default: "dark")
- Hardcoded: 壳层栅格、响应式断点、过渡、页面容器与品牌位置。

### ProjectContextGuard
- Source: `apps/desktop/src/components/common/ProjectContextGuard.vue`
- Category: layout
- Description: 项目上下文缺失时展示统一恢复引导。
- Extractable props: hasProject (boolean, default: true), dashboardHref (string, default: "#dashboard")
- Hardcoded: 空态图标、中文原因与动作标签、所有 CSS。

## Basic Components

### Button
- Source: `apps/desktop/src/components/ui/Button/Button.vue`
- Category: basic
- Description: 主、次、AI、危险与幽灵按钮。
- Extractable props: isActive (boolean, default: false), isRunning (boolean, default: false), isDisabled (boolean, default: false)
- Hardcoded: 图标、按钮示例文案、尺寸、变体与所有 CSS。

### Card
- Source: `apps/desktop/src/components/ui/Card/Card.vue`
- Category: basic
- Description: 统一内容卡片。
- Extractable props: isActive (boolean, default: false)
- Hardcoded: 卡片结构、示例内容与所有 CSS。

### Chip
- Source: `apps/desktop/src/components/ui/Chip/Chip.vue`
- Category: basic
- Description: 状态、筛选和语义标签。
- Extractable props: isActive (boolean, default: false), showBadge (boolean, default: true), badgeCount (number, default: 1)
- Hardcoded: 状态标签示例、图标与所有 CSS。

### Input
- Source: `apps/desktop/src/components/ui/Input/Input.vue`
- Category: basic
- Description: 带标签、错误和辅助信息的输入控件。
- Extractable props: isDisabled (boolean, default: false), showError (boolean, default: false)
- Hardcoded: 示例标签、占位文案、图标与所有 CSS。

### Tab
- Source: `apps/desktop/src/components/ui/Tab/Tab.vue`
- Category: basic
- Description: 页内模式与版本切换标签。
- Extractable props: currentTab (string, default: "overview"), showBadge (boolean, default: true), badgeCount (number, default: 2)
- Hardcoded: 标签文案、图标与所有 CSS。

### Modal
- Source: `apps/desktop/src/components/ui/Modal/Modal.vue`
- Category: basic
- Description: 确认、高风险动作和表单浮层。
- Extractable props: isOpen (boolean, default: true), showClose (boolean, default: true)
- Hardcoded: 标题、说明、按钮、遮罩与所有 CSS。

### EmptyState
- Source: `apps/desktop/src/components/common/EmptyState.vue`
- Category: basic
- Description: 空、警告和错误状态的统一下一步引导。
- Extractable props: showAction (boolean, default: true), actionHref (string, default: "#")
- Hardcoded: 示例图标、中文标题、说明、动作标签与所有 CSS。

## 抽取顺序

1. TkopsBrandMark
2. ShellTitleBar
3. ShellSidebar
4. ShellDetailPanel
5. ShellStatusBar
6. ProjectContextGuard

Button、Card、Chip、Input、Tab、Modal 与 EmptyState 不创建 DraftComponent，设计草稿内联实现。
