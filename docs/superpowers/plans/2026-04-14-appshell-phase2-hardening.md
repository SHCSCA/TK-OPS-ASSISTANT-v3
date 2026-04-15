# AppShell Phase 2 硬化 — 窗口控制 + 状态栏 + 响应式面板

> **任务等级**：M 档（单模块，非破坏性扩展）  
> **影响范围**：`apps/desktop/src/layouts/` + `apps/desktop/src-tauri/`  
> **执行方式**：Claude 直接实施  
> **日期**：2026-04-14

---

## 一、当前状态核查（执行前已验证）

| 文件 | 当前状态 | 问题 |
|------|---------|------|
| `AppShell.vue` | `isDetailPanelOpen = ref(false)` 已存在（L82）；Detail Panel 已为全局 drawer 模式（absolute + transform） | StatusBar 未传 `runtimeStatus`；TitleBar 未传 `aiProviderLabel` |
| `ShellStatusBar.vue` | 仅 32 行，2 个裸 span，`projectLabel` prop 未渲染 | 几乎空白 |
| `ShellSidebar.vue` | `.shell-sidebar` 无显式 width；`.sidebar--collapsed` 68px | 展开宽度依赖全局 CSS |
| `shell.css` | L71 已有展开态 `width: var(--sidebar-width)` ✅；L123 折叠态 68px ❌ | 只需修复 L123 |
| `ShellTitleBar.vue` | 无 `data-tauri-drag-region`；无窗口控制按钮；无 AI chip；无 toggle-detail 发射 | 4 处缺失 |
| `tauri.conf.json` | 无 `decorations`；无 `label` 字段 | 需补充 |
| `capabilities/default.json` | 不存在 | 需新建 |

---

## 二、实施步骤（按优先级顺序）

### Step 1：ShellStatusBar.vue — 完整重建

**文件**：`apps/desktop/src/layouts/shell/ShellStatusBar.vue`

**Props 变更**：新增 `runtimeStatus` 属性（联动 pulse 颜色）。

**完整替换**（32 行 → 约 90 行）：

```vue
<template>
  <footer class="shell-status-bar" aria-label="全局状态栏">
    <!-- 左：项目上下文 -->
    <div class="status-group status-group--left">
      <span class="status-pill">
        <span class="material-symbols-outlined status-pill__icon">folder_open</span>
        <span class="status-pill__text" :title="projectLabel">{{ projectLabel }}</span>
      </span>
    </div>

    <!-- 中：Runtime 状态 + 队列占位 -->
    <div class="status-group status-group--center">
      <span class="status-pill status-pill--runtime" :class="`status-pill--${runtimeStatus}`">
        <span class="status-dot" :class="`status-dot--${runtimeStatus}`"></span>
        <span class="status-pill__text">{{ runtimeLabel }}</span>
      </span>
      <span class="status-pill status-pill--muted">
        <span class="status-pill__text">任务队列待接入</span>
      </span>
    </div>

    <!-- 右：同步时间 -->
    <div class="status-group status-group--right">
      <span class="status-pill">
        <span class="material-symbols-outlined status-pill__icon">sync</span>
        <span class="status-pill__text" :title="syncLabel">{{ syncLabel }}</span>
      </span>
    </div>
  </footer>
</template>

<script setup lang="ts">
defineProps<{
  projectLabel: string;
  runtimeLabel: string;
  runtimeStatus: 'online' | 'offline' | 'loading' | 'idle';
  syncLabel: string;
}>();
</script>

<style scoped>
.shell-status-bar {
  height: 100%;
  padding: 0 var(--space-3);
  background: var(--surface-secondary);
  border-top: 1px solid var(--border-default);
  display: flex;
  align-items: center;
  justify-content: space-between;
  user-select: none;
  font-family: var(--font-base);
  font-size: 11px;
  overflow: hidden;
}

.status-group {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-width: 0;
}

.status-pill {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: 100px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: var(--text-tertiary);
}

.status-pill--runtime {
  background: var(--surface-sunken);
}

.status-pill--muted {
  color: var(--text-tertiary);
  opacity: 0.6;
}

.status-pill__icon {
  font-size: 13px;
  flex-shrink: 0;
}

.status-pill__text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
  background: var(--text-tertiary);
  position: relative;
}

.status-dot--online {
  background: var(--status-success);
  box-shadow: 0 0 6px var(--status-success);
}

.status-dot--online::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 50%;
  background: var(--status-success);
  animation: status-pulse 2s ease-out infinite;
}

@keyframes status-pulse {
  0%   { transform: scale(1); opacity: 0.7; }
  100% { transform: scale(3); opacity: 0; }
}

.status-dot--offline {
  background: var(--status-error);
}

.status-dot--loading {
  background: var(--status-warning);
}
</style>
```

**AppShell.vue 同步修改**（`ShellStatusBar` 调用处，约 L51-55）：

