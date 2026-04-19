<template>
  <Teleport to="body">
    <transition name="modal-fade">
      <div
        v-if="open"
        class="ui-modal-backdrop"
        :data-theme="theme"
        aria-hidden="true"
        @click="handleBackdropClick"
      >
        <div
          class="ui-modal"
          :class="`ui-modal--${size}`"
          role="dialog"
          aria-modal="true"
          @click.stop
        >
          <header v-if="$slots.header || title" class="ui-modal__header">
            <slot name="header">
              <h2 class="ui-modal__title">{{ title }}</h2>
            </slot>
            <button
              v-if="closable"
              class="ui-modal__close"
              aria-label="关闭弹窗"
              @click="emit('close')"
            >
              <span class="material-symbols-outlined">close</span>
            </button>
          </header>

          <main class="ui-modal__body">
            <slot />
          </main>

          <footer v-if="$slots.footer" class="ui-modal__footer">
            <slot name="footer" />
          </footer>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useShellUiStore } from "@/stores/shell-ui";

const props = defineProps<{
  closable?: boolean;
  closeOnBackdrop?: boolean;
  open: boolean;
  size?: "sm" | "md" | "lg" | "fullscreen";
  title?: string;
}>();

const emit = defineEmits<{
  (e: "close"): void;
}>();

const shellUiStore = useShellUiStore();
const theme = computed(() => shellUiStore.theme);

function handleBackdropClick() {
  if (props.closeOnBackdrop && props.closable) {
    emit("close");
  }
}
</script>

<style scoped>
.ui-modal-backdrop {
  position: fixed;
  inset: 0;
  background: var(--color-bg-overlay);
  z-index: var(--z-modal-backdrop);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-6);
  backdrop-filter: blur(8px);
}

.ui-modal {
  background: var(--color-bg-surface);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-lg);
  border: 1px solid var(--color-border-subtle);
  display: flex;
  flex-direction: column;
  max-height: 100%;
  width: 100%;
  color: var(--color-text-primary);
  position: relative;
  z-index: var(--z-modal);
}

.ui-modal--sm { max-width: 400px; }
.ui-modal--md { max-width: 640px; }
.ui-modal--lg { max-width: 960px; }
.ui-modal--fullscreen {
  max-width: 100%;
  height: 100%;
  border-radius: 0;
  border: none;
}

.ui-modal__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-5) var(--space-6);
  border-bottom: 1px solid var(--color-border-subtle);
  flex-shrink: 0;
}

.ui-modal__title {
  margin: 0;
  font: var(--font-title-lg);
  letter-spacing: var(--ls-title-lg);
  color: var(--color-text-primary);
}

.ui-modal__close {
  background: transparent;
  border: none;
  color: var(--color-text-tertiary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: var(--radius-md);
  margin-right: -8px;
  transition: background-color var(--motion-fast) var(--ease-standard), color var(--motion-fast) var(--ease-standard);
}

.ui-modal__close:hover {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
}

.ui-modal__close:focus-visible {
  outline: 2px solid var(--color-brand-primary);
  outline-offset: 2px;
}

.ui-modal__body {
  padding: var(--space-6);
  overflow-y: auto;
  flex: 1;
}

.ui-modal__footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--space-3);
  padding: var(--space-4) var(--space-6);
  border-top: 1px solid var(--color-border-subtle);
  background: var(--color-bg-canvas);
  border-radius: 0 0 var(--radius-xl) var(--radius-xl);
  flex-shrink: 0;
}

.ui-modal--fullscreen .ui-modal__footer {
  border-radius: 0;
}

/* Modal Entry Animation */
.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity var(--motion-default) var(--ease-standard);
}

.modal-fade-enter-active .ui-modal,
.modal-fade-leave-active .ui-modal {
  transition: transform var(--motion-slow) var(--ease-spring);
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}

.modal-fade-enter-from .ui-modal,
.modal-fade-leave-to .ui-modal {
  transform: translateY(16px) scale(0.96);
}

@media (max-width: 640px) {
  .ui-modal-backdrop {
    padding: var(--space-4);
  }
}
</style>
