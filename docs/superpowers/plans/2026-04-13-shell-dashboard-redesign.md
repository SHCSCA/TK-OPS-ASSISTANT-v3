# 壳层与创作总览视觉重做实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 基于 Stitch 设计稿（主要参考 `docs/stitch_text_document/tk_ops/`、`_12/`、`_13/`），将 TK-OPS 桌面应用的壳层（Title Bar、Sidebar、Detail Panel、Status Bar）和创作总览首页从当前粗糙状态重做为现代化、视觉精致、信息层次清晰的 UI 基线。同时修复所有页面占位组件的中文乱码问题。

**Architecture:** 纯前端改动，不涉及 Runtime / API / 数据模型变更。保持 Vue 3 + Pinia + Vue Router + CSS Variables 架构不变。样式拆分为独立文件，壳层组件按职责拆分为子组件。

**Tech Stack:** Vue 3、TypeScript、CSS Variables、设计令牌

---

## 视觉方向（从 Stitch 设计稿提取）

设计稿 `tk_ops/` 确立的视觉语言：

| 特征 | 设计稿表达 | 当前代码问题 |
|------|-----------|------------|
| **顶栏** | 紧凑 ~56px，左侧品牌+标题，中部全局搜索框，右侧头像+通知 | 118px 过高，塞了 4 个 status pill，无搜索 |
| **侧栏** | 图标+文字导航，分组标题轻量，活跃态左侧竖条+背景色 | emoji 图标，圆角 30px 过大，intro 区块多余 |
| **内容区** | 宽敞留白，卡片 12-16px 圆角，阴影克制 | 圆角 28px 过大，阴影过重 |
| **右侧面板** | 上下文信息面板（如系统状态面板、素材详情），不是调试工具 | 堆砌 5 个调试 section |
| **状态栏** | 结构化指示器，紧凑 32-36px | 4 个纯文本 span |
| **配色** | 青绿主色 `#20b2aa`，白底 `#f8fafb`，卡片 `#fff` | 渐变过多过重，视觉噪声大 |
| **首页** | 指标卡顶部（总数、趋势、ROI），趋势图中部，状态面板和活动流下方 | 创建表单 + 最近项目平铺，缺乏数据视觉 |

## 边界

- 不新增 Runtime API 或数据模型
- 不改变路由结构
- 不实现业务功能页面（脚本、分镜等保持现状）
- 不引入新的 npm 依赖（图表用 CSS 模拟或占位）
- 首启页（BootstrapGate）只做视觉微调，不重做流程
- 现有测试必须全部通过

## 文件结构

### 新建文件

| 文件 | 职责 |
|------|------|
| `apps/desktop/src/layouts/components/ShellTitleBar.vue` | 顶栏子组件 |
| `apps/desktop/src/layouts/components/ShellSidebar.vue` | 侧栏子组件 |
| `apps/desktop/src/layouts/components/ShellDetailPanel.vue` | 右侧面板子组件 |
| `apps/desktop/src/layouts/components/ShellStatusBar.vue` | 状态栏子组件 |
| `apps/desktop/src/styles/shell.css` | 壳层专用样式（从 base.css 和 shell-dashboard.css 拆出） |
| `apps/desktop/src/styles/dashboard.css` | 创作总览专用样式 |
| `apps/desktop/src/pages/dashboard/components/DashboardStatCards.vue` | 指标卡组件 |
| `apps/desktop/src/pages/dashboard/components/DashboardRecentProjects.vue` | 最近项目列表组件 |
| `apps/desktop/src/pages/dashboard/components/DashboardChainRail.vue` | 创作链路组件 |
| `apps/desktop/src/pages/dashboard/components/DashboardSystemStatus.vue` | 系统状态面板组件 |

### 修改文件

