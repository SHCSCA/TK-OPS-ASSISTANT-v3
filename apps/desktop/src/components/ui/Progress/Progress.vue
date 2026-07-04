<template>
  <div
    class="ui-progress"
    :class="{ 'is-indeterminate': indeterminate }"
    :aria-valuemax="max"
    :aria-valuemin="0"
    :aria-valuenow="clampedValue"
    role="progressbar"
  >
    <div class="ui-progress__track">
      <div class="ui-progress__fill" :style="{ width: indeterminate ? undefined : `${fillWidth}%` }" />
    </div>
    <span v-if="showLabel" class="ui-progress__label">{{ indeterminate ? "处理中" : `${Math.round(fillWidth)}%` }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = withDefaults(
  defineProps<{
    indeterminate?: boolean;
    max?: number;
    showLabel?: boolean;
    value?: number;
  }>(),
  {
    indeterminate: false,
    max: 100,
    showLabel: false,
    value: 0
  }
);

const clampedValue = computed(() => Math.min(Math.max(props.value, 0), props.max));
const fillWidth = computed(() => (props.max <= 0 ? 0 : (clampedValue.value / props.max) * 100));
</script>

<style scoped>
.ui-progress {
  animation: progress-enter var(--motion-content) var(--ease-standard);
  display: grid;
  gap: 6px;
}

@keyframes progress-enter {
  from { opacity: 0; }
  to { opacity: 1; }
}

.ui-progress__track {
  background: var(--color-bg-muted);
  border-radius: var(--radius-full);
  height: 8px;
  overflow: hidden;
}

.ui-progress__fill {
  background: var(--gradient-ai-primary);
  background-size: 160px 100%;
  border-radius: inherit;
  height: 100%;
  transition: width var(--motion-default) var(--ease-standard);
}

.is-indeterminate .ui-progress__fill {
  animation: progress-flow var(--motion-pulse) linear infinite;
  width: 40%;
}

.ui-progress__label {
  color: var(--color-text-secondary);
  font: var(--font-caption);
}
</style>
