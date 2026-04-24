<template>
  <section class="settings-workspace-panel">
    <div class="settings-workspace-panel__header">
      <div>
        <p class="detail-panel__label">能力矩阵</p>
        <h2>能力到 Provider 的绑定</h2>
        <p class="workspace-page__summary">
          能力列表只负责选择和启停，具体 Provider、模型和提示词在右侧 Inspector 编辑。
        </p>
      </div>
    </div>

    <div v-if="capabilities.length === 0" class="settings-workspace-panel__empty">
      AI 能力配置尚未加载。
    </div>

    <div v-else class="capability-matrix capability-matrix__list">
      <button
        v-for="capability in capabilities"
        :key="capability.capabilityId"
        class="capability-matrix__row"
        :class="{
          'capability-matrix__row--active': capability.capabilityId === selectedCapabilityId,
          'capability-matrix__row--disabled': disabled
        }"
        type="button"
        :data-capability-id="capability.capabilityId"
        :aria-pressed="capability.capabilityId === selectedCapabilityId"
        @click="$emit('select', capability.capabilityId)"
      >
        <div class="capability-matrix__main">
          <strong>{{ capabilityLabels[capability.capabilityId] ?? capability.capabilityId }}</strong>
          <span>{{ capability.capabilityId }}</span>
        </div>
        <div class="capability-matrix__meta">
          <span>{{ capability.provider || "未绑定 Provider" }}</span>
          <span>{{ capability.model || "未绑定模型" }}</span>
        </div>
        <label class="capability-matrix__toggle" @click.stop>
          <input
            v-model="capability.enabled"
            :data-field="`capability.${capability.capabilityId}.enabled`"
            type="checkbox"
            :disabled="disabled"
          />
          <span>{{ capability.enabled ? "已启用" : "已停用" }}</span>
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
  min-width: 0;
  container-type: inline-size;
}

.settings-workspace-panel__header {
  display: grid;
  gap: 8px;
}

.settings-workspace-panel__header h2 {
  margin: 0;
}

.settings-workspace-panel__empty {
  padding: 16px;
  border: 1px dashed var(--border-default);
  border-radius: 8px;
  background: color-mix(in srgb, var(--surface-secondary) 92%, transparent);
  color: var(--text-secondary);
}

.capability-matrix {
  display: grid;
  gap: 10px;
  min-width: 0;
}

.capability-matrix__row {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(180px, 0.9fr) auto;
  gap: 12px;
  align-items: center;
  min-width: 0;
  padding: 14px 16px;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: color-mix(in srgb, var(--surface-secondary) 94%, transparent);
  color: var(--text-primary);
  cursor: pointer;
  text-align: left;
  transition: border-color 160ms ease, background 160ms ease, transform 160ms ease;
}

.capability-matrix__row:hover,
.capability-matrix__row--active {
  border-color: color-mix(in srgb, var(--brand-primary) 34%, var(--border-default));
  background: color-mix(in srgb, var(--brand-primary) 10%, var(--surface-tertiary));
  transform: translateY(-1px);
}

.capability-matrix__row--disabled {
  cursor: default;
}

.capability-matrix__main,
.capability-matrix__meta {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.capability-matrix__main strong,
.capability-matrix__main span,
.capability-matrix__meta span,
.capability-matrix__toggle span {
  min-width: 0;
  overflow-wrap: anywhere;
}

.capability-matrix__main span,
.capability-matrix__meta span {
  color: var(--text-secondary);
  font-size: 12px;
}

.capability-matrix__toggle {
  display: inline-flex;
  align-items: center;
  justify-self: end;
  gap: 8px;
  color: var(--text-secondary);
  font-size: 12px;
  white-space: nowrap;
}

@container (max-width: 620px) {
  .capability-matrix__row {
    grid-template-columns: 1fr;
    align-items: start;
  }

  .capability-matrix__meta {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    column-gap: 12px;
  }

  .capability-matrix__toggle {
    justify-self: start;
  }
}
</style>