```vue
<!-- 修改前 -->
<ShellStatusBar
  :project-label="projectLabel || '当前未选择项目'"
  :runtime-label="runtimeStatusLabel"
  :sync-label="lastSyncLabel"
/>

<!-- 修改后 -->
<ShellStatusBar
  :project-label="projectLabel || '当前未选择项目'"
  :runtime-label="runtimeStatusLabel"
  :runtime-status="configBusStore.runtimeStatus"
  :sync-label="lastSyncLabel"
/>
```

---

### Step 2：ShellSidebar.vue — 展开宽度声明

**文件**：`apps/desktop/src/layouts/shell/ShellSidebar.vue`

在 `.shell-sidebar` 规则中新增 `width: var(--sidebar-width);`（shell.css L71 已有全局覆盖，此处为组件内 scoped 保障）：

```css
/* 修改前 */
.shell-sidebar {
  transition: width var(--motion-base), background var(--motion-base);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  overflow-x: hidden;
  height: 100%;
}

.sidebar--collapsed {
  width: 68px !important;
}

/* 修改后 */
.shell-sidebar {
  width: var(--sidebar-width);
  transition: width var(--motion-base), background var(--motion-base);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  overflow-x: hidden;
  height: 100%;
}

.sidebar--collapsed {
  width: 64px !important;
}
```

**shell.css 同步修改**（L123）：

```css
/* 修改前 */
.sidebar--collapsed {
  width: 68px !important;
}

/* 修改后 */
.sidebar--collapsed {
  width: 64px !important;
}
```

---

### Step 3：AppShell.vue — 新增 AI Provider 派生计算

在 `runtimeStatusTone` computed 之后（约 L143），新增：

```ts
const aiProviderLabel = computed(() => {
  const provider = (configBusStore.settings as any)?.ai?.provider?.trim();
  return provider ? `AI ${provider}` : 'AI 未配置';
});
```

更新 `ShellTitleBar` 调用（约 L5-12），新增两个 prop：

```vue
<ShellTitleBar
  :runtime-tone="runtimeStatusTone"
  :runtime-status="configBusStore.runtimeStatus"
  :ai-provider-label="aiProviderLabel"
  :is-collapsed="isSidebarCollapsed"
  :project-name="projectStore.currentProject?.projectName"
  @toggle-sidebar="toggleSidebar"
  @toggle-theme="toggleTheme"
  @toggle-detail="toggleDetailPanel"
/>
```

---

### Step 4：ShellTitleBar.vue — AI chip + Detail Panel 按钮 + Tauri 窗口控制

**完整替换**（约 267 行 → 约 360 行）：

**template 修改点**：

1. `<header>` 标签添加 `data-tauri-drag-region`（按钮交互不受影响，Tauri 只对无交互区域生效）
2. 右侧动作区：AI chip 位于 Runtime 状态点左侧，之后是 Detail Panel 触发按钮，最后是窗口控制按钮

**新增 props**：
```ts
const props = defineProps<{
  runtimeTone: string;
  runtimeStatus: 'online' | 'offline' | 'loading' | 'idle';
  aiProviderLabel: string;
  isCollapsed: boolean;
  projectName?: string;
}>();

const emit = defineEmits<{
  (e: 'toggle-sidebar'): void;
  (e: 'toggle-theme'): void;
  (e: 'toggle-detail'): void;
}>();
```

**新增 Tauri 窗口控制脚本**：
```ts
import { getCurrentWindow } from '@tauri-apps/api/window';

const appWindow = getCurrentWindow();

function handleWindowError(action: string, error: unknown) {
  console.error(`窗口${action}失败`, error);
}

async function handleMinimize() {
  try { await appWindow.minimize(); } catch (e) { handleWindowError('最小化', e); }
}

async function handleToggleMaximize() {
  try { await appWindow.toggleMaximize(); } catch (e) { handleWindowError('最大化切换', e); }
}

async function handleClose() {
  try { await appWindow.close(); } catch (e) { handleWindowError('关闭', e); }
}
```

