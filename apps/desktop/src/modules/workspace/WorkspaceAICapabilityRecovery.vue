<template>
  <div class="dashboard-alert workspace-ai-readiness-alert" data-tone="warning">
    <span class="material-symbols-outlined">warning</span>
    <span class="workspace-ai-readiness-alert__message">{{ message }}</span>
    <div class="workspace-ai-readiness-alert__actions">
      <button
        class="workspace-ai-readiness-alert__button"
        data-testid="workspace-ai-refresh-button"
        type="button"
        :disabled="loading"
        @click="$emit('refresh')"
      >
        <span class="material-symbols-outlined">sync</span>
        重新同步 AI 状态
      </button>
      <button
        class="workspace-ai-readiness-alert__button workspace-ai-readiness-alert__button--primary"
        data-testid="workspace-ai-settings-button"
        type="button"
        @click="$emit('open-settings')"
      >
        <span class="material-symbols-outlined">settings</span>
        打开 AI 设置
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  loading: boolean;
  message: string;
}>();

defineEmits<{
  "open-settings": [];
  refresh: [];
}>();
</script>

<style scoped>
.workspace-ai-readiness-alert {
  align-items: center;
  flex-wrap: wrap;
}

.workspace-ai-readiness-alert__message {
  flex: 1 1 280px;
  min-width: 0;
}

.workspace-ai-readiness-alert__actions {
  display: flex;
  flex: 0 0 auto;
  flex-wrap: wrap;
  gap: var(--space-2);
  justify-content: flex-end;
  margin-left: auto;
}

.workspace-ai-readiness-alert__button {
  align-items: center;
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-md);
  color: var(--color-text-primary);
  cursor: pointer;
  display: inline-flex;
  font: var(--font-label-sm);
  gap: var(--space-2);
  min-height: 32px;
  padding: 0 var(--space-3);
  transition:
    background-color var(--motion-fast) var(--ease-standard),
    border-color var(--motion-fast) var(--ease-standard),
    transform var(--motion-instant) var(--ease-bounce);
  white-space: nowrap;
}

.workspace-ai-readiness-alert__button--primary {
  background: var(--color-brand-primary);
  border-color: var(--color-brand-primary);
  color: var(--color-text-on-brand);
}

.workspace-ai-readiness-alert__button:not(:disabled):hover {
  border-color: var(--color-brand-primary);
  transform: translateY(-1px);
}

.workspace-ai-readiness-alert__button:disabled {
  cursor: not-allowed;
  opacity: 0.56;
}

.workspace-ai-readiness-alert__button .material-symbols-outlined {
  font-size: 18px;
}
</style>
