<template>
  <div class="shell-status-bar" :class="{ 'has-activity': hasActivity }">
    <div class="shell-status-bar__group">
      <div class="shell-status-bar__runtime" :title="runtimeLabel">
        <span class="shell-status-bar__dot" :class="`is-${runtimeTone}`" />
        <span class="shell-status-bar__text">{{ runtimeLabel }}</span>
      </div>

      <div class="shell-status-bar__divider" />

      <transition name="status-fade" mode="out-in">
        <component :is="activeComponent" v-bind="componentProps" />
      </transition>
    </div>

    <div class="shell-status-bar__group shell-status-bar__group--secondary">
      <span class="shell-status-bar__text">{{ syncLabel }}</span>
      <div class="shell-status-bar__divider" />
      <span class="shell-status-bar__text">{{ detailOpen ? "右侧上下文已展开" : "右侧上下文已收起" }}</span>
      <div class="shell-status-bar__divider" />
      <span class="shell-status-bar__text">{{ projectLabel }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

import EditingStatus from "@/components/shell/status/EditingStatus.vue";
import OverviewStatus from "@/components/shell/status/OverviewStatus.vue";
import TaskProgressStatus from "@/components/shell/status/TaskProgressStatus.vue";

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

const activeComponent = computed(() => {
  switch (props.mode) {
    case "editing":
      return EditingStatus;
    case "rendering":
    case "tasks":
    case "publishing":
    case "review":
      return TaskProgressStatus;
    default:
      return OverviewStatus;
  }
});

const componentProps = computed(() => {
  if (activeComponent.value === OverviewStatus) {
    return {
      aiProviderLabel: props.aiProviderLabel,
      pageTitle: props.pageTitle,
      pageType: props.pageType,
      runtimeStatus: props.runtimeStatus
    };
  }

  if (activeComponent.value === EditingStatus) {
    return {
      detailOpen: props.detailOpen,
      pageTitle: props.pageTitle,
      projectLabel: props.projectLabel
    };
  }

  return {
    mode: props.mode
  };
});

const hasActivity = computed(() => ["editing", "rendering", "tasks", "publishing", "review"].includes(props.mode));
</script>

<style scoped>
.shell-status-bar {
  align-items: center;
  background: var(--color-bg-surface);
  display: flex;
  font-family: var(--font-family-mono);
  font-size: var(--font-caption);
  height: 100%;
  justify-content: space-between;
  overflow: hidden;
  padding: 0 var(--space-4);
  position: relative;
}

.shell-status-bar::before {
  background: var(--gradient-status-bar);
  background-size: 200% 100%;
  content: "";
  height: 1px;
  left: 0;
  opacity: 0;
  position: absolute;
  right: 0;
  top: 0;
  transition: opacity var(--motion-default) var(--ease-standard);
}

.shell-status-bar.has-activity::before {
  animation: status-flow 2.4s linear infinite;
  opacity: 1;
}

.shell-status-bar__group {
  align-items: center;
  display: flex;
  gap: var(--space-3);
  min-width: 0;
}

.shell-status-bar__group--secondary {
  color: var(--color-text-tertiary);
}

.shell-status-bar__runtime {
  align-items: center;
  display: inline-flex;
  gap: var(--space-2);
  min-width: 0;
}

.shell-status-bar__dot {
  border-radius: 999px;
  flex-shrink: 0;
  height: 6px;
  width: 6px;
}

.shell-status-bar__dot.is-online {
  background: var(--color-success);
}

.shell-status-bar__dot.is-offline {
  background: var(--color-danger);
}

.shell-status-bar__dot.is-loading {
  animation: subtle-pulse 1.4s var(--ease-standard) infinite;
  background: var(--color-warning);
}

.shell-status-bar__dot.is-idle {
  background: var(--color-info);
}

.shell-status-bar__text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.shell-status-bar__divider {
  background: var(--color-border-subtle);
  height: 12px;
  width: 1px;
}

.status-fade-enter-active,
.status-fade-leave-active {
  transition:
    opacity var(--motion-fast) var(--ease-standard),
    transform var(--motion-fast) var(--ease-standard);
}

.status-fade-enter-from,
.status-fade-leave-to {
  opacity: 0;
  transform: translateX(4px);
}

@media (max-width: 860px) {
  .shell-status-bar__group--secondary {
    display: none;
  }
}
</style>
