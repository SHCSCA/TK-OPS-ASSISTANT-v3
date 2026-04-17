<template>
  <div class="shell-title-bar" data-tauri-drag-region>
    <div class="shell-title-bar__left" data-tauri-drag-region>
      <button
        aria-label="切换侧边栏"
        class="shell-title-bar__icon-button"
        type="button"
        @click="emit('toggle-sidebar')"
      >
        <span class="material-symbols-outlined">{{ isCollapsed ? "menu_open" : "menu" }}</span>
      </button>

      <div class="shell-brand" data-tauri-drag-region>
        <div class="shell-brand__mark" data-tauri-drag-region>TK</div>
        <div class="shell-brand__copy" data-tauri-drag-region>
          <strong data-tauri-drag-region>TK-OPS</strong>
          <span data-tauri-drag-region>本地 AI 视频创作中枢</span>
        </div>
      </div>

      <div class="shell-title-bar__project" data-tauri-drag-region>
        <span class="shell-title-bar__project-label" data-tauri-drag-region>{{ pageTitle }}</span>
        <strong data-tauri-drag-region>{{ projectLabel }}</strong>
      </div>
    </div>

    <div class="shell-title-bar__search">
      <Input v-model="searchKeyword" placeholder="搜索项目 / 脚本 / 任务 / 资产">
        <template #leading>
          <span class="material-symbols-outlined">search</span>
        </template>
        <template #trailing>
          <kbd class="shell-title-bar__shortcut">Cmd+K</kbd>
        </template>
      </Input>
    </div>

    <div class="shell-title-bar__actions">
      <Chip :tone="runtimeChipTone" size="sm">
        <template #leading>
          <span class="material-symbols-outlined">memory</span>
        </template>
        {{ runtimeLabel }}
      </Chip>

      <Chip :tone="licenseChipTone" size="sm">
        <template #leading>
          <span class="material-symbols-outlined">verified</span>
        </template>
        {{ licenseLabel }}
      </Chip>

      <Chip tone="neutral" size="sm">
        <template #leading>
          <span class="material-symbols-outlined">auto_awesome</span>
        </template>
        {{ aiProviderLabel }}
      </Chip>

      <button
        :aria-pressed="detailOpen"
        aria-label="切换详情面板"
        class="shell-title-bar__icon-button"
        title="切换属性面板"
        type="button"
        @click="emit('toggle-detail')"
      >
        <span class="material-symbols-outlined">right_panel_open</span>
      </button>

      <button
        :aria-pressed="reducedMotion"
        aria-label="切换减弱动效"
        class="shell-title-bar__icon-button"
        type="button"
        @click="emit('toggle-motion')"
      >
        <span class="material-symbols-outlined">{{ reducedMotion ? "motion_photos_off" : "animation" }}</span>
      </button>

      <button
        :aria-label="theme === 'dark' ? '切换浅色主题' : '切换深色主题'"
        class="shell-title-bar__icon-button"
        type="button"
        @click="emit('toggle-theme')"
      >
        <span class="material-symbols-outlined">{{ theme === "dark" ? "light_mode" : "dark_mode" }}</span>
      </button>

      <div class="shell-window-controls" aria-label="窗口控制">
        <button class="shell-window-controls__button" title="最小化" type="button" @click="handleMinimize">
          <span class="material-symbols-outlined">remove</span>
        </button>
        <button class="shell-window-controls__button" title="最大化或还原" type="button" @click="handleToggleMaximize">
          <span class="material-symbols-outlined">crop_square</span>
        </button>
        <button class="shell-window-controls__button shell-window-controls__button--close" title="关闭" type="button" @click="handleClose">
          <span class="material-symbols-outlined">close</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";

import Chip from "@/components/ui/Chip/Chip.vue";
import Input from "@/components/ui/Input/Input.vue";

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
  theme: "light" | "dark";
}>();

