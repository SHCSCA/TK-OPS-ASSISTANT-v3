<template>
  <div class="editing-status">
    <div class="editing-status__chip">
      <span class="material-symbols-outlined">edit</span>
      <span>{{ pageTitle }}</span>
    </div>
    <div class="editing-status__meta">
      <span>{{ projectLabel }}</span>
      <span>{{ detailOpen ? "详情面板已展开" : "详情面板已收起" }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  detailOpen: boolean;
  pageTitle: string;
  projectLabel: string;
}>();
</script>

<style scoped>
.editing-status {
  align-items: center;
  display: flex;
  gap: var(--space-3);
}

.editing-status__chip {
  align-items: center;
  color: var(--color-brand-primary);
  display: inline-flex;
  gap: 6px;
  font-family: var(--font-family-mono);
  font-size: var(--font-caption);
  font-weight: 600;
}

.editing-status__meta {
  color: var(--color-text-tertiary);
  display: flex;
  gap: var(--space-2);
}
</style>
