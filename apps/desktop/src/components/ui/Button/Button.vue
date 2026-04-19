<template>
  <button
    class="ui-button"
    :class="[
      `ui-button--${variant}`,
      `ui-button--${size}`,
      {
        'is-block': block,
        'is-disabled': disabled,
        'is-icon-only': iconOnly
      }
    ]"
    :data-state="running ? 'running' : 'idle'"
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
/* 基础属性 */
.ui-button {
  align-items: center;
  appearance: none;
  border: none;
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
    filter var(--motion-fast) var(--ease-standard);
  will-change: transform;
}

.ui-button__icon {
  align-items: center;
  display: inline-flex;
  font-size: 18px; /* Material symbols usually look good at 18/20px */
  line-height: 1;
}

.ui-button__label {
  white-space: nowrap;
}

/* 尺寸规范 */
.ui-button--sm {
  height: 28px;
  padding: 0 12px;
  font: var(--font-title-sm);
  letter-spacing: var(--ls-title-sm);
}
.ui-button--sm.is-icon-only {
  width: 28px;
  padding: 0;
}

.ui-button--md {
  height: 36px;
  padding: 0 16px;
  font: var(--font-title-sm);
  letter-spacing: var(--ls-title-sm);
}
.ui-button--md.is-icon-only {
  width: 36px;
  padding: 0;
}

.ui-button--lg {
  height: 44px;
  padding: 0 20px;
  font: var(--font-title-md);
  letter-spacing: var(--ls-title-md);
}
.ui-button--lg.is-icon-only {
  width: 44px;
  padding: 0;
}

/* Primary */
.ui-button--primary {
  background: var(--color-brand-primary);
  color: var(--color-text-on-brand);
}
.ui-button--primary:hover:not(:disabled) {
  background: var(--color-brand-primary-hover);
  box-shadow: var(--shadow-glow-brand);
}
.ui-button--primary:active:not(:disabled) {
  background: var(--color-brand-primary-active);
  transform: scale(0.98);
  transition-duration: var(--motion-instant);
}
.ui-button--primary:focus-visible {
  outline: 2px solid var(--color-brand-primary);
  outline-offset: 2px;
}
.ui-button--primary:disabled,
.ui-button--primary.is-disabled {
  background: var(--color-bg-muted);
  color: var(--color-text-tertiary);
  cursor: not-allowed;
  box-shadow: none;
  transform: none;
}

/* Secondary */
.ui-button--secondary {
  background: transparent;
  color: var(--color-text-primary);
  border: 1px solid var(--color-border-default);
}
.ui-button--secondary:hover:not(:disabled) {
  background: var(--color-bg-hover);
  border-color: var(--color-border-strong);
}
.ui-button--secondary:active:not(:disabled) {
  background: var(--color-bg-active);
  transform: scale(0.98);
  transition-duration: var(--motion-instant);
}
.ui-button--secondary:focus-visible {
  outline: 2px solid var(--color-brand-primary);
  outline-offset: 2px;
}
.ui-button--secondary:disabled,
.ui-button--secondary.is-disabled {
  color: var(--color-text-tertiary);
  border-color: var(--color-border-subtle);
  cursor: not-allowed;
  transform: none;
}

/* AI */
.ui-button--ai {
  background: var(--gradient-ai-primary);
  background-size: 200% 200%;
  background-position: 0% 50%;
  color: #FFFFFF;
  position: relative;
  overflow: hidden;
  transition:
    background-position var(--motion-default) var(--ease-standard),
    transform var(--motion-instant) var(--ease-bounce),
    box-shadow var(--motion-fast) var(--ease-standard);
}
.ui-button--ai:hover:not(:disabled) {
  background-position: 100% 50%;
  box-shadow: var(--shadow-glow-ai);
}
.ui-button--ai:active:not(:disabled) {
  transform: scale(0.98);
}
.ui-button--ai[data-state="running"]:not(:disabled) {
  animation: ai-flow var(--motion-flow) linear infinite;
  box-shadow: var(--shadow-glow-ai);
}
.ui-button--ai:focus-visible {
  outline: 2px solid var(--color-brand-secondary);
  outline-offset: 2px;
}
.ui-button--ai:disabled,
.ui-button--ai.is-disabled {
  background: var(--color-bg-muted);
  color: var(--color-text-tertiary);
  cursor: not-allowed;
  transform: none;
}
@keyframes ai-flow {
  0% { background-position: 0% 50%; }
  100% { background-position: 200% 50%; }
}

/* Danger */
.ui-button--danger {
  background: var(--color-danger);
  color: #FFFFFF;
}
.ui-button--danger:hover:not(:disabled) {
  filter: brightness(1.1);
  box-shadow: 0 4px 12px rgba(255, 90, 99, 0.2);
}
.ui-button--danger:active:not(:disabled) {
  transform: scale(0.98);
  filter: brightness(0.95);
}
.ui-button--danger:focus-visible {
  outline: 2px solid var(--color-danger);
  outline-offset: 2px;
}
.ui-button--danger:disabled,
.ui-button--danger.is-disabled {
  background: var(--color-bg-muted);
  color: var(--color-text-tertiary);
  cursor: not-allowed;
  transform: none;
}

/* Ghost */
.ui-button--ghost {
  background: transparent;
  color: var(--color-text-secondary);
}
.ui-button--ghost:hover:not(:disabled) {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
}
.ui-button--ghost:active:not(:disabled) {
  background: var(--color-bg-active);
  transform: scale(0.98);
}
.ui-button--ghost:focus-visible {
  outline: 2px solid var(--color-brand-primary);
  outline-offset: 2px;
}
.ui-button--ghost:disabled,
.ui-button--ghost.is-disabled {
  color: var(--color-text-tertiary);
  cursor: not-allowed;
  transform: none;
}

/* 其他辅助 */
.is-block {
  width: 100%;
}
</style>
