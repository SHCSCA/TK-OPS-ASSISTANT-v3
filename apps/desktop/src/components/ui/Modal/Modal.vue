<template>
  <transition name="ui-modal-fade">
    <div
      v-if="open"
      class="ui-modal"
      role="presentation"
      @click.self="$emit('close')"
    >
      <section
        class="ui-modal__surface"
        :class="[`ui-modal__surface--${size}`]"
        role="dialog"
        aria-modal="true"
        v-bind="$attrs"
      >
        <header v-if="$slots.header || title" class="ui-modal__header">
          <div>
            <p v-if="eyebrow" class="ui-modal__eyebrow">{{ eyebrow }}</p>
            <h3 class="ui-modal__title">{{ title }}</h3>
          </div>
          <button
            class="ui-modal__close"
            type="button"
            aria-label="关闭弹窗"
            @click="$emit('close')"
          >
            <span class="material-symbols-outlined">close</span>
          </button>
        </header>

        <div class="ui-modal__body">
          <slot />
        </div>

        <footer v-if="$slots.footer" class="ui-modal__footer">
          <slot name="footer" />
        </footer>
      </section>
    </div>
  </transition>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    eyebrow?: string;
    open: boolean;
    size?: "sm" | "md" | "lg";
    title?: string;
  }>(),
  {
    eyebrow: "",
    size: "md",
    title: ""
  }
);

defineEmits<{
  close: [];
}>();
</script>

<style scoped>
.ui-modal {
  align-items: center;
  background: var(--color-bg-overlay);
  display: grid;
  inset: 0;
  justify-items: center;
  padding: var(--space-5);
  position: fixed;
  z-index: var(--z-modal-backdrop);
}

.ui-modal__surface {
  animation: modal-enter var(--motion-slow) var(--ease-spring);
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  display: grid;
  gap: var(--space-4);
  max-height: min(88vh, 960px);
  min-width: min(100%, 360px);
  overflow: hidden;
  z-index: var(--z-modal);
}

.ui-modal__surface--sm {
  width: min(100%, 420px);
}

.ui-modal__surface--md {
  width: min(100%, 560px);
}

.ui-modal__surface--lg {
  width: min(100%, 760px);
}

.ui-modal__header,
.ui-modal__footer {
  align-items: center;
  display: flex;
  gap: var(--space-3);
  justify-content: space-between;
  padding: var(--space-4) var(--space-5);
}

.ui-modal__header {
  border-bottom: 1px solid var(--color-border-subtle);
}

.ui-modal__footer {
  border-top: 1px solid var(--color-border-subtle);
}

.ui-modal__body {
  color: var(--color-text-primary);
  display: grid;
  gap: var(--space-4);
  max-height: min(64vh, 720px);
  overflow: auto;
  padding: 0 var(--space-5) var(--space-5);
}

.ui-modal__eyebrow {
  color: var(--color-text-tertiary);
  font-size: var(--font-caption);
  margin: 0 0 4px;
}

.ui-modal__title {
  font-size: var(--font-title-lg);
  margin: 0;
}

.ui-modal__close {
  align-items: center;
  appearance: none;
  background: transparent;
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  cursor: pointer;
  display: inline-flex;
  height: 32px;
  justify-content: center;
  width: 32px;
}

.ui-modal__close:hover {
  background: var(--color-bg-hover);
  border-color: var(--color-border-default);
  color: var(--color-text-primary);
}

.ui-modal-fade-enter-active,
.ui-modal-fade-leave-active {
  transition: opacity var(--motion-fast) var(--ease-standard);
}

.ui-modal-fade-enter-from,
.ui-modal-fade-leave-to {
  opacity: 0;
}
</style>
