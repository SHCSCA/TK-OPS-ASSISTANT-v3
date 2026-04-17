<template>
  <div class="task-progress-status">
    <Progress indeterminate class="task-progress-status__progress" />
    <span class="task-progress-status__label">{{ modeLabel }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

import Progress from "@/components/ui/Progress/Progress.vue";

const props = defineProps<{
  mode: string;
}>();

const modeLabel = computed(() => {
  switch (props.mode) {
    case "rendering":
      return "渲染任务通道已接管";
    case "publishing":
      return "发布任务等待 Runtime 推送";
    case "review":
      return "复盘链路等待新事件";
    default:
      return "后台任务等待新事件";
  }
});
</script>

<style scoped>
.task-progress-status {
  align-items: center;
  display: flex;
  gap: var(--space-3);
  min-width: 220px;
}

.task-progress-status__progress {
  flex: 1;
}

.task-progress-status__label {
  color: var(--color-text-secondary);
  font-size: var(--font-caption);
  white-space: nowrap;
}
</style>