| 文件 | 改动 |
|------|------|
| `apps/desktop/src/layouts/AppShell.vue` | 拆分为子组件组合，大幅精简 |
| `apps/desktop/src/pages/dashboard/CreatorDashboardPage.vue` | 重做布局和视觉 |
| `apps/desktop/src/styles/tokens.css` | 微调设计令牌（圆角、阴影收敛） |
| `apps/desktop/src/styles/base.css` | 移除壳层/仪表盘专用样式到独立文件 |
| `apps/desktop/src/styles/shell-dashboard.css` | 删除或清空（职责已拆分） |
| `apps/desktop/src/styles/index.css` | 更新导入列表 |
| `apps/desktop/src/components/PagePlaceholderState.vue` | 确认中文正常显示 |
| 所有 `apps/desktop/src/pages/*/...Page.vue` 占位页面 | 修复 `?????` 乱码为正确中文 |

---

## 任务

### Task 1: 修复全部占位页面的中文乱码

**Files:**
- Modify: `apps/desktop/src/pages/workspace/AIEditingWorkspacePage.vue`
- Modify: `apps/desktop/src/pages/video/VideoDeconstructionCenterPage.vue`
- Modify: `apps/desktop/src/pages/voice/VoiceStudioPage.vue`
- Modify: `apps/desktop/src/pages/subtitles/SubtitleAlignmentCenterPage.vue`
- Modify: `apps/desktop/src/pages/assets/AssetLibraryPage.vue`
- Modify: `apps/desktop/src/pages/accounts/AccountManagementPage.vue`
- Modify: `apps/desktop/src/pages/devices/DeviceWorkspaceManagementPage.vue`
- Modify: `apps/desktop/src/pages/automation/AutomationConsolePage.vue`
- Modify: `apps/desktop/src/pages/publishing/PublishingCenterPage.vue`
- Modify: `apps/desktop/src/pages/renders/RenderExportCenterPage.vue`
- Modify: `apps/desktop/src/pages/review/ReviewOptimizationCenterPage.vue`

当前问题：这些占位页面的中文在文件中显示为 `?????`，可能是文件编码问题（非 UTF-8）或写入时编码损坏。

- [ ] **Step 1: 检查文件编码**

运行: `file apps/desktop/src/pages/workspace/AIEditingWorkspacePage.vue`
确认文件编码，如果非 UTF-8 需要转换。

- [ ] **Step 2: 逐个修复所有占位页面的中文文案**

每个文件需要重写为正确 UTF-8 编码的中文内容。以下是每个页面应显示的标题和描述：

| 页面 | title | description |
|------|-------|-------------|
| AIEditingWorkspacePage | AI 剪辑工作台 | 在时间线中编排视频片段、音轨、字幕，统一导出可发布的项目版本。 |
| VideoDeconstructionCenterPage | 视频拆解中心 | 导入已有视频，自动转写、切段，提取可复用的脚本与镜头结构。 |
| VoiceStudioPage | 配音中心 | 生成 TTS 配音、管理音色版本，输出与时间线对齐的音轨。 |
| SubtitleAlignmentCenterPage | 字幕对齐中心 | 自动生成字幕、校正时间码，调整样式与节奏。 |
| AssetLibraryPage | 资产中心 | 检索、管理和预览项目内的视频、图片、音频和模板资产。 |
| AccountManagementPage | 账号管理 | 管理 TikTok 账号状态与分组，服务于发布与执行闭环。 |
| DeviceWorkspaceManagementPage | 设备与工作区管理 | 管理真实 PC 工作区、浏览器实例和执行环境。 |
| AutomationConsolePage | 自动化执行中心 | 配置和监控采集、回复、同步等自动化任务队列。 |
| PublishingCenterPage | 发布中心 | 创建发布计划、执行预检、追踪发布回执。 |
| RenderExportCenterPage | 渲染与导出中心 | 管理渲染任务队列，导出可发布的视频文件。 |
| ReviewOptimizationCenterPage | 复盘与优化中心 | 回顾创作数据、异常事件，获取 AI 优化建议。 |

