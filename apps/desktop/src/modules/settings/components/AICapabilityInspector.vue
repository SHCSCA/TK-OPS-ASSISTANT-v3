<template>
  <section class="settings-workspace-panel capability-strategy-inspector">
    <div class="settings-workspace-panel__header">
      <div>
        <p class="detail-panel__label">能力 Inspector</p>
        <h2>{{ title }}</h2>
        <p class="workspace-page__summary">{{ summary }}</p>
      </div>
    </div>

    <div v-if="capability === null" class="settings-workspace-panel__empty">
      先选择一个能力，再查看绑定细节。
    </div>

    <div v-else class="capability-strategy-inspector__stack">
      <section class="capability-binding-preview">
        <div>
          <p class="detail-panel__label">绑定预览</p>
          <h3>{{ capabilityLabel }}</h3>
        </div>
        <div class="capability-binding-preview__grid">
          <span>Provider <strong>{{ capability.provider || "未绑定" }}</strong></span>
          <span>模型 <strong>{{ capability.model || "未绑定" }}</strong></span>
          <span>Agent <strong>{{ capability.agentRole || "未设置" }}</strong></span>
          <span>状态 <strong>{{ capability.enabled ? "已启用" : "已停用" }}</strong></span>
        </div>
        <div v-if="supportSummary.length > 0" class="capability-inspector__chips">
          <span v-for="item in supportSummary" :key="item" class="settings-workspace-panel__pill">
            {{ item }}
          </span>
        </div>
      </section>

      <section class="settings-card">
        <label class="settings-field">
          <span>Provider</span>
          <select
            v-model="capability.provider"
            :data-field="`capability.${capability.capabilityId}.provider`"
            :disabled="disabled || providerOptions.length === 0"
          >
            <option value="">{{ providerOptions.length === 0 ? "当前能力暂无可用 Provider" : "请选择 Provider" }}</option>
            <option v-for="option in providerOptions" :key="option.provider" :value="option.provider">
              {{ option.configured ? "● " : "" }}{{ option.label }}{{ option.configured ? "" : "（未配置）" }}
            </option>
          </select>
        </label>

        <label class="settings-field">
          <span>模型</span>
          <select
            v-model="capability.model"
            :data-field="`capability.${capability.capabilityId}.model`"
            :disabled="disabled || modelOptions.length === 0"
          >
            <option value="">{{ modelOptions.length === 0 ? "当前 Provider 暂无模型" : "请选择模型" }}</option>
            <option v-for="option in modelOptions" :key="option.modelId" :value="option.modelId">
              {{ option.displayName }}
            </option>
          </select>
        </label>

        <label class="settings-field">
          <span>Agent 角色</span>
          <input
            v-model="capability.agentRole"
            :data-field="`capability.${capability.capabilityId}.agentRole`"
            :disabled="disabled"
          />
        </label>

        <label class="settings-field">
          <span>系统提示词</span>
          <textarea
            v-model="capability.systemPrompt"
            class="editor-textarea"
            :data-field="`capability.${capability.capabilityId}.systemPrompt`"
            :disabled="disabled"
          />
        </label>

        <label class="settings-field">
          <span>用户提示词模板</span>
          <textarea
            v-model="capability.userPromptTemplate"
            class="editor-textarea editor-textarea--compact"
            :data-field="`capability.${capability.capabilityId}.userPromptTemplate`"
            :disabled="disabled"
          />
        </label>
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";

import type {
  AICapabilityConfig,
  AICapabilitySupportItem,
  AIModelCatalogItem,
  AIProviderCatalogItem
} from "@/types/runtime";

const props = defineProps<{
  capability: AICapabilityConfig | null;
  capabilityLabel: string;
  disabled: boolean;
  providerCatalog: AIProviderCatalogItem[];
  modelCatalogByProvider: Record<string, AIModelCatalogItem[]>;
  supportItem: AICapabilitySupportItem | null;
}>();

const emit = defineEmits<{
  (e: "loadModels", providerId: string): void;
}>();

