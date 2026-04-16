<template>
  <footer class="shell-status-bar">
    <div class="status-left">
      <!-- Runtime 状态 (始终固定) -->
      <div class="status-item" :title="`Runtime: ${runtimeLabel}`">
        <span class="runtime-dot" :class="`runtime-dot--${runtimeTone}`"></span>
        <span class="status-text">{{ runtimeLabel }}</span>
      </div>

      <div class="divider"></div>

      <!-- 动态业务状态区 -->
      <transition name="status-fade" mode="out-in">
        <component
          :is="activeComponent"
          v-bind="componentProps"
        />
      </transition>
    </div>

    <div class="status-right">
      <!-- 同步状态 -->
      <div class="status-item sync-status">
        <span class="material-symbols-outlined status-icon">cloud_sync</span>
        <span class="status-text">{{ syncLabel }}</span>
      </div>

      <div class="divider"></div>

      <!-- 版本号 -->
      <div class="status-item system-version">
        <span class="status-text">v0.2.0</span>
      </div>
    </div>
  </footer>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import OverviewStatus from '@/components/shell/status/OverviewStatus.vue';
import EditingStatus from '@/components/shell/status/EditingStatus.vue';
import TaskProgressStatus from '@/components/shell/status/TaskProgressStatus.vue';

const props = defineProps<{
  mode: string;
  runtimeLabel: string;
  runtimeTone: string;
  runtimeStatus: 'online' | 'offline' | 'loading' | 'idle';
  aiProviderLabel: string;
  syncLabel: string;
}>();

const activeComponent = computed(() => {
  switch (props.mode) {
    case 'editing': return EditingStatus;
    case 'rendering':
    case 'tasks':
    case 'publishing': return TaskProgressStatus;
    default: return OverviewStatus;
  }
});

const componentProps = computed(() => {
  if (activeComponent.value === OverviewStatus) {
    return {
      runtimeStatus: props.runtimeStatus,
      aiProviderLabel: props.aiProviderLabel
    };
  }
  return {};
});
</script>

<style scoped>
.shell-status-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  height: 100%;
  padding: 0 16px;
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-tertiary);
  background: var(--surface-secondary);
}

.status-left, .status-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.status-icon {
  font-size: 14px;
}

.status-text {
  font-weight: 500;
  letter-spacing: 0.02em;
}

.divider {
  width: 1px;
  height: 14px;
  background: var(--border-default);
}

.runtime-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  position: relative;
  display: inline-block;
}

.runtime-dot::after {
  content: "";
  position: absolute;
  top: -3px; left: -3px; right: -3px; bottom: -3px;
  border-radius: 50%;
  border: 1px solid currentColor;
  opacity: 0.4;
  animation: ripple 2s infinite;
}

@keyframes ripple {
  0% { transform: scale(1); opacity: 0.4; }
  100% { transform: scale(2.5); opacity: 0; }
}

.runtime-dot--online { background: var(--status-success); color: var(--status-success); }
.runtime-dot--loading { background: var(--status-warning); color: var(--status-warning); }
.runtime-dot--offline { background: var(--status-error); color: var(--status-error); }
.runtime-dot--idle { background: var(--status-info); color: var(--status-info); }

.system-version {
  font-weight: 800;
  color: var(--text-secondary);
}

.status-fade-enter-active,
.status-fade-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.status-fade-enter-from {
  opacity: 0;
  transform: translateX(-4px);
}

.status-fade-leave-to {
  opacity: 0;
  transform: translateX(4px);
}
</style>