示例修正（AIEditingWorkspacePage.vue）：
```vue
<template>
  <PagePlaceholderState
    title="AI 剪辑工作台"
    route-id="ai_editing_workspace"
    page-type="workspace"
    description="在时间线中编排视频片段、音轨、字幕，统一导出可发布的项目版本。"
  />
</template>

<script setup lang="ts">
import PagePlaceholderState from "@/components/PagePlaceholderState.vue";
</script>
```

- [ ] **Step 3: 运行前端测试确认通过**

运行: `npm --prefix apps/desktop run test`

- [ ] **Step 4: 提交**

```bash
git add apps/desktop/src/pages/
git commit -m "fix: 修复所有占位页面的中文乱码"
```

---

### Task 2: 设计令牌收敛

**Files:**
- Modify: `apps/desktop/src/styles/tokens.css`

当前问题：圆角过大（28px）、阴影过重、渐变过多，与 Stitch 设计稿的克制风格不一致。

- [ ] **Step 1: 调整设计令牌**

```css
:root {
  /* 圆角收敛 */
  --radius-sm: 6px;    /* was 8px */
  --radius-md: 10px;   /* was 12px */
  --radius-lg: 14px;   /* was 18px */
  --radius-xl: 18px;   /* was 28px */

  /* 阴影收敛 */
  --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.06), 0 1px 2px rgba(0, 0, 0, 0.04);
  --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.08);
  --shadow-lg: 0 10px 30px rgba(0, 0, 0, 0.12);

  /* 新增 token */
  --titlebar-height: 56px;
  --sidebar-width: 240px;
  --detail-panel-width: 300px;
  --statusbar-height: 34px;
}
```

- [ ] **Step 2: 运行前端构建确认无报错**

运行: `npm --prefix apps/desktop run build`

- [ ] **Step 3: 提交**

```bash
git add apps/desktop/src/styles/tokens.css
git commit -m "refactor: 收敛设计令牌圆角和阴影"
```

---

### Task 3: 样式文件拆分

**Files:**
- Create: `apps/desktop/src/styles/shell.css`
- Create: `apps/desktop/src/styles/dashboard.css`
- Modify: `apps/desktop/src/styles/base.css`
- Modify: `apps/desktop/src/styles/shell-dashboard.css`
- Modify: `apps/desktop/src/styles/index.css`

当前问题：`base.css`（859 行）承载了全局基础、壳层、仪表盘、设置页、编辑器等所有样式，违反文件大小约束。

- [ ] **Step 1: 将壳层样式从 base.css 移到 shell.css**

提取以下选择器到 `shell.css`：
- `.app-shell` / `.title-bar` / `.brand-*` / `.sidebar` / `.nav-*` / `.detail-panel` / `.status-bar` / `.status-pill` / `.content-host` 等壳层相关样式
- `.bootstrap-screen*` 首启页样式

- [ ] **Step 2: 将仪表盘样式从 base.css 移到 dashboard.css**

提取以下选择器到 `dashboard.css`：
- `.dashboard-*` / `.command-panel` / `.chain-*` / `.empty-state` 等仪表盘相关样式

- [ ] **Step 3: 清空 shell-dashboard.css 并移除**

`shell-dashboard.css` 的职责已被 `shell.css` + `dashboard.css` 替代。

- [ ] **Step 4: 更新 index.css 导入**

```css
@import "./tokens.css";
@import "./base.css";
@import "./shell.css";
@import "./dashboard.css";
```

- [ ] **Step 5: base.css 只保留全局基础样式**

保留内容：reset、body、typography、通用组件（`.settings-field`、`.settings-page__button` 等）、媒体查询中与壳层无关的部分。

目标：`base.css` 降到 ~250 行，`shell.css` ~200 行，`dashboard.css` ~150 行。

- [ ] **Step 6: 运行前端构建和测试确认通过**

