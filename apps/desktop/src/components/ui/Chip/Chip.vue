<template>
  <span class="ui-chip" :class="[`ui-chip--${tone}`, `ui-chip--${size}`]" v-bind="$attrs">
    <span v-if="$slots.leading" class="ui-chip__icon">
      <slot name="leading" />
    </span>
    <span class="ui-chip__label">
      <slot />
    </span>
  </span>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    size?: "sm" | "md";
    tone?: "neutral" | "brand" | "success" | "warning" | "danger" | "info";
  }>(),
  {
    size: "md",
    tone: "neutral"
  }
);
</script>

<style scoped>
.ui-chip {
  align-items: center;
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-full);
  display: inline-flex;
  gap: 6px;
  line-height: 1;
  white-space: nowrap;
}

.ui-chip--sm {
  min-height: 22px;
  padding: 0 8px;
}

.ui-chip--md {
  min-height: 24px;
  padding: 0 10px;
}

.ui-chip--neutral {
  background: var(--color-bg-muted);
  color: var(--color-text-secondary);
}

.ui-chip--brand {
  background: var(--color-bg-active);
  border-color: color-mix(in srgb, var(--color-brand-primary) 26%, var(--color-border-default));
  color: var(--color-brand-primary);
}

.ui-chip--success {
  background: color-mix(in srgb, var(--color-success) 12%, var(--color-bg-surface));
  border-color: color-mix(in srgb, var(--color-success) 26%, var(--color-border-default));
  color: var(--color-success);
}

.ui-chip--warning {
  background: color-mix(in srgb, var(--color-warning) 12%, var(--color-bg-surface));
  border-color: color-mix(in srgb, var(--color-warning) 26%, var(--color-border-default));
  color: var(--color-warning);
}

.ui-chip--danger {
  background: color-mix(in srgb, var(--color-danger) 12%, var(--color-bg-surface));
  border-color: color-mix(in srgb, var(--color-danger) 26%, var(--color-border-default));
  color: var(--color-danger);
}

.ui-chip--info {
  background: color-mix(in srgb, var(--color-info) 12%, var(--color-bg-surface));
  border-color: color-mix(in srgb, var(--color-info) 26%, var(--color-border-default));
  color: var(--color-info);
}

.ui-chip__icon {
  display: inline-flex;
  font-size: 14px;
  line-height: 1;
}

.ui-chip__label {
  font-size: var(--font-caption);
  font-weight: 600;
}
</style>