const emit = defineEmits<{
  (event: "toggle-detail"): void;
  (event: "toggle-motion"): void;
  (event: "toggle-sidebar"): void;
  (event: "toggle-theme"): void;
}>();

const searchKeyword = ref("");

const runtimeChipTone = computed(() => {
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
  align-items: center;
  background: var(--color-bg-surface);
  display: grid;
  gap: var(--space-4);
  grid-template-columns: auto minmax(280px, 1fr) auto;
  height: 100%;
  min-width: 0;
  padding: 0 var(--space-4);
}

.shell-title-bar__left,
.shell-title-bar__actions {
  align-items: center;
  display: flex;
  gap: var(--space-3);
  min-width: 0;
}

.shell-title-bar__search {
  min-width: 0;
}

.shell-brand {
  align-items: center;
  display: flex;
  gap: 10px;
  min-width: 0;
}

.shell-brand__mark {
  align-items: center;
  background: var(--gradient-ai-primary);
  border-radius: var(--radius-sm);
  box-shadow: var(--shadow-glow-brand);
  color: var(--color-text-on-brand);
  display: inline-flex;
  font-size: 12px;
  font-weight: 700;
  height: 24px;
  justify-content: center;
  width: 24px;
}

.shell-brand__copy {
  display: grid;
  gap: 2px;
}

.shell-brand__copy strong {
  font-size: var(--font-title-sm);
  line-height: 1;
}

.shell-brand__copy span,
.shell-title-bar__project-label,
.shell-title-bar__shortcut {
  color: var(--color-text-tertiary);
  font-size: var(--font-caption);
}

.shell-title-bar__project {
  border-left: 1px solid var(--color-border-subtle);
  display: grid;
  gap: 2px;
  min-width: 0;
  padding-left: var(--space-3);
}

.shell-title-bar__project strong {
  font-size: var(--font-body-sm);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.shell-title-bar__icon-button,
.shell-window-controls__button {
  align-items: center;
  appearance: none;
  background: transparent;
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  cursor: pointer;
  display: inline-flex;
  height: 32px;
  justify-content: center;
  transition:
    background-color var(--motion-fast) var(--ease-standard),
    color var(--motion-fast) var(--ease-standard),
    border-color var(--motion-fast) var(--ease-standard),
    transform var(--motion-instant) var(--ease-bounce);
  width: 32px;
}

.shell-title-bar__icon-button:hover,
.shell-window-controls__button:hover {
  background: var(--color-bg-hover);
  border-color: var(--color-border-subtle);
  color: var(--color-text-primary);
}

.shell-title-bar__icon-button:active,
.shell-window-controls__button:active {
  transform: scale(0.98);
}

.shell-title-bar__icon-button:focus-visible,
.shell-window-controls__button:focus-visible {
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--color-brand-primary) 20%, transparent);
  outline: none;
}

.shell-title-bar__shortcut {
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-xs);
  font-family: var(--font-family-mono);
  line-height: 1;
  padding: 3px 6px;
}

.shell-window-controls {
  align-items: center;
  border-left: 1px solid var(--color-border-subtle);
  display: flex;
  gap: 4px;
  margin-left: var(--space-1);
  padding-left: var(--space-3);
}

.shell-window-controls__button--close:hover {
  background: var(--color-danger);
  border-color: var(--color-danger);
  color: var(--color-text-on-brand);
}

@media (max-width: 1320px) {
  .shell-title-bar {
    grid-template-columns: auto minmax(220px, 1fr) auto;
  }
}

@media (max-width: 1160px) {
  .shell-title-bar {
    grid-template-columns: minmax(0, 1fr) auto;
  }

  .shell-title-bar__search {
    display: none;
  }
}

@media (max-width: 900px) {
  .shell-title-bar__project,
  .shell-title-bar__actions :deep(.ui-chip:nth-of-type(3)) {
    display: none;
  }
}

@media (max-width: 760px) {
  .shell-brand__copy span,
  .shell-title-bar__actions :deep(.ui-chip) {
    display: none;
  }
}
</style>