运行:
```bash
npm --prefix apps/desktop run build
npm --prefix apps/desktop run test
```

- [ ] **Step 7: 提交**

```bash
git add apps/desktop/src/styles/
git commit -m "refactor: 拆分壳层和仪表盘样式为独立文件"
```

---

### Task 4: 壳层子组件拆分

**Files:**
- Create: `apps/desktop/src/layouts/components/ShellTitleBar.vue`
- Create: `apps/desktop/src/layouts/components/ShellSidebar.vue`
- Create: `apps/desktop/src/layouts/components/ShellDetailPanel.vue`
- Create: `apps/desktop/src/layouts/components/ShellStatusBar.vue`
- Modify: `apps/desktop/src/layouts/AppShell.vue`

当前问题：`AppShell.vue` 有 269 行，模板和逻辑混在一起。拆分为四个子组件后，每个 < 100 行。

- [ ] **Step 1: 提取 ShellTitleBar.vue**

从 `AppShell.vue` 的 `<header class="title-bar">` 提取，接收 props：
```typescript
defineProps<{
  pageTitle: string;
  runtimeStatus: string;
  configStatus: string;
  licenseActive: boolean;
  projectName: string;
}>();
```

- [ ] **Step 2: 提取 ShellSidebar.vue**

从 `AppShell.vue` 的 `<aside class="sidebar">` 提取，接收 props：
```typescript
defineProps<{
  navGroups: Array<{ label: string; items: Array<{ id: string; path: string; title: string; icon: string }> }>;
}>();
```

- [ ] **Step 3: 提取 ShellDetailPanel.vue**

从 `AppShell.vue` 的 `<aside class="detail-panel">` 提取。

- [ ] **Step 4: 提取 ShellStatusBar.vue**

从 `AppShell.vue` 的 `<footer class="status-bar">` 提取。

- [ ] **Step 5: 重组 AppShell.vue**

```vue
<template>
  <div class="app-shell">
    <ShellTitleBar v-bind="titleBarProps" />
    <div class="app-shell__body" :class="{ 'app-shell__body--wizard': isWizardPage }">
      <ShellSidebar v-if="showWorkspaceChrome" :nav-groups="navGroups" />
      <main class="content-host">
        <RouterView />
      </main>
      <ShellDetailPanel v-if="showWorkspaceChrome" v-bind="detailPanelProps" />
    </div>
    <ShellStatusBar v-bind="statusBarProps" />
  </div>
</template>
```

- [ ] **Step 6: 运行前端测试确认通过**
- [ ] **Step 7: 提交**

```bash
git add apps/desktop/src/layouts/
git commit -m "refactor: 壳层拆分为 TitleBar/Sidebar/DetailPanel/StatusBar 子组件"
```

---

### Task 5: 壳层视觉重做（Stitch → Gemini → Claude）

**Files:**
- Modify: `apps/desktop/src/layouts/components/ShellTitleBar.vue`
- Modify: `apps/desktop/src/layouts/components/ShellSidebar.vue`
- Modify: `apps/desktop/src/layouts/components/ShellDetailPanel.vue`
- Modify: `apps/desktop/src/layouts/components/ShellStatusBar.vue`
- Modify: `apps/desktop/src/styles/shell.css`

参考设计稿：`docs/stitch_text_document/tk_ops/screen.png`

#### 5a: Title Bar 重做

- [ ] **Step 1: 编写 component spec**

设计目标（基于 `tk_ops/` 设计稿顶栏）：
- 高度固定 56px，不再随内容撑高
- 左侧：品牌 Logo（32x32 圆角方块）+ "TK-OPS" 文字
- 中部：全局搜索框（圆角输入框，placeholder "搜索项目、脚本、资产…"），当前不接数据，纯 UI
- 右侧：Runtime 状态小圆点（绿/黄/红）+ 当前用户名/头像占位
- 移除 4 个 status pill，状态信息下沉到 Status Bar
- 背景：纯白 + 底部 1px 边线，去掉半透明模糊

