<template>
  <div class="ui-toast" :class="[`ui-toast--${tone}`]" role="status" v-bind="$attrs">
    <span class="material-symbols-outlined ui-toast__icon">{{ icon }}</span>
    <div class="ui-toast__body">
      <strong v-if="title">{{ title }}</strong>
      <span><slot /></span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = withDefaults(
  defineProps<{
    title?: string;
    tone?: "info" | "success" | "warning" | "danger";
  }>(),
  {
    title: "",
    tone: "info"
  }
);

const icon = computed(() => {
  switch (props.tone) {
    case "success":
      return "check_circle";
    case "warning":
      return "warning";
    case "danger":
      return "error";
    default:
      return "info";
  }
});
</script>

<style scoped>
.ui-toast {
  align-items: flex-start;
  animation: toast-slide-up var(--motion-default) var(--ease-spring);
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  display: grid;
  gap: var(--space-3);
  grid-template-columns: auto minmax(0, 1fr);
  padding: var(--space-3) var(--space-4);
}

.ui-toast__icon {
  font-size: 18px;
  line-height: 1.2;
}

.ui-toast__body {
  display: grid;
  gap: 4px;
}

.ui-toast__body strong {
  font-size: var(--font-body-sm);
}

.ui-toast__body span {
  color: var(--color-text-secondary);
  font-size: var(--font-caption);
  line-height: 1.6;
}

.ui-toast--info {
  background: color-mix(in srgb, var(--color-info) 10%, var(--color-bg-elevated));
  border-color: color-mix(in srgb, var(--color-info) 28%, var(--color-border-default));
}

.ui-toast--info .ui-toast__icon,
.ui-toast--info strong {
  color: var(--color-info);
}

.ui-toast--success {
  background: color-mix(in srgb, var(--color-success) 12%, var(--color-bg-elevated));
  border-color: color-mix(in srgb, var(--color-success) 28%, var(--color-border-default));
}

.ui-toast--success .ui-toast__icon,
.ui-toast--success strong {
  color: var(--color-success);
}

.ui-toast--warning {
  background: color-mix(in srgb, var(--color-warning) 12%, var(--color-bg-elevated));
  border-color: color-mix(in srgb, var(--color-warning) 28%, var(--color-border-default));
}

.ui-toast--warning .ui-toast__icon,
.ui-toast--warning strong {
  color: var(--color-warning);
}

.ui-toast--danger {
  background: color-mix(in srgb, var(--color-danger) 12%, var(--color-bg-elevated));
  border-color: color-mix(in srgb, var(--color-danger) 28%, var(--color-border-default));
}

.ui-toast--danger .ui-toast__icon,
.ui-toast--danger strong {
  color: var(--color-danger);
}
</style>
