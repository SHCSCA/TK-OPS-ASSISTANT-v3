<template>
  <section class="settings-workspace-panel">
    <div class="editor-card__header">
      <div>
        <p class="detail-panel__label">能力策略</p>
        <h2>能力矩阵</h2>
        <p class="workspace-page__summary">
          先选能力，再在右侧检查默认模型、Provider 和提示词，减少纵向滚动噪音。
        </p>
      </div>
    </div>

    <div v-if="capabilities.length === 0" class="empty-state">AI 能力配置尚未加载。</div>
    <div v-else class="capability-matrix">
      <button
        v-for="capability in capabilities"
        :key="capability.capabilityId"
        class="capability-matrix__row"
        :class="{ 'capability-matrix__row--active': capability.capabilityId === selectedCapabilityId }"
        type="button"
        :data-capability-id="capability.capabilityId"
        @click="$emit('select', capability.capabilityId)"
      >
        <div class="capability-matrix__main">
          <strong>{{ capabilityLabels[capability.capabilityId] ?? capability.capabilityId }}</strong>
          <span>{{ capability.capabilityId }}</span>
        </div>
        <div class="capability-matrix__meta">
          <span>{{ capability.provider }}</span>
          <span>{{ capability.model }}</span>
        </div>
        <label class="capability-matrix__toggle" @click.stop>
          <input
            v-model="capability.enabled"
            :data-field="`capability.${capability.capabilityId}.enabled`"
            type="checkbox"
            :disabled="disabled"
          />
          启用
        </label>
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { AICapabilityConfig } from "@/types/runtime";

defineProps<{
  capabilities: AICapabilityConfig[];
  capabilityLabels: Record<string, string>;
  disabled: boolean;
  selectedCapabilityId: string;
}>();

defineEmits<{
  (e: "select", capabilityId: string): void;
}>();
</script>

<style scoped>
.settings-workspace-panel {
  display: grid;
  gap: 16px;
}

.capability-matrix {
  display: grid;
  gap: 10px;
}

.capability-matrix__row {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(180px, 0.9fr) auto;
  gap: 12px;
  align-items: center;
  padding: 14px 16px;
  border: 1px solid var(--border-default);
  border-radius: 16px;
  background: color-mix(in srgb, var(--surface-secondary) 90%, transparent);
  color: var(--text-primary);
  cursor: pointer;
  text-align: left;
  transition: border-color 160ms ease, background 160ms ease, transform 160ms ease;
}

.capability-matrix__row:hover,
.capability-matrix__row--active {
  border-color: color-mix(in srgb, var(--brand-primary) 36%, var(--border-default));
  background: color-mix(in srgb, var(--brand-primary) 10%, var(--surface-tertiary));
  transform: translateY(-1px);
}

.capability-matrix__main,
.capability-matrix__meta {
  display: grid;
  gap: 4px;
}

.capability-matrix__main span,
.capability-matrix__meta span {
  color: var(--text-secondary);
  font-size: 12px;
}

.capability-matrix__toggle {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--text-secondary);
  font-size: 12px;
}

@media (max-width: 920px) {
  .capability-matrix__row {
    grid-template-columns: 1fr;
  }
}
</style>