- [ ] **Step 2: 指派 Gemini 实现**

```bash
/ask gemini "基于以下 spec 重做 ShellTitleBar.vue：
- 高度固定 56px
- 左侧：32x32 品牌方块（背景 var(--brand-primary)，白色 TK 文字）+ 'TK-OPS' 文字标题
- 中部：圆角搜索输入框，placeholder '搜索项目、脚本、资产…'，暂不接数据
- 右侧：Runtime 状态圆点（8px，绿=online/黄=loading/红=offline）+ 'Administrator' 文字
- 背景：var(--surface-secondary)，底部 1px solid var(--border-default)
- 无 blur 效果，无 status pill
参考设计稿：docs/stitch_text_document/tk_ops/screen.png
涉及文件：apps/desktop/src/layouts/components/ShellTitleBar.vue，apps/desktop/src/styles/shell.css"
```

- [ ] **Step 3: Claude 样式校准**

对照设计稿 `tk_ops/screen.png` 顶栏区域，校准间距、字号、颜色。

#### 5b: Sidebar 重做

- [ ] **Step 4: 编写 component spec**

设计目标（基于 `tk_ops/` 设计稿侧栏）：
- 宽度 240px，背景纯白，无圆角（或极小 0-4px）
- 移除 `sidebar__intro` 渐变区块
- 导航项：左侧图标（16x16 SVG 或 emoji）+ 文字，行高 40px
- 活跃态：左侧 3px 竖条（品牌色）+ 浅品牌色背景
- 分组标题：12px 灰色大写字母，上方 16px 间距
- 底部可放"系统设置"固定入口

- [ ] **Step 5: 指派 Gemini 实现**
- [ ] **Step 6: Claude 样式校准**

#### 5c: Detail Panel 重做

- [ ] **Step 7: 编写 component spec**

设计目标（基于 `tk_ops/` 设计稿右侧面板 "System Status Panel"）：
- 宽度 300px
- 只展示两个 section：
  1. **系统状态**：Runtime（在线/离线）、许可证（已激活/需授权）、配置（就绪/异常），每项一行，带状态圆点
  2. **项目上下文**：当前项目名、状态、脚本版本、分镜版本；无项目时空态提示
- 移除：诊断信息 section、最近错误 section（这些属于 AI 与系统设置页面）
- 视觉：卡片圆角 10px，无过重阴影

- [ ] **Step 8: 指派 Gemini 实现**
- [ ] **Step 9: Claude 样式校准**

#### 5d: Status Bar 重做

- [ ] **Step 10: 编写 component spec**

设计目标：
- 高度 34px，背景 `var(--surface-secondary)`，顶部 1px 边线
- 左侧：Runtime 在线状态文字 + 版本号
- 中部：当前项目名（无项目时"未选择项目"）
- 右侧：最近同步时间
- 字号 12px，颜色 `var(--text-tertiary)`

- [ ] **Step 11: 指派 Gemini 实现**
- [ ] **Step 12: Claude 样式校准**

- [ ] **Step 13: 运行前端测试确认通过**
- [ ] **Step 14: 提交**

```bash
git add apps/desktop/src/layouts/ apps/desktop/src/styles/shell.css
git commit -m "feat: 壳层视觉重做——对齐 Stitch 设计稿"
```

---

### Task 6: 创作总览首页拆分为子组件

**Files:**
- Create: `apps/desktop/src/pages/dashboard/components/DashboardStatCards.vue`
- Create: `apps/desktop/src/pages/dashboard/components/DashboardRecentProjects.vue`
- Create: `apps/desktop/src/pages/dashboard/components/DashboardChainRail.vue`
- Create: `apps/desktop/src/pages/dashboard/components/DashboardSystemStatus.vue`
- Modify: `apps/desktop/src/pages/dashboard/CreatorDashboardPage.vue`