const title = computed(() => (props.capability ? `${props.capabilityLabel} 策略` : "能力策略"));
const summary = computed(() => {
  if (!props.capability) {
    return "右侧 Inspector 只显示当前选中的能力，避免一次展开太多提示词。";
  }

  return `当前绑定 ${props.capability.provider || "未绑定 Provider"} / ${props.capability.model || "未绑定模型"}。修改后统一通过底部保存条提交。`;
});
const supportSummary = computed(() => {
  if (!props.supportItem) {
    return [];
  }

  return [
    `推荐 Provider ${props.supportItem.providers.length}`,
    `推荐模型 ${props.supportItem.models.length}`
  ];
});
const providerOptions = computed(() => {
  return [...props.providerCatalog].sort((a, b) => {
    const aReady = a.configured ? 0 : 1;
    const bReady = b.configured ? 0 : 1;
    if (aReady !== bReady) return aReady - bReady;
    return a.label.localeCompare(b.label, "zh-Hans-CN");
  });
});
const modelOptions = computed(() => {
  if (!props.capability?.provider) {
    return [];
  }

  const loadedModels = props.modelCatalogByProvider[props.capability.provider] ?? [];
  if (loadedModels.length > 0) {
    return loadedModels;
  }
  return props.supportItem?.models.filter((item) => item.provider === props.capability?.provider) ?? [];
});

const previousProvider = ref("");

watch(
  () => props.capability?.provider ?? "",
  (provider) => {
    if (!props.capability) {
      return;
    }

    if (provider && previousProvider.value && provider !== previousProvider.value) {
      props.capability.model = "";
    }
    if (provider && !(provider in props.modelCatalogByProvider)) {
      emit("loadModels", provider);
    }
    previousProvider.value = provider;
  },
  { immediate: true }
);

watch(
  () => [props.capability?.model, modelOptions.value],
  () => {
    if (!props.capability) {
      return;
    }
    if (modelOptions.value.length > 0) {
      const hasModel = modelOptions.value.some((item) => item.modelId === props.capability?.model);
      if (!hasModel) {
        props.capability.model = modelOptions.value[0].modelId;
      }
    }
  },
  { deep: true, immediate: true }
);
</script>

<style scoped>
.settings-workspace-panel {
  display: grid;
  gap: 16px;
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

.settings-card {
  display: grid;
  gap: 14px;
  padding: 16px;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: color-mix(in srgb, var(--surface-secondary) 94%, transparent);
}

.capability-strategy-inspector__stack {
  display: grid;
  gap: 14px;
  min-width: 0;
}

.capability-binding-preview {
  display: grid;
  gap: 12px;
  padding: 16px;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: color-mix(in srgb, var(--surface-secondary) 94%, transparent);
}

.capability-binding-preview h3,
.capability-binding-preview .detail-panel__label {
  margin: 0;
}

.capability-binding-preview__grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.capability-binding-preview__grid span {
  display: grid;
  gap: 4px;
  min-width: 0;
  color: var(--text-secondary);
  font-size: 12px;
}

.capability-binding-preview__grid strong {
  min-width: 0;
  overflow-wrap: anywhere;
  color: var(--text-primary);
  font: var(--font-title-sm);
}

.capability-inspector__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.settings-field {
  display: grid;
  gap: 8px;
}

.settings-field span {
  color: var(--text-secondary);
  font-size: 12px;
}

.settings-field input,
.settings-field select,
.editor-textarea {
  width: 100%;
  min-height: 38px;
  padding: 10px 12px;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: color-mix(in srgb, var(--surface-primary) 96%, transparent);
  color: var(--text-primary);
  font: inherit;
}

.editor-textarea {
  min-height: 120px;
  resize: vertical;
}

.editor-textarea--compact {
  min-height: 100px;
}

@media (max-width: 1120px) {
  .settings-card {
    gap: 12px;
  }
}

@container settings-console (max-width: 720px) {
  .capability-binding-preview__grid {
    grid-template-columns: 1fr;
  }
}
</style>
