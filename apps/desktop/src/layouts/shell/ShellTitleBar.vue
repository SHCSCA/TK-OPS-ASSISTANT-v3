<template>
  <div class="shell-title-bar" data-tauri-drag-region>
    
    <!-- 左侧区 -->
    <div class="shell-title-bar__left" data-tauri-drag-region>
      <button
        v-if="showSidebarToggle"
        class="shell-title-bar__sidebar-toggle icon-button"
        :title="isCollapsed ? '展开侧边栏' : '收起侧边栏'"
        :aria-label="isCollapsed ? '展开侧边栏' : '收起侧边栏'"
        @click="emit('toggle-sidebar')"
      >
        <span class="material-symbols-outlined">
          {{ isCollapsed ? "menu_open" : "keyboard_double_arrow_left" }}
        </span>
      </button>

      <div class="shell-brand" data-tauri-drag-region>
        <div class="shell-brand__logo" data-tauri-drag-region></div>
        <span class="shell-brand__name" data-tauri-drag-region>TK-OPS</span>
      </div>
      
      <div class="shell-divider" data-tauri-drag-region>|</div>
      
      <div class="shell-project" data-tauri-drag-region>
        <span class="shell-project__name" :title="projectLabel" data-tauri-drag-region>
          {{ projectLabel }}
        </span>
      </div>
    </div>

    <!-- 中间区 -->
    <div class="shell-title-bar__center" data-tauri-drag-region>
      <div class="shell-search">
        <span class="material-symbols-outlined shell-search__icon">search</span>
        <input class="shell-search__input" type="text" placeholder="搜索项目 / 脚本 / 任务 / 资产" />
        <kbd class="shell-search__shortcut">Cmd+K</kbd>
      </div>
    </div>

    <!-- 右侧区 -->
    <div class="shell-title-bar__right" data-tauri-drag-region>
      <div class="shell-status-item">
        <span class="status-dot status-dot--brand"></span>
        <span class="status-text">{{ aiProviderLabel }}</span>
      </div>
      
      <div class="shell-status-item">
        <span class="status-dot" :class="`status-dot--${runtimeStatusTone}`"></span>
        <span class="status-text">{{ runtimeLabel }}</span>
      </div>

      <Chip :variant="licenseChipTone" size="sm" class="shell-license-chip">
        {{ licenseLabel }}
      </Chip>

      <div class="shell-actions">
        <button 
          class="icon-button" 
          :title="theme === 'dark' ? '切换浅色主题' : '切换深色主题'" 
          @click="emit('toggle-theme')"
        >
          <span class="material-symbols-outlined">{{ theme === 'dark' ? 'light_mode' : 'dark_mode' }}</span>
        </button>
        <button class="icon-button" title="系统设置">
          <span class="material-symbols-outlined">settings</span>
        </button>
      </div>

      <div class="shell-window-controls">
        <button class="icon-button" title="最小化" @click="handleMinimize">
          <span class="material-symbols-outlined">remove</span>
        </button>
        <button class="icon-button" title="最大化或还原" @click="handleToggleMaximize">
          <span class="material-symbols-outlined">crop_square</span>
        </button>
        <button class="icon-button window-close" title="关闭" @click="handleClose">
          <span class="material-symbols-outlined">close</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import Chip from "@/components/ui/Chip/Chip.vue";

const props = defineProps<{
  aiProviderLabel: string;
  detailOpen: boolean;
  isCollapsed: boolean;
  licenseLabel: string;
  pageTitle: string;
  projectLabel: string;
  reducedMotion: boolean;
  runtimeLabel: string;
  runtimeTone: "idle" | "loading" | "online" | "offline";
  showSidebarToggle: boolean;
  theme: "light" | "dark";
}>();

const emit = defineEmits<{
  (event: "toggle-detail"): void;
  (event: "toggle-motion"): void;
  (event: "toggle-sidebar"): void;
  (event: "toggle-theme"): void;
}>();

const runtimeStatusTone = computed(() => {
  switch (props.runtimeTone) {
    case "online":
      return "success";
    case "offline":
      return "danger";
    case "loading":
      return "warning";
    default:
      return "info";
  }
});

const licenseChipTone = computed(() => (props.licenseLabel.includes("激活") ? "brand" : "warning"));

function handleWindowError(action: string, error: unknown) {
  console.warn(`[Tauri 模拟] ${action} 未在当前环境执行。`, error);
}

async function handleMinimize() {
  try {
    const { getCurrentWindow } = await import("@tauri-apps/api/window");
    await getCurrentWindow().minimize();
  } catch (error) {
    handleWindowError("最小化", error);
  }
}

async function handleToggleMaximize() {
  try {
    const { getCurrentWindow } = await import("@tauri-apps/api/window");
    await getCurrentWindow().toggleMaximize();
  } catch (error) {
    handleWindowError("最大化切换", error);
  }
}

async function handleClose() {
  try {
    const { getCurrentWindow } = await import("@tauri-apps/api/window");
    await getCurrentWindow().close();
  } catch (error) {
    handleWindowError("关闭", error);
  }
}
</script>