当前 `CreatorDashboardPage.vue` 有 297 行。拆分后根组件 < 80 行。

- [ ] **Step 1: 提取 DashboardStatCards.vue**

顶部指标卡区域。当前没有真实统计数据，展示空态/引导态：
- 总项目数（从 `projectStore.recentProjects.length` 读取）
- 总脚本数（显示"待接入"）
- AI 调用数（显示"待接入"）
- 系统状态（从 configBusStore 读取）

- [ ] **Step 2: 提取 DashboardRecentProjects.vue**

最近项目列表 + 创建新项目入口。保留现有 `handleCreateProject` 和 `handleSelectProject` 逻辑。

- [ ] **Step 3: 提取 DashboardChainRail.vue**

创作链路步骤条。保留现有 `chainSteps` 数据。

- [ ] **Step 4: 提取 DashboardSystemStatus.vue**

运行与授权 + AI 默认项。合并为一个系统状态卡片。

- [ ] **Step 5: 重组 CreatorDashboardPage.vue**

```vue
<template>
  <section class="dashboard-page">
    <DashboardStatCards />
    <div class="dashboard-grid">
      <DashboardRecentProjects />
      <DashboardSystemStatus />
    </div>
    <DashboardChainRail />
  </section>
</template>
```

- [ ] **Step 6: 运行前端测试确认通过**
- [ ] **Step 7: 提交**

```bash
git add apps/desktop/src/pages/dashboard/
git commit -m "refactor: 创作总览拆分为子组件"
```

---

### Task 7: 创作总览视觉重做（Stitch → Gemini → Claude）

**Files:**
- Modify: `apps/desktop/src/pages/dashboard/components/DashboardStatCards.vue`
- Modify: `apps/desktop/src/pages/dashboard/components/DashboardRecentProjects.vue`
- Modify: `apps/desktop/src/pages/dashboard/components/DashboardChainRail.vue`
- Modify: `apps/desktop/src/pages/dashboard/components/DashboardSystemStatus.vue`
- Modify: `apps/desktop/src/pages/dashboard/CreatorDashboardPage.vue`
- Modify: `apps/desktop/src/styles/dashboard.css`

参考设计稿：`docs/stitch_text_document/tk_ops/screen.png`

- [ ] **Step 1: 编写 component spec**

设计目标（基于 `tk_ops/` 设计稿主内容区）：

**布局**：
```
[概览数据看板 标题]
[指标卡1] [指标卡2] [指标卡3] [指标卡4]    ← 顶部 4 列指标
[趋势区域（占位）          ] [系统状态面板  ]  ← 中部 2 列
[最近项目活动列表                           ]  ← 底部全宽
```

**指标卡**（DashboardStatCards）：
- 4 个等宽卡片，一行排列
- 每个卡片：标签（灰色小字）+ 数值（大号粗体）+ 变化趋势（绿涨/红跌百分比）
- 卡片 1：总项目数（真实数据）
- 卡片 2-4：真实数据不可用时显示"—"和"待接入"

**系统状态面板**（DashboardSystemStatus）：
- 标题 "System Status Panel" 改为 "系统状态"
- 列表形式：名称 + 状态标签（Active/Inactive）
- 项目：Runtime 引擎、AI 文本生成、许可证授权

**最近项目**（DashboardRecentProjects）：
- 表格形式：项目名 + 描述 + 状态 + 最近访问时间
- 带"创建新项目"按钮
- 空态：虚线边框 + 引导文案

**创作链路**（DashboardChainRail）：
- 保持 4 步横向卡片，但视觉更紧凑
- 每步：序号 + 标题 + 一行描述

- [ ] **Step 2: 指派 Gemini 实现**

