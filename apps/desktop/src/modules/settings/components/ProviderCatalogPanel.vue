<template>
  <section class="settings-workspace-panel" data-testid="provider-catalog-panel">
    <div class="settings-workspace-panel__header">
      <div>
        <p class="detail-panel__label">Provider 与模型</p>
        <h2>接入注册表与连接凭据</h2>
        <p class="workspace-page__summary">
          这里直接反映 Provider 注册表、模型目录和真实连接状态，不把凭据当作假成功率来展示。
        </p>
      </div>
      <div class="settings-workspace-panel__meta">
        <span class="settings-workspace-panel__pill">Provider {{ providerCatalog.length }}</span>
        <span class="settings-workspace-panel__pill settings-workspace-panel__pill--muted">已配置 {{ configuredProviderCount }}</span>
      </div>
    </div>

    <div v-if="providerCatalog.length === 0" class="settings-workspace-panel__empty" data-testid="provider-empty-state">
      Provider 注册表尚未加载。
    </div>

    <template v-else>
      <div class="provider-toolbar">
        <label class="settings-field provider-toolbar__selector">
          <span>当前 Provider</span>
          <select
            :value="selectedProviderId"
            data-testid="provider-picker"
            data-field="provider.selected"
            :disabled="disabled"
            @change="$emit('select-provider', String(($event.target as HTMLSelectElement).value))"
          >
            <option v-for="provider in providerCatalog" :key="provider.provider" :value="provider.provider">
              {{ provider.label }}
            </option>
          </select>
        </label>

        <article class="provider-summary" :class="providerSummaryTone">
          <div class="provider-summary__header">
            <div>
              <h3>{{ selectedProvider?.label ?? "未选择 Provider" }}</h3>
              <p>{{ selectedProvider?.provider ?? "请选择 Provider" }} · {{ selectedProvider?.kind ?? "-" }}</p>
            </div>
            <span class="provider-summary__status">{{ providerStatusText }}</span>
          </div>

          <div class="provider-summary__chips">
            <span
              v-for="capability in selectedProvider?.capabilities ?? []"
              :key="capability"
              class="settings-workspace-panel__pill settings-workspace-panel__pill--muted"
            >
              {{ capability }}
            </span>
          </div>

          <p class="provider-summary__endpoint" :title="selectedProviderBaseUrl">
            {{ selectedProviderBaseUrl || "等待配置 Base URL" }}
          </p>
        </article>
      </div>

      <div class="provider-workspace-grid">
        <section class="settings-card">
          <div class="settings-card__header">
            <div>
              <p class="detail-panel__label">模型目录</p>
              <h3>{{ selectedProviderLabel }}</h3>
            </div>
            <button class="settings-workspace-panel__button" type="button" :disabled="disabled" @click="$emit('refresh-models')">
              刷新目录
            </button>
          </div>

          <label class="settings-field">
            <span>健康检查模型</span>
            <select
              :value="healthModel"
              data-field="provider.health.model"
              :disabled="disabled || selectedProviderModels.length === 0"
              @change="$emit('update:health-model', String(($event.target as HTMLSelectElement).value))"
            >
              <option value="">
                {{ selectedProviderModels.length === 0 ? "当前 Provider 暂无模型目录" : "请选择健康检查模型" }}
              </option>
              <option v-for="model in selectedProviderModels" :key="`${model.provider}:${model.modelId}`" :value="model.modelId">
                {{ model.displayName }}
              </option>
            </select>
          </label>

          <div v-if="selectedProviderModels.length === 0" class="settings-workspace-panel__empty">
            先连接 Provider，再查看可用模型目录。
          </div>
          <div v-else class="provider-model-list">
            <article
              v-for="model in selectedProviderModels"
              :key="`${model.provider}:${model.modelId}`"
              class="provider-model-list__item"
            >
              <div class="provider-model-list__copy">
                <h4>{{ model.displayName }}</h4>
                <p :title="model.modelId">{{ model.modelId }}</p>
              </div>
              <div class="provider-model-list__meta">
                <span>{{ model.capabilityTypes.join(" / ") }}</span>
                <span>默认用于 {{ model.defaultFor.join("、") || "手动选择" }}</span>
              </div>
            </article>
          </div>
        </section>

        <section class="settings-card">
          <div class="settings-card__header">
            <div>
              <p class="detail-panel__label">连接凭据</p>
              <h3>{{ selectedProviderTitle }}</h3>
            </div>
            <button
              class="settings-workspace-panel__button"
              type="button"
              data-action="check-provider"
              :disabled="disabled || selectedProviderModels.length === 0"
              @click="$emit('check-provider')"
            >
              执行连接检查
            </button>
          </div>

          <div class="provider-secret__status" :class="providerHealthTone">
            <strong>{{ selectedProviderHealthLabel }}</strong>
            <p>{{ selectedProviderHealth?.message ?? secretStatusSummary }}</p>
          </div>

          <label class="settings-field">
            <span>API Key</span>
            <input
              v-model="providerDraft.apiKey"
              data-field="provider.secret.apiKey"
              :placeholder="secretPlaceholder"
              :disabled="disabled"
              type="password"
            />
          </label>
          <label class="settings-field">
            <span>Base URL</span>
            <input
              v-model="providerDraft.baseUrl"
              data-field="provider.secret.baseUrl"
              :placeholder="selectedProviderBaseUrl"
              :title="providerDraft.baseUrl || selectedProviderBaseUrl"
              :disabled="disabled"
            />
          </label>
          <div class="settings-card__actions">
            <button class="settings-workspace-panel__button" type="button" :disabled="disabled" @click="$emit('save-provider-secret')">
              保存凭据
            </button>
          </div>
        </section>
      </div>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";

