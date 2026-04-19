<template>
  <span
    class="ui-chip"
    :data-variant="variant"
    :class="{ 'is-clickable': clickable }"
    v-bind="$attrs"
  >
    <span v-if="$slots.icon || icon" class="ui-chip__icon">
      <slot name="icon">
        <span class="material-symbols-outlined">{{ icon }}</span>
      </slot>
    </span>
    <span class="ui-chip__label">
      <slot>{{ label }}</slot>
    </span>
    <button v-if="removable" class="ui-chip__remove" aria-label="移除标签" @click.stop="$emit('remove')">
      <span class="material-symbols-outlined">close</span>
    </button>
  </span>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    clickable?: boolean;
    icon?: string;
    label?: string;
    removable?: boolean;
    variant?: "default" | "brand" | "success" | "warning" | "danger" | "info";
  }>(),
  {
    clickable: false,
    label: "",
    removable: false,
    variant: "default"
  }
);

defineEmits<{
  (e: "remove"): void;
}>();
</script>

<style scoped>
.ui-chip {
  align-items: center;
  background: var(--color-bg-muted);
  border: 1px solid transparent;
  border-radius: var(--radius-full);
  color: var(--color-text-secondary);
  display: inline-flex;
  font: var(--font-caption);
  gap: 6px;
  height: 22px;
  letter-spacing: var(--ls-caption);
  padding: 0 8px;
  transition:
    background-color var(--motion-fast) var(--ease-standard),
    border-color var(--motion-fast) var(--ease-standard),
    color var(--motion-fast) var(--ease-standard);
  white-space: nowrap;
}

/* 变体: Default (已在基础类定义) */
.ui-chip[data-variant="default"] {
  background: var(--color-bg-muted);
  color: var(--color-text-secondary);
}

/* 变体: Brand */
.ui-chip[data-variant="brand"] {
  background: var(--color-bg-active);
  color: var(--color-brand-primary);
}

/* 变体: Success */
.ui-chip[data-variant="success"] {
  background: color-mix(in srgb, var(--color-success) 12%, transparent);
  color: var(--color-success);
}

/* 变体: Warning */
.ui-chip[data-variant="warning"] {
  background: color-mix(in srgb, var(--color-warning) 12%, transparent);
  color: var(--color-warning);
}

/* 变体: Danger */
.ui-chip[data-variant="danger"] {
  background: color-mix(in srgb, var(--color-danger) 12%, transparent);
  color: var(--color-danger);
}

/* 变体: Info */
.ui-chip[data-variant="info"] {
  background: color-mix(in srgb, var(--color-info) 12%, transparent);
  color: var(--color-info);
}

/* 可交互悬停态 */
.ui-chip.is-clickable {
  cursor: pointer;
}

.ui-chip.is-clickable:hover {
  border-color: currentColor;
}

/* 图标 */
.ui-chip__icon {
  align-items: center;
  display: flex;
  font-size: 14px;
  line-height: 1;
}

.ui-chip__icon :deep(.material-symbols-outlined) {
  font-size: 14px;
}

.ui-chip__label {
  line-height: 1;
}

/* 移除按钮 */
.ui-chip__remove {
  align-items: center;
  appearance: none;
  background: transparent;
  border: none;
  border-radius: var(--radius-full);
  color: currentColor;
  cursor: pointer;
  display: flex;
  height: 16px;
  justify-content: center;
  margin-left: -4px; /* 补偿内边距，使视觉上更紧凑 */
  opacity: 0.6;
  outline: none;
  padding: 0;
  transition:
    background-color var(--motion-fast) var(--ease-standard),
    opacity var(--motion-fast) var(--ease-standard);
  width: 16px;
}

.ui-chip__remove:hover {
  background: color-mix(in srgb, currentColor 10%, transparent);
  opacity: 1;
}

.ui-chip__remove:focus-visible {
  outline: 2px solid currentColor;
  outline-offset: 2px;
}

.ui-chip__remove .material-symbols-outlined {
  font-size: 14px;
}
</style>
