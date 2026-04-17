<template>
  <button
    class="ui-button"
    :class="[
      `ui-button--${variant}`,
      `ui-button--${size}`,
      {
        'is-block': block,
        'is-disabled': disabled,
        'is-icon-only': iconOnly,
        'is-running': running
      }
    ]"
    :disabled="disabled"
    :type="type"
    v-bind="$attrs"
  >
    <span v-if="$slots.leading" class="ui-button__icon">
      <slot name="leading" />
    </span>
    <span v-if="!iconOnly" class="ui-button__label">
      <slot />
    </span>
    <span v-if="$slots.trailing && !iconOnly" class="ui-button__icon">
      <slot name="trailing" />
    </span>
  </button>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    block?: boolean;
    disabled?: boolean;
    iconOnly?: boolean;
    running?: boolean;
    size?: "sm" | "md" | "lg";
    type?: "button" | "submit" | "reset";
    variant?: "primary" | "secondary" | "ghost" | "danger" | "ai";
  }>(),
  {
    block: false,
    disabled: false,
    iconOnly: false,
    running: false,
    size: "md",
    type: "button",
    variant: "secondary"
  }
);
</script>

<style scoped>
.ui-button {
  align-items: center;
  appearance: none;
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  cursor: pointer;
  display: inline-flex;
  gap: var(--space-2);
  justify-content: center;
  min-width: 0;
  outline: none;
  transition:
    background-color var(--motion-fast) var(--ease-standard),
    border-color var(--motion-fast) var(--ease-standard),
    color var(--motion-fast) var(--ease-standard),
    box-shadow var(--motion-fast) var(--ease-standard),
    transform var(--motion-instant) var(--ease-bounce),
    background-position var(--motion-default) var(--ease-standard);
  will-change: transform;
}

.ui-button:focus-visible {
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--color-brand-primary) 20%, transparent);
}

.ui-button:hover:not(:disabled) {
  transform: translateY(-1px);
}

.ui-button:active:not(:disabled) {
  transform: scale(0.98);
}

.ui-button:disabled,
.ui-button.is-disabled {
  cursor: not-allowed;
  opacity: 0.56;
  transform: none;
}

.ui-button--sm {
  height: 28px;
  padding: 0 var(--space-3);
}

.ui-button--md {
  height: 36px;
  padding: 0 var(--space-4);
}

.ui-button--lg {
  height: 44px;
  padding: 0 var(--space-5);
}

.ui-button--primary {
  background: var(--color-brand-primary);
  border-color: var(--color-brand-primary);
  color: var(--color-text-on-brand);
}

.ui-button--primary:hover:not(:disabled) {
  background: var(--color-brand-primary-hover);
  border-color: var(--color-brand-primary-hover);
  box-shadow: var(--shadow-glow-brand);
}

.ui-button--secondary {
  background: var(--color-bg-surface);
  border-color: var(--color-border-default);
  color: var(--color-text-primary);
}

.ui-button--secondary:hover:not(:disabled) {
  background: var(--color-bg-hover);
  border-color: var(--color-border-strong);
}

.ui-button--ghost {
  background: transparent;
  border-color: transparent;
  color: var(--color-text-secondary);
}

.ui-button--ghost:hover:not(:disabled) {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
}

.ui-button--danger {
  background: color-mix(in srgb, var(--color-danger) 10%, var(--color-bg-surface));
  border-color: color-mix(in srgb, var(--color-danger) 28%, var(--color-border-default));
  color: var(--color-text-primary);
}

.ui-button--danger:hover:not(:disabled) {
  background: color-mix(in srgb, var(--color-danger) 16%, var(--color-bg-surface));
  border-color: color-mix(in srgb, var(--color-danger) 40%, var(--color-border-default));
}

.ui-button--ai {
  background: var(--gradient-ai-primary);
  background-size: 200% 100%;
  border-color: transparent;
  color: var(--color-text-on-brand);
}

.ui-button--ai:hover:not(:disabled),
.ui-button--ai.is-running {
  animation: ai-flow 2.4s linear infinite;
  box-shadow: var(--shadow-glow-ai);
}

.ui-button__icon {
  align-items: center;
  display: inline-flex;
  font-size: 18px;
  line-height: 1;
}

.ui-button__label {
  font-size: var(--font-title-sm);
  font-weight: 600;
  line-height: 1;
  white-space: nowrap;
}

.is-block {
  width: 100%;
}

.is-icon-only {
  padding: 0;
  width: 36px;
}

.ui-button--sm.is-icon-only {
  width: 28px;
}

.ui-button--lg.is-icon-only {
  width: 44px;
}
</style>