import type {
  AIModelCatalogItem,
  AIProviderCatalogItem,
  AIProviderHealth,
  AIProviderSecretStatus
} from "@/types/runtime";

const props = defineProps<{
  disabled: boolean;
  healthModel: string;
  providerCatalog: AIProviderCatalogItem[];
  providerDraft: { apiKey: string; baseUrl: string };
  selectedProviderHealth: AIProviderHealth | null;
  selectedProviderId: string;
  selectedProviderModels: AIModelCatalogItem[];
  secretStatus: AIProviderSecretStatus | null;
}>();

defineEmits<{
  (e: "check-provider"): void;
  (e: "refresh-models"): void;
  (e: "save-provider-secret"): void;
  (e: "select-provider", providerId: string): void;
  (e: "update:health-model", modelId: string): void;
}>();

const configuredProviderCount = computed(
  () => props.providerCatalog.filter((provider) => provider.configured).length
);
const selectedProvider = computed(
  () => props.providerCatalog.find((item) => item.provider === props.selectedProviderId) ?? null
);
const selectedProviderLabel = computed(() =>
  selectedProvider.value ? `${selectedProvider.value.label} 模型目录` : "模型目录"
);
const selectedProviderTitle = computed(() =>
  selectedProvider.value ? `${selectedProvider.value.label} 连接凭据` : "连接凭据"
);
const selectedProviderBaseUrl = computed(() => selectedProvider.value?.baseUrl ?? "");
const selectedProviderHealthLabel = computed(() => {
  switch (props.selectedProviderHealth?.status) {
    case "ready":
      return "连接正常";
    case "missing_secret":
      return "缺少密钥";
    case "misconfigured":
      return "配置不完整";
    case "offline":
      return "连接离线";
    default:
      return "等待检查";
  }
});
const secretStatusSummary = computed(() => {
  if (props.secretStatus?.configured) {
    return `已保存 ${props.secretStatus.maskedSecret}，来源 ${props.secretStatus.secretSource}。`;
  }
  return "当前 Provider 还没有可用凭据。";
});
const secretPlaceholder = computed(() =>
  props.secretStatus?.configured ? "已保存密钥，输入后会覆盖" : "请输入 Provider API Key"
);
const providerStatusText = computed(() =>
  selectedProvider.value ? providerStatusLabel(selectedProvider.value.status) : "待选择"
);
const providerSummaryTone = computed(() => {
  switch (selectedProvider.value?.status) {
    case "ready":
      return "provider-summary--ready";
    case "missing_secret":
    case "misconfigured":
    case "offline":
      return "provider-summary--blocked";
    default:
      return "provider-summary--idle";
  }
});
const providerHealthTone = computed(() => {
  switch (props.selectedProviderHealth?.status) {
    case "ready":
      return "provider-secret__status--ready";
    case "missing_secret":
    case "misconfigured":
    case "offline":
      return "provider-secret__status--alert";
    default:
      return "";
  }
});

function providerStatusLabel(status: string): string {
  return (
    {
      missing_secret: "缺少密钥",
      misconfigured: "配置不完整",
      ready: "已就绪",
      unsupported: "暂未接入",
      offline: "离线"
    }[status] ?? status
  );
}
</script>

