<template>
  <div class="overview-status">
    <div class="ai-provider-chip" :class="`ai-provider-chip--${runtimeStatus}`">
      <span class="material-symbols-outlined provider-icon">memory</span>
      <span class="ai-chip-text">{{ aiProviderLabel }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  runtimeStatus: string;
  aiProviderLabel: string;
}>();
</script>

<style scoped>
.ai-provider-chip {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  background: var(--surface-sunken);
  border: 1px solid var(--border-default);
  border-radius: 4px;
  color: var(--text-secondary);
}

.provider-icon {
  font-size: 13px;
}

.ai-provider-chip--online {
  border-color: color-mix(in srgb, var(--status-success) 30%, var(--border-default));
  color: var(--brand-primary);
}

.ai-provider-chip--offline {
  border-color: color-mix(in srgb, var(--status-error) 40%, var(--border-default));
  color: var(--status-error);
}
</style>
