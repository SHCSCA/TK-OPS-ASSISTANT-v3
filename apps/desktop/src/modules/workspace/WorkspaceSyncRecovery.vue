<template>
  <div class="workspace-sync-recovery" data-testid="workspace-sync-recovery">
    <span class="material-symbols-outlined">sync_problem</span>
    <div>
      <strong>AI 三轨未对齐</strong>
      <p>{{ message }}</p>
    </div>
    <button
      type="button"
      data-testid="workspace-sync-managed-tracks-button"
      :disabled="disabled"
      @click="$emit('sync')"
    >
      <span class="material-symbols-outlined">sync</span>
      同步 AI 三轨
    </button>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  disabled: boolean;
  message: string;
}>();

defineEmits<{
  sync: [];
}>();
</script>

<style scoped>
.workspace-sync-recovery {
  align-items: center;
  background: color-mix(in srgb, var(--color-warning) 10%, var(--color-bg-surface));
  border: 1px solid color-mix(in srgb, var(--color-warning) 34%, var(--color-border-default));
  border-radius: var(--radius-lg);
  color: var(--color-text-primary);
  display: grid;
  gap: var(--space-3);
  grid-template-columns: auto minmax(0, 1fr) auto;
  padding: var(--space-3) var(--space-4);
}

.workspace-sync-recovery > .material-symbols-outlined {
  color: var(--color-warning);
}

.workspace-sync-recovery p {
  color: var(--color-text-secondary);
  margin: 2px 0 0;
}

.workspace-sync-recovery button {
  align-items: center;
  background: var(--color-brand-primary);
  border: 1px solid var(--color-brand-primary);
  border-radius: var(--radius-md);
  color: var(--color-text-on-brand);
  cursor: pointer;
  display: inline-flex;
  font: var(--font-label-sm);
  gap: var(--space-2);
  justify-content: center;
  min-height: 34px;
  padding: 0 var(--space-3);
  white-space: nowrap;
}

.workspace-sync-recovery button:disabled {
  cursor: not-allowed;
  opacity: 0.56;
}

@container editing-workspace (max-width: 860px) {
  .workspace-sync-recovery {
    grid-template-columns: auto minmax(0, 1fr);
  }

  .workspace-sync-recovery button {
    grid-column: 1 / -1;
  }
}
</style>