<style scoped>
.settings-workspace-panel {
  display: grid;
  gap: 16px;
}

.settings-workspace-panel__header,
.provider-toolbar,
.provider-workspace-grid {
  display: grid;
  gap: 14px;
}

.settings-workspace-panel__header {
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: start;
}

.settings-workspace-panel__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: flex-end;
}

.settings-workspace-panel__pill {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 0 10px;
  border: 1px solid var(--border-default);
  border-radius: 999px;
  background: color-mix(in srgb, var(--surface-secondary) 92%, transparent);
  color: var(--text-primary);
  font-size: 12px;
}

.settings-workspace-panel__pill--muted {
  color: var(--text-secondary);
}

.settings-workspace-panel__empty {
  padding: 16px;
  border: 1px dashed var(--border-default);
  border-radius: 8px;
  background: color-mix(in srgb, var(--surface-secondary) 92%, transparent);
  color: var(--text-secondary);
}

.provider-toolbar {
  grid-template-columns: minmax(280px, 320px) minmax(0, 1fr);
  align-items: start;
}

.provider-toolbar__selector {
  margin: 0;
}

.provider-summary {
  display: grid;
  gap: 12px;
  min-width: 0;
  padding: 18px;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: color-mix(in srgb, var(--surface-secondary) 94%, transparent);
}

.provider-summary--ready {
  border-color: color-mix(in srgb, var(--status-success) 28%, var(--border-default));
}

.provider-summary--blocked {
  border-color: color-mix(in srgb, var(--status-warning) 30%, var(--border-default));
}

.provider-summary--idle {
  border-color: color-mix(in srgb, var(--brand-primary) 18%, var(--border-default));
}

.provider-summary__header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: start;
}

.provider-summary__header h3,
.provider-model-list__item h4 {
  margin: 0;
}

.provider-summary__header p,
.provider-model-list__copy p,
.provider-model-list__meta span {
  margin: 0;
  color: var(--text-secondary);
}

.provider-summary__status {
  flex-shrink: 0;
  min-height: 24px;
  padding: 0 8px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--surface-primary) 92%, transparent);
  color: var(--text-primary);
  font-size: 12px;
  line-height: 24px;
}

.provider-summary__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.provider-summary__endpoint {
  margin: 0;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text-secondary);
  font-family: var(--font-mono);
}

.provider-workspace-grid {
  grid-template-columns: minmax(0, 1.15fr) minmax(320px, 0.85fr);
}

.settings-card {
  display: grid;
  gap: 14px;
  padding: 16px;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: color-mix(in srgb, var(--surface-secondary) 94%, transparent);
}

.settings-card__header,
.settings-card__actions {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: start;
}

.settings-card__header h3 {
  margin: 0;
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
.settings-field select {
  width: 100%;
  min-height: 38px;
  padding: 0 12px;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: color-mix(in srgb, var(--surface-primary) 96%, transparent);
  color: var(--text-primary);
  font: inherit;
}

.settings-workspace-panel__button {
  min-height: 36px;
  padding: 0 12px;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: transparent;
  color: var(--text-primary);
  font: inherit;
  cursor: pointer;
}

.settings-workspace-panel__button:disabled,
.settings-field input:disabled,
.settings-field select:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.provider-model-list {
  display: grid;
  gap: 10px;
  max-height: 340px;
  overflow-y: auto;
  padding-right: 4px;
}

.provider-model-list__item {
  display: grid;
  gap: 8px;
  padding: 14px 16px;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: color-mix(in srgb, var(--surface-primary) 96%, transparent);
}

.provider-model-list__copy,
.provider-model-list__meta {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.provider-model-list__copy p {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.provider-secret__status {
  display: grid;
  gap: 6px;
  padding: 12px 14px;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: color-mix(in srgb, var(--surface-secondary) 90%, transparent);
}

.provider-secret__status strong,
.provider-secret__status p {
  margin: 0;
}

.provider-secret__status p {
  color: var(--text-secondary);
}

.provider-secret__status--ready {
  border-color: color-mix(in srgb, var(--status-success) 30%, var(--border-default));
}

.provider-secret__status--alert {
  border-color: color-mix(in srgb, var(--status-warning) 30%, var(--border-default));
}

@media (max-width: 1120px) {
  .provider-toolbar,
  .provider-workspace-grid {
    grid-template-columns: 1fr;
  }

  .settings-workspace-panel__header {
    grid-template-columns: 1fr;
  }
}
</style>