<style scoped>
.shell-title-bar {
  height: var(--titlebar-height, 48px);
  background: var(--color-bg-surface);
  border-bottom: 1px solid var(--color-border-subtle);
  padding: 0 var(--space-4);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  min-width: 0;
  overflow: hidden;
  width: 100%;
  -webkit-app-region: drag;
}

/* ====================
 * 左侧区 
 * ==================== */
.shell-title-bar__left {
  display: flex;
  align-items: center;
  gap: var(--space-3); /* 12px */
  flex: 0 1 280px;
  min-width: 0;
}

.shell-title-bar__sidebar-toggle {
  display: none;
  flex: 0 0 auto;
  -webkit-app-region: no-drag;
}

.shell-brand {
  display: flex;
  align-items: center;
  flex: 0 0 auto;
  gap: var(--space-2);
}

.shell-brand__logo {
  width: 20px;
  height: 20px;
  background: var(--gradient-ai-primary);
  border-radius: var(--radius-xs);
  box-shadow: var(--shadow-glow-brand);
}

.shell-brand__name {
  font: var(--font-title-sm);
  letter-spacing: var(--ls-title-sm);
  color: var(--color-text-primary);
}

.shell-divider {
  font-size: 14px;
  line-height: 14px;
  color: var(--color-border-default);
  user-select: none;
}

.shell-project {
  flex: 1;
  min-width: 0;
}

.shell-project__name {
  display: block;
  font: var(--font-body-md);
  letter-spacing: var(--ls-body-md);
  color: var(--color-text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ====================
 * 中间区 
 * ==================== */
.shell-title-bar__center {
  flex: 1 1 260px;
  display: flex;
  justify-content: center;
  max-width: 560px;
  min-width: 160px;
}

.shell-search {
  display: flex;
  align-items: center;
  width: 100%;
  height: 32px;
  background: var(--color-bg-muted);
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  padding: 0 8px;
  gap: 8px;
  min-width: 0;
  transition: border-color var(--motion-fast) var(--ease-standard), background-color var(--motion-fast) var(--ease-standard);
  -webkit-app-region: no-drag;
}

.shell-search:focus-within {
  background: var(--color-bg-surface);
  border-color: var(--color-border-strong);
}

.shell-search__icon {
  font-size: 18px;
  color: var(--color-text-tertiary);
}

.shell-search__input {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  font: var(--font-body-md);
  letter-spacing: var(--ls-body-md);
  min-width: 0;
  color: var(--color-text-primary);
}

.shell-search__input::placeholder {
  color: var(--color-text-tertiary);
}

.shell-search__shortcut {
  font-family: var(--font-family-mono);
  font-size: 12px;
  color: var(--color-text-tertiary);
  padding: 2px 6px;
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-xs);
}

/* ====================
 * 右侧区 
 * ==================== */
.shell-title-bar__right {
  display: flex;
  align-items: center;
  flex: 0 1 auto;
  gap: var(--space-2); /* 8px */
  justify-content: flex-end;
  min-width: 0;
  overflow: hidden;
}

.shell-status-item {
  display: flex;
  align-items: center;
  flex: 0 1 auto;
  gap: 6px;
  min-width: 0;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-bg-muted);
}

.status-dot--success { background: var(--color-success); box-shadow: 0 0 8px var(--color-success); }
.status-dot--warning { background: var(--color-warning); box-shadow: 0 0 8px var(--color-warning); }
.status-dot--danger { background: var(--color-danger); box-shadow: 0 0 8px var(--color-danger); }
.status-dot--info { background: var(--color-info); }
.status-dot--brand { background: var(--color-brand-primary); box-shadow: 0 0 8px var(--color-brand-primary); }

.status-text {
  font: var(--font-caption);
  letter-spacing: var(--ls-caption);
  color: var(--color-text-secondary);
  max-width: 116px;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.shell-actions, .shell-window-controls {
  display: flex;
  align-items: center;
  flex: 0 0 auto;
  gap: 4px;
  -webkit-app-region: no-drag;
}

.shell-window-controls {
  flex: 0 0 auto;
}

.icon-button {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: transparent;
  border: none;
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: background-color var(--motion-fast) var(--ease-standard), color var(--motion-fast) var(--ease-standard);
}

.icon-button:hover {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
}

.icon-button .material-symbols-outlined {
  font-size: 18px;
}

.window-close:hover {
  background: var(--color-danger);
  color: #fff;
}

/* 适配窄屏 */
@media (max-width: 1160px) {
  .shell-title-bar__center {
    display: none;
  }
}
@media (max-width: 900px) {
  .shell-title-bar__left {
    width: auto;
  }
  .shell-divider, .shell-project {
    display: none;
  }
}
@media (max-width: 960px) {
  .shell-title-bar__sidebar-toggle {
    display: flex;
  }
}
@media (max-width: 760px) {
  .shell-status-item,
  .shell-license-chip {
    display: none;
  }
}
</style>
