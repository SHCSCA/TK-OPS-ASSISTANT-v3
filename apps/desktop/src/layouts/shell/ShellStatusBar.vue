<template>
  <div class="shell-status-bar" :data-has-running-task="String(hasRunningTask)">
    
    <div class="shell-status-bar__left">
      <div class="status-item">
        <span class="status-dot" :class="`status-dot--${runtimeTone}`"></span>
        <span>{{ runtimeLabel }}</span>
      </div>
      
      <div class="status-item">
        <span class="material-symbols-outlined">queue</span>
        <span>{{ runningTasksCount }} 运行中 / {{ queuedTasksCount }} 排队</span>
      </div>

      <div class="status-item">
        <span class="material-symbols-outlined">auto_awesome</span>
        <span>{{ aiProviderLabel }} · {{ aiLatency }}</span>
      </div>
    </div>

    <div class="shell-status-bar__right">
      <span class="status-item">{{ syncLabel }}</span>
      <span class="status-item">主题 · {{ themeLabel }}</span>
      <button class="status-icon-btn" title="快捷打开日志" @click="openLogs">
        <span class="material-symbols-outlined">receipt_long</span>
      </button>
    </div>
    
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useShellUiStore } from "@/stores/shell-ui";
import { useTaskBusStore } from "@/stores/task-bus";

const props = defineProps<{
  aiProviderLabel: string;
  detailOpen: boolean;
  mode: string;
  pageTitle: string;
  pageType: string;
  projectLabel: string;
  runtimeLabel: string;
  runtimeStatus: "online" | "offline" | "loading" | "idle";
  runtimeTone: string;
  syncLabel: string;
}>();

const shellUiStore = useShellUiStore();
const taskBusStore = useTaskBusStore();

const themeLabel = computed(() => shellUiStore.theme === 'dark' ? 'Dark' : 'Light');

const runningTasksCount = computed(() => {
  let count = 0;
  taskBusStore.tasks.forEach((task) => {
    if (task.status === "running" || task.status === "processing") {
      count++;
    }
  });
  return count;
});

const queuedTasksCount = computed(() => {
  let count = 0;
  taskBusStore.tasks.forEach((task) => {
    if (task.status === "queued" || task.status === "pending") {
      count++;
    }
  });
  return count;
});

const hasRunningTask = computed(() => runningTasksCount.value > 0);

// Mock latency based on connection status
const aiLatency = computed(() => props.runtimeStatus === 'online' ? '128ms' : '--');

function openLogs() {
  shellUiStore.setDetailPanelOpen(true);
}
</script>

<style scoped>
.shell-status-bar {
  height: var(--statusbar-height, 28px);
  background: var(--color-bg-surface);
  border-top: 1px solid var(--color-border-subtle);
  padding: 0 var(--space-4);
  display: flex;
  align-items: center;
  justify-content: space-between;
  font: var(--font-caption);
  letter-spacing: var(--ls-caption);
  color: var(--color-text-secondary);
  position: relative;
  z-index: var(--z-statusbar);
  min-width: 0;
}

/* 顶部发光线（任务运行时出现） */
.shell-status-bar::before {
  content: '';
  position: absolute;
  top: 0; 
  left: 0; 
  right: 0;
  height: 1px;
  background: var(--gradient-status-bar);
  background-size: 200% 100%;
  opacity: 0.4;
  animation: status-flow calc(var(--motion-flow) * 3) linear infinite;
  transition: opacity var(--motion-default) var(--ease-standard);
  pointer-events: none;
}

.shell-status-bar[data-has-running-task="true"]::before {
  opacity: 1;
  animation: status-flow var(--motion-flow) linear infinite;
}

.shell-status-bar__left,
.shell-status-bar__right {
  display: flex;
  align-items: center;
  gap: var(--space-4); /* 16px */
  min-width: 0;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
}

.status-item .material-symbols-outlined {
  font-size: 14px;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-bg-muted);
  flex-shrink: 0;
}

.status-dot--success, .status-dot--online {
  background: var(--color-success);
  box-shadow: 0 0 6px var(--color-success);
  animation: device-heartbeat var(--motion-breathe) ease-in-out infinite;
}
.status-dot--warning, .status-dot--loading {
  background: var(--color-warning);
  box-shadow: 0 0 6px var(--color-warning);
  animation: device-heartbeat var(--motion-breathe) ease-in-out infinite;
}
.status-dot--danger, .status-dot--offline {
  background: var(--color-danger);
  box-shadow: 0 0 6px var(--color-danger);
  animation: device-heartbeat var(--motion-breathe) ease-in-out infinite;
}
.status-dot--info, .status-dot--idle { background: var(--color-info); }
.status-dot--brand {
  background: var(--color-brand-primary);
  box-shadow: 0 0 6px var(--color-brand-primary);
  animation: device-heartbeat var(--motion-breathe) ease-in-out infinite;
}

.status-icon-btn {
  background: transparent;
  border: none;
  color: currentColor;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  opacity: 0.8;
  transition: opacity var(--motion-fast) var(--ease-standard), color var(--motion-fast) var(--ease-standard);
  outline: none;
}

.status-icon-btn:hover {
  opacity: 1;
  color: var(--color-text-primary);
}

.status-icon-btn:focus-visible {
  outline: 2px solid var(--color-brand-primary);
  outline-offset: 2px;
  border-radius: var(--radius-xs);
}

.status-icon-btn .material-symbols-outlined {
  font-size: 16px;
}

/* 窄屏适配 */
@media (max-width: 860px) {
  .shell-status-bar__right {
    gap: var(--space-2);
  }
  .shell-status-bar__right .status-item:not(:last-of-type) {
    display: none;
  }
}
@media (max-width: 640px) {
  .shell-status-bar__left .status-item:not(:first-child) {
    display: none;
  }
}
</style>
