<template>
  <section class="settings-workspace-panel">
    <div class="editor-card__header">
      <div>
        <p class="detail-panel__label">能力 Inspector</p>
        <h2>{{ title }}</h2>
        <p class="workspace-page__summary">{{ summary }}</p>
      </div>
    </div>

    <div v-if="capability === null" class="empty-state">选择能力后显示详细策略。</div>
    <section v-else class="command-panel settings-card">
      <div v-if="supportSummary.length > 0" class="capability-inspector__options">
        <span v-for="item in supportSummary" :key="item" class="page-chip page-chip--muted">
          {{ item }}
        </span>
      </div>

      <label class="settings-field">
        <span>Provider</span>
        <select
          v-model="capability.provider"
          :data-field="`capability.${capability.capabilityId}.provider`"
          :disabled="disabled || providerOptions.length === 0"
        >
          <option value="">{{ providerOptions.length === 0 ? "当前能力暂无可选 Provider" : "请选择 Provider" }}</option>
          <option v-for="option in providerOptions" :key="option.provider" :value="option.provider">
            {{ option.label }}
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
          <option value="">{{ modelOptions.length === 0 ? "当前 Provider 暂无可选模型" : "请选择模型" }}</option>
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
  </section>
</template>

<script setup lang="ts">
import { computed, watch } from "vue";

import type {
  AICapabilityConfig,
  AICapabilitySupportItem,
  AIProviderCatalogItem
} from "@/types/runtime";

const props = defineProps<{
  capability: AICapabilityConfig | null;
  capabilityLabel: string;
  disabled: boolean;
  providerCatalog: AIProviderCatalogItem[];
  supportItem: AICapabilitySupportItem | null;
}>();

const title = computed(() => (props.capability ? `${props.capabilityLabel} 策略` : "能力策略"));
const summary = computed(() => {
  if (!props.capability) {
    return "右侧 Inspector 只显示当前选中能力，避免一次性展开所有提示词。";
  }

  return `当前能力绑定 ${props.capability.provider} / ${props.capability.model}。修改后统一通过底部保存条提交。`;
});
const supportSummary = computed(() => {
  if (!props.supportItem) {
    return [];
  }

  return [
    `可选 Provider ${props.supportItem.providers.length}`,
    `可选模型 ${props.supportItem.models.length}`
  ];
});
const providerOptions = computed(() => {
  if (!props.supportItem) {
    return [];
  }

  return props.supportItem.providers.map((providerId) => {
    const provider = props.providerCatalog.find((item) => item.provider === providerId);
    return {
      label: provider?.label ?? providerId,
      provider: providerId
    };
  });
});
const modelOptions = computed(() => {
  if (!props.supportItem || !props.capability) {
    return [];
  }

  return props.supportItem.models.filter((item) => item.provider === props.capability?.provider);
});

watch(
  () => [props.capability?.provider, props.supportItem?.providers, props.supportItem?.models],
  () => {
    if (!props.capability) {
      return;
    }

    if (providerOptions.value.length > 0) {
      const hasProvider = providerOptions.value.some((item) => item.provider === props.capability?.provider);
      if (!hasProvider) {
        props.capability.provider = providerOptions.value[0].provider;
      }
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

.capability-inspector__options {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
</style>
