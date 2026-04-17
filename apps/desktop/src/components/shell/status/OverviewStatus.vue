<template>
  <div class="overview-status">
    <div class="overview-status__chip" :class="`overview-status__chip--${runtimeStatus}`">
      <span class="material-symbols-outlined">auto_awesome</span>
      <span>{{ aiProviderLabel }}</span>
    </div>
    <div class="overview-status__meta">
      <span>{{ pageTitle }}</span>
      <span>{{ pageTypeLabel }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  aiProviderLabel: string;
  pageTitle: string;
  pageType: string;
  runtimeStatus: string;
}>();

const pageTypeLabel = computed(() => {
  switch (props.pageType) {
    case "wizard":
      return "首启链路";
    case "dashboard":
      return "创作总览";
    case "workspace":
      return "工作台";
    case "editor":
      return "编辑流";
    case "queue":
      return "任务队列";
    case "settings":
      return "系统设置";
    default:
      return props.pageType;
  }
});
</script>

<style scoped>
.overview-status {
  align-items: center;
  display: flex;
  gap: var(--space-3);
}

.overview-status__chip {
  align-items: center;
  background: var(--color-bg-muted);
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-xs);
  color: var(--color-text-secondary);
  display: inline-flex;
  gap: 4px;
  padding: 2px 8px;
}

.overview-status__chip--online {
  border-color: color-mix(in srgb, var(--color-success) 28%, var(--color-border-default));
  color: var(--color-brand-primary);
}

.overview-status__chip--offline {
  border-color: color-mix(in srgb, var(--color-danger) 32%, var(--color-border-default));
  color: var(--color-danger);
}

.overview-status__meta {
  color: var(--color-text-tertiary);
  display: flex;
  gap: var(--space-2);
}
</style>
