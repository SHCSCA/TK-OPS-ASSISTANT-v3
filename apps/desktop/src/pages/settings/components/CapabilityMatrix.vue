<template>
  <div class="matrix-container">
    <table class="matrix-table">
      <thead>
        <tr>
          <th class="col-capability">能力</th>
          <th class="col-enabled">启用</th>
          <th class="col-provider">Provider</th>
          <th class="col-model">模型</th>
          <th class="col-status">状态</th>
        </tr>
      </thead>
      <tbody>
        <CapabilityRow
          v-for="row in rows"
          :key="row.capabilityId"
          :row="row"
          :provider-catalog="providerCatalog"
          :model-catalog="modelCatalog"
          :support-matrix="supportMatrix"
          @update="$emit('update', $event)"
          @load-models="$emit('loadModels', $event)"
        />
      </tbody>
    </table>
    
    <div class="matrix-footer">
      <p class="hint">提示：Provider 已全量开放，执行前请通过检测中心确认能力与协议是否可用。</p>
      <div class="actions">
        <Button variant="secondary" @click="$emit('reset')">恢复默认</Button>
        <Button variant="primary" :disabled="!dirty" @click="$emit('save')">保存绑定</Button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { CapabilityBindingRow, AICapabilitySupportMatrix, AIProviderCatalogItem, AIModelCatalogItem } from "../types";
import CapabilityRow from "./CapabilityRow.vue";
import Button from "@/components/ui/Button/Button.vue";

defineProps<{
  rows: CapabilityBindingRow[];
  providerCatalog: AIProviderCatalogItem[];
  modelCatalog: Record<string, AIModelCatalogItem[]>;
  supportMatrix: AICapabilitySupportMatrix | null;
  dirty: boolean;
}>();

defineEmits<{
  (e: "update", patch: Partial<CapabilityBindingRow> & { capabilityId: string }): void;
  (e: "loadModels", providerId: string): void;
  (e: "save"): void;
  (e: "reset"): void;
}>();
</script>

<style scoped>
.matrix-container {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.matrix-table {
  width: 100%;
  border-collapse: collapse;
}

.matrix-table th {
  text-align: left;
  padding: var(--space-3) var(--space-4);
  font: var(--font-caption);
  color: var(--color-text-tertiary);
  text-transform: uppercase;
  border-bottom: 1px solid var(--color-border-default);
}

.col-capability { width: 160px; }
.col-enabled { width: 80px; }
.col-provider { width: 220px; }
.col-model { min-width: 200px; }
.col-status { width: 80px; text-align: center !important; }

.matrix-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: var(--space-4);
  border-top: 1px solid var(--color-border-subtle);
}

.hint {
  font: var(--font-body-sm);
  color: var(--color-text-tertiary);
  margin: 0;
}

.actions {
  display: flex;
  gap: var(--space-3);
}
</style>
