<template>
  <tr class="matrix-row">
    <td class="matrix-cell">
      <strong class="capability-label">{{ row.label }}</strong>
    </td>
    <td class="matrix-cell">
      <label class="ui-toggle-wrapper">
        <input
          type="checkbox"
          :checked="row.enabled"
          class="ui-toggle"
          @change="handleToggle"
        />
        <span class="ui-toggle-track" />
      </label>
    </td>
    <td class="matrix-cell">
      <select
        :value="row.provider"
        class="ui-select"
        @change="handleProviderChange"
      >
        <option value="" disabled>选择 Provider</option>
        <option
          v-for="p in filteredProviders"
          :key="p.provider"
          :value="p.provider"
          :disabled="!p.configured"
          :class="{ 'option-unconfigured': !p.configured }"
        >
          {{ p.configured ? '● ' : '' }}{{ p.label }}{{ p.configured ? '' : ' (未配置)' }}
        </option>
      </select>
    </td>
    <td class="matrix-cell">
      <select
        :value="row.model"
        class="ui-select"
        @change="handleModelChange"
      >
        <option value="" disabled>选择模型</option>
        <option
          v-for="m in sortedModels"
          :key="m.modelId"
          :value="m.modelId"
        >
          {{ m.displayName || m.modelId }}{{ m.defaultFor.includes(row.capabilityId) ? ' ★' : '' }}
        </option>
      </select>
    </td>
    <td class="matrix-cell align-center">
      <span class="status-dot" :class="computedStatus" :title="statusTitle" />
    </td>
  </tr>
</template>

<script setup lang="ts">
import { computed, watch } from "vue";
import type { CapabilityBindingRow, AICapabilitySupportMatrix, AIProviderCatalogItem, AIModelCatalogItem } from "../types";

const props = defineProps<{
  row: CapabilityBindingRow;
  providerCatalog: AIProviderCatalogItem[];
  modelCatalog: Record<string, AIModelCatalogItem[]>;
  supportMatrix: AICapabilitySupportMatrix | null;
}>();

const emit = defineEmits<{
  (e: "update", patch: Partial<CapabilityBindingRow> & { capabilityId: string }): void;
  (e: "loadModels", providerId: string): void;
}>();

/** 按能力过滤：只显示支持当前能力的 Provider */
const filteredProviders = computed(() => {
  if (!props.supportMatrix) return props.providerCatalog;

  const supportItem = props.supportMatrix.capabilities.find(
    c => c.capabilityId === props.row.capabilityId
  );
  if (!supportItem) return props.providerCatalog;

  const supportedIds = new Set(supportItem.providers);
  return props.providerCatalog.filter(p => supportedIds.has(p.provider));
});

/** 模型排序：defaultFor 匹配的排在前面 */
const sortedModels = computed(() => {
  const models = props.modelCatalog[props.row.provider] || [];
  return [...models].sort((a, b) => {
    const aDefault = a.defaultFor.includes(props.row.capabilityId) ? 0 : 1;
    const bDefault = b.defaultFor.includes(props.row.capabilityId) ? 0 : 1;
    return aDefault - bDefault;
  });
});

/** 状态计算 */
const computedStatus = computed(() => {
  if (!props.row.enabled) return "neutral";
  const provider = props.providerCatalog.find(p => p.provider === props.row.provider);
  if (!provider) return "neutral";
  if (!provider.configured) return "warning";
  if (provider.status === "ready") return "ready";
  return "warning";
});

const statusTitle = computed(() => {
  switch (computedStatus.value) {
    case "ready": return "就绪";
    case "warning": return "Provider 未配置或未通过测试";
    case "neutral": return "未启用";
    default: return "";
  }
});

/** Provider 变更时自动加载模型列表 */
watch(() => props.row.provider, (newProvider) => {
  if (newProvider && !props.modelCatalog[newProvider]) {
    emit("loadModels", newProvider);
  }
});

function handleToggle(e: Event) {
  const target = e.target as HTMLInputElement;
  emit("update", { capabilityId: props.row.capabilityId, enabled: target.checked });
}

function handleProviderChange(e: Event) {
  const target = e.target as HTMLSelectElement;
  emit("update", { capabilityId: props.row.capabilityId, provider: target.value, model: "" });
  if (target.value && !props.modelCatalog[target.value]) {
    emit("loadModels", target.value);
  }
}

function handleModelChange(e: Event) {
  const target = e.target as HTMLSelectElement;
  emit("update", { capabilityId: props.row.capabilityId, model: target.value });
}
</script>

<style scoped>
.matrix-row {
  border-bottom: 1px solid var(--color-border-subtle);
  transition: background-color var(--motion-fast) var(--ease-standard);
}

.matrix-row:hover {
  background: var(--color-bg-hover);
}

.matrix-cell {
  padding: var(--space-3) var(--space-4);
  vertical-align: middle;
}

.capability-label {
  font: var(--font-body-md);
  color: var(--color-text-primary);
}

/* 自定义开关 */
.ui-toggle-wrapper {
  position: relative;
  display: inline-flex;
  cursor: pointer;
}

.ui-toggle {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
}

.ui-toggle-track {
  display: inline-block;
  width: 32px;
  height: 18px;
  border-radius: 9px;
  background: var(--color-bg-muted);
  border: 1px solid var(--color-border-default);
  position: relative;
  transition: background var(--motion-fast) var(--ease-standard);
}

.ui-toggle-track::after {
  content: '';
  position: absolute;
  top: 2px;
  left: 2px;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--color-text-tertiary);
  transition: transform var(--motion-fast) var(--ease-spring), background var(--motion-fast) var(--ease-standard);
}

.ui-toggle:checked + .ui-toggle-track {
  background: var(--color-brand-primary);
  border-color: var(--color-brand-primary);
}

.ui-toggle:checked + .ui-toggle-track::after {
  transform: translateX(14px);
  background: #fff;
}

.ui-select {
  width: 100%;
  height: 32px;
  background: var(--color-bg-muted);
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-sm);
  color: var(--color-text-primary);
  font: var(--font-body-sm);
  padding: 0 8px;
  outline: none;
  transition: border-color var(--motion-fast) var(--ease-standard);
}

.ui-select:focus {
  border-color: var(--color-brand-primary);
}

.option-unconfigured {
  color: var(--color-text-tertiary);
}

.align-center { text-align: center; }

.status-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-text-tertiary);
  transition: background var(--motion-fast) var(--ease-standard), box-shadow var(--motion-fast) var(--ease-standard);
}
.status-dot.ready { background: var(--color-success); box-shadow: 0 0 6px var(--color-success); }
.status-dot.warning { background: var(--color-warning); }
.status-dot.error { background: var(--color-danger); }
.status-dot.neutral { background: var(--color-bg-muted); border: 1px solid var(--color-border-default); }
</style>