```bash
/ask gemini "基于以下 spec 重做创作总览首页的四个子组件。
参考设计稿：docs/stitch_text_document/tk_ops/screen.png
整体布局：页面标题'概览数据看板' + 副标题 → 4列指标卡 → 中部2列(左侧趋势占位+右侧系统状态) → 底部最近项目列表 → 创作链路
所有组件使用 CSS Variables，不引入新依赖。
涉及文件：
- apps/desktop/src/pages/dashboard/components/DashboardStatCards.vue
- apps/desktop/src/pages/dashboard/components/DashboardRecentProjects.vue
- apps/desktop/src/pages/dashboard/components/DashboardChainRail.vue
- apps/desktop/src/pages/dashboard/components/DashboardSystemStatus.vue
- apps/desktop/src/pages/dashboard/CreatorDashboardPage.vue
- apps/desktop/src/styles/dashboard.css"
```

- [ ] **Step 3: Claude 样式校准**

对照 `tk_ops/screen.png`，逐区域校准：
1. 指标卡的间距、字号、数字大小
2. 系统状态面板的行高、状态标签颜色
3. 项目列表的行距、操作按钮
4. 全局留白和卡片间距

- [ ] **Step 4: 移除旧样式**

清理 `dashboard.css` 中的旧选择器：`.command-signal`、`.dashboard-hero__orb`、`.command-dashboard__hero::after` 等。

- [ ] **Step 5: 运行前端测试确认通过**
- [ ] **Step 6: 提交**

```bash
git add apps/desktop/src/pages/dashboard/ apps/desktop/src/styles/dashboard.css
git commit -m "feat: 创作总览视觉重做——对齐 Stitch 设计稿"
```

---

### Task 8: 首启页视觉微调

**Files:**
- Modify: `apps/desktop/src/bootstrap/BootstrapLoadingScreen.vue`
- Modify: `apps/desktop/src/bootstrap/BootstrapLicenseScreen.vue`
- Modify: `apps/desktop/src/bootstrap/BootstrapInitializationScreen.vue`

参考设计稿：`docs/stitch_text_document/_12/screen.png`（配置向导步骤条风格）

- [ ] **Step 1: 微调首启页视觉**

不重做流程，只调整：
- 圆角与阴影对齐新 token
- 渐变收敛（减少 radial-gradient 叠加层数）
- 按钮样式对齐主应用

- [ ] **Step 2: 指派 Gemini 实现微调**
- [ ] **Step 3: Claude 样式校准**
- [ ] **Step 4: 运行前端测试确认通过**
- [ ] **Step 5: 提交**

```bash
git add apps/desktop/src/bootstrap/ apps/desktop/src/styles/
git commit -m "fix: 首启页视觉对齐新设计令牌"
```

---

### Task 9: 端到端验证与清理

- [ ] **Step 1: 运行全部测试**

```bash
npm --prefix apps/desktop run test
```

- [ ] **Step 2: 运行前端构建确认无报错**

```bash
npm --prefix apps/desktop run build
```

- [ ] **Step 3: 一键启动验证**

运行: `npm run app:dev`

验证清单：
1. 首启页三个阶段视觉正常，中文显示正确
2. 壳层顶栏紧凑，56px 高度
3. 侧栏导航 16 个页面可点击，活跃态有竖条
4. 右侧面板展示系统状态和项目上下文
5. 状态栏紧凑，信息清晰
6. 创作总览首页指标卡、项目列表、系统状态面板布局正确
7. 创建项目 → 打开项目 → 跳转脚本中心链路正常
8. 所有占位页面中文正常显示
9. 窗口缩小到 960px 时响应式布局正常
10. Dark 模式（如已实现切换）视觉可接受

- [ ] **Step 4: 清理无用样式选择器**

删除 `base.css` 和 `shell.css` 中不再被任何组件引用的选择器。

- [ ] **Step 5: 提交**

```bash
git add -A
git commit -m "chore: 壳层与首页重做最终验证和样式清理"
```