**右侧 actions 区域的新结构**（替换原有 `.shell-title-bar__actions`）：
```vue
<div class="shell-title-bar__actions">
  <!-- 通知 -->
  <button class="icon-button notification-btn" title="系统通知">
    <span class="material-symbols-outlined icon-size">notifications</span>
    <span class="notification-badge"></span>
  </button>

  <!-- 主题切换 -->
  <button class="icon-button" @click="handleToggleTheme" title="切换主题">
    <span class="material-symbols-outlined icon-size">contrast</span>
  </button>

  <div class="divider"></div>

  <!-- AI Provider chip -->
  <div class="ai-provider-chip" :class="`ai-provider-chip--${runtimeStatus}`" :title="aiProviderLabel">
    <span class="ai-chip-dot"></span>
    <span class="ai-chip-text">{{ aiProviderLabel }}</span>
  </div>

  <!-- Detail Panel 触发按钮 -->
  <button class="icon-button" @click="handleToggleDetail" title="切换属性面板">
    <span class="material-symbols-outlined icon-size">dock_to_right</span>
  </button>

  <div class="divider"></div>

  <!-- Runtime 状态点 -->
  <div class="runtime-status-container">
    <span class="runtime-dot" :class="'runtime-dot--' + runtimeTone"></span>
  </div>

  <div class="divider"></div>

  <!-- 窗口控制按钮 -->
  <div class="window-controls" aria-label="窗口控制">
    <button class="win-btn" type="button" title="最小化" @click="handleMinimize">
      <span class="material-symbols-outlined win-btn-icon">remove</span>
    </button>
    <button class="win-btn" type="button" title="最大化/还原" @click="handleToggleMaximize">
      <span class="material-symbols-outlined win-btn-icon">crop_square</span>
    </button>
    <button class="win-btn win-btn--close" type="button" title="关闭" @click="handleClose">
      <span class="material-symbols-outlined win-btn-icon">close</span>
    </button>
  </div>
</div>
```

**新增 CSS**：
```css
.ai-provider-chip {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 3px 10px;
  background: var(--surface-sunken);
  border: 1px solid var(--border-default);
  border-radius: 100px;
  font-size: 11px;
  font-weight: 700;
  color: var(--text-secondary);
  max-width: 110px;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.ai-chip-dot {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--brand-primary);
  flex-shrink: 0;
}

.ai-provider-chip--online {
  border-color: color-mix(in srgb, var(--status-success) 40%, var(--border-default));
}

.ai-provider-chip--offline {
  border-color: color-mix(in srgb, var(--status-error) 40%, var(--border-default));
  color: var(--status-error);
}

.window-controls {
  display: flex;
  align-items: center;
  gap: 2px;
  margin-left: 4px;
}

.win-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 32px;
  background: transparent;
  border: none;
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--motion-fast);
}

.win-btn:hover {
  background: var(--surface-tertiary);
  color: var(--text-primary);
}

.win-btn--close:hover {
  background: var(--status-error);
  color: #ffffff;
}

.win-btn-icon {
  font-size: 18px;
}
```

---

### Step 5：tauri.conf.json — 禁用系统装饰

在 `app.windows[0]` 对象中添加两个字段：

```json
{
  "label": "main",
  "title": "TK-OPS",
  "width": 1440,
  "height": 960,
  "resizable": true,
  "decorations": false
}
```

---

### Step 6：capabilities/default.json — 新建窗口权限

新建文件：`apps/desktop/src-tauri/capabilities/default.json`

```json
{
  "$schema": "../gen/schemas/desktop-schema.json",
  "identifier": "default",
  "description": "TK-OPS 主窗口权限",
  "windows": ["main"],
  "permissions": [
    "core:default",
    "core:window:allow-close",
    "core:window:allow-minimize",
    "core:window:allow-toggle-maximize",
    "core:window:allow-start-dragging"
  ]
}
```

> ⚠️ 若构建报 schema 路径错误，移除 `$schema` 行即可。

---

## 三、验证步骤

```bash
# 1. 构建验证
npm --prefix apps/desktop run build

# 2. 测试
npm --prefix apps/desktop run test

# 3. 启动验证
npm run app:dev
```

**手动检查清单**：
- [ ] 窗口无原生系统标题栏装饰
- [ ] 最小化/最大化/关闭按钮功能正常
- [ ] 拖拽 TitleBar 非按钮区域可移动窗口
- [ ] StatusBar 显示项目名 + Runtime 状态点 + 同步时间
- [ ] Detail Panel 按钮可触发 dock 面板开合
- [ ] Sidebar 展开 240px，折叠 64px（浏览器开发工具测量）
- [ ] AI chip 显示 Provider 名称或"AI 未配置"
- [ ] Light/Dark 主题切换正常

---

## 四、风险点

| 风险 | 处理方式 |
|------|---------|
| Vitest 中 `@tauri-apps/api/window` 导入失败 | 在测试 setup 中 mock：`vi.mock('@tauri-apps/api/window', ...)` |
| Tauri 窗口 label 不匹配 capabilities | `tauri.conf.json` 已添加 `"label": "main"` |
| `color-mix()` 兼容性 | 降级为硬编码 border color token |
| `configBusStore.settings.ai.provider` 路径不存在 | `?.` 链式访问 + fallback "AI 未配置" |
| `decorations: false` 在开发时白屏 | 确保 Vite dev server 已启动后再启动 Tauri |

---

## 五、不在本任务范围内

- Detail Panel 响应式行为（已为全局 drawer，当前实现合理）
- Sidebar 280px vs 240px token 对齐（需另开 token 对齐任务）
- StatusBar 任务队列真实数据（需 Runtime 队列 API）
- 页面级 Detail Panel 上下文感知（后续迭代）
