<template>
  <section class="settings-workspace-panel">
    <div class="editor-card__header">
      <div>
        <p class="detail-panel__label">Provider 与模型</p>
        <h2>多 AI 接入与能力选用</h2>
        <p class="workspace-page__summary">
          Provider 改成紧凑选择式工作流，先选对象，再看模型、凭据和测试结果。
        </p>
      </div>
      <div class="settings-workspace-panel__meta">
        <span class="page-chip">Provider {{ providerCatalog.length }}</span>
        <span class="page-chip page-chip--muted">已配置 {{ configuredProviderCount }}</span>
      </div>
    </div>

    <div v-if="providerCatalog.length === 0" class="empty-state">Provider 注册表尚未加载。</div>
    <template v-else>
      <section class="provider-toolbar">
        <label class="settings-field provider-toolbar__selector">
          <span>当前 Provider</span>
          <select
            :value="selectedProviderId"
            data-testid="provider-picker"
            data-field="provider.selected"
            @change="$emit('select-provider', String(($event.target as HTMLSelectElement).value))"
          >
            <option
              v-for="provider in providerCatalog"
              :key="provider.provider"
              :value="provider.provider"
            >
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
              class="page-chip page-chip--muted"
            >
              {{ capability }}
            </span>
          </div>

          <p class="provider-summary__endpoint" :title="selectedProviderBaseUrl">
            {{ selectedProviderBaseUrl || "等待配置 Base URL" }}
          </p>
        </article>
      </section>

      <div class="provider-workspace-grid">
        <section class="command-panel settings-card">
          <div class="editor-card__header">
            <div>
              <p class="detail-panel__label">模型目录</p>
              <h2>{{ selectedProviderLabel }}</h2>
            </div>
            <button class="dashboard-list__action" type="button" @click="$emit('refresh-models')">
              刷新目录
            </button>
          </div>

          <label class="settings-field">
            <span>测试模型</span>
            <select
              :value="healthModel"
              data-field="provider.health.model"
              :disabled="selectedProviderModels.length === 0"
              @change="$emit('update:health-model', String(($event.target as HTMLSelectElement).value))"
            >
              <option value="">
                {{ selectedProviderModels.length === 0 ? "当前 Provider 暂无模型目录" : "请选择测试模型" }}
              </option>
              <option
                v-for="model in selectedProviderModels"
                :key="`${model.provider}:${model.modelId}`"
                :value="model.modelId"
              >
                {{ model.displayName }}
              </option>
            </select>
          </label>

          <div v-if="selectedProviderModels.length === 0" class="empty-state">
            选择 Provider 后显示可测试模型。
          </div>
          <div v-else class="provider-model-list">
            <article
              v-for="model in selectedProviderModels"
              :key="`${model.provider}:${model.modelId}`"
              class="provider-model-list__item"
            >
              <div class="provider-model-list__copy">
                <h3>{{ model.displayName }}</h3>
                <p :title="model.modelId">{{ model.modelId }}</p>
              </div>
              <div class="provider-model-list__meta">
                <span>{{ model.capabilityTypes.join(" / ") }}</span>
                <span>默认用于 {{ model.defaultFor.join("、") || "手动选择" }}</span>
              </div>
            </article>
          </div>
        </section>

        <section class="command-panel settings-card">
          <div class="editor-card__header">
            <div>
              <p class="detail-panel__label">连接凭据</p>
              <h2>{{ selectedProviderTitle }}</h2>
            </div>
            <button
              class="dashboard-list__action"
              type="button"
              data-action="check-provider"
              @click="$emit('check-provider')"
            >
              测试连接
            </button>
          </div>

          <div class="provider-secret__status" :class="providerHealthTone">
            <strong>{{ selectedProviderHealth?.status === "ready" ? "连通性正常" : "当前状态" }}</strong>
            <p>{{ selectedProviderHealth?.message ?? secretStatusSummary }}</p>
          </div>

          <label class="settings-field">
            <span>API Key</span>
            <input
              v-model="providerDraft.apiKey"
              data-field="provider.secret.apiKey"
              :placeholder="secretPlaceholder"
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
            />
          </label>
          <div class="editor-card__actions">
            <button class="settings-page__button" type="button" @click="$emit('save-provider-secret')">
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
const secretStatusSummary = computed(() => {
  if (props.secretStatus?.configured) {
    return `已保存 ${props.secretStatus.maskedSecret}，来源 ${props.secretStatus.secretSource}。`;
  }
  return "当前 Provider 尚未保存可用凭据。";
});
const secretPlaceholder = computed(() =>
  props.secretStatus?.configured ? "已保存密钥；输入新值后覆盖" : "输入 Provider API Key"
);
const providerStatusText = computed(() =>
  selectedProvider.value ? providerStatusLabel(selectedProvider.value.status) : "待选择"
);
const providerSummaryTone = computed(() =>
  selectedProvider.value?.status === "ready" ? "provider-summary--ready" : "provider-summary--idle"
);
const providerHealthTone = computed(() => {
  switch (props.selectedProviderHealth?.status) {
    case "ready":
      return "provider-secret__status--ready";
    case "offline":
    case "misconfigured":
    case "missing_secret":
      return "provider-secret__status--alert";
    default:
      return "";
  }
});

function providerStatusLabel(status: string): string {
  return (
    {
      missing_secret: "需要配置密钥",
      misconfigured: "配置不完整",
      ready: "已就绪",
      unsupported: "暂未接入",
      offline: "离线"
    }[status] ?? status
  );
}
</script>

<style scoped>
.settings-workspace-panel,
.settings-workspace-panel__meta {
  display: grid;
  gap: 16px;
}

.settings-workspace-panel__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.provider-toolbar,
.provider-workspace-grid,
.provider-model-list {
  display: grid;
  gap: 14px;
}

.provider-toolbar {
  align-items: start;
  grid-template-columns: minmax(280px, 320px) minmax(0, 1fr);
}

.provider-toolbar__selector {
  margin: 0;
}

.provider-summary {
  display: grid;
  gap: 12px;
  min-width: 0;
  padding: 18px 20px;
  border: 1px solid var(--border-default);
  border-radius: 14px;
  background: color-mix(in srgb, var(--surface-secondary) 92%, transparent);
}

.provider-summary--ready {
  border-color: color-mix(in srgb, var(--status-success) 28%, var(--border-default));
  background: color-mix(in srgb, var(--status-success) 8%, var(--surface-secondary));
}

.provider-summary--idle {
  border-color: color-mix(in srgb, var(--brand-primary) 18%, var(--border-default));
}

.provider-summary__header {
  align-items: start;
  display: flex;
  gap: 12px;
  justify-content: space-between;
}

.provider-summary__header h3,
.provider-model-list__item h3 {
  margin: 0;
}

.provider-summary__header p,
.provider-model-list__copy p,
.provider-model-list__meta span {
  color: var(--text-secondary);
  margin: 0;
}

.provider-summary__status {
  flex-shrink: 0;
  padding: 4px 10px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--surface-tertiary) 88%, transparent);
  color: var(--text-primary);
  font-size: 12px;
  font-weight: 700;
}

.provider-summary__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
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

.provider-model-list {
  max-height: 340px;
  overflow-y: auto;
  padding-right: 4px;
}

.provider-model-list__item {
  display: grid;
  gap: 8px;
  padding: 14px 16px;
  border: 1px solid var(--border-default);
  border-radius: 12px;
  background: color-mix(in srgb, var(--surface-secondary) 90%, transparent);
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
  margin-bottom: 14px;
  padding: 12px 14px;
  border-radius: 12px;
  border: 1px solid var(--border-default);
  background: color-mix(in srgb, var(--surface-secondary) 88%, transparent);
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
  background: color-mix(in srgb, var(--status-success) 10%, var(--surface-secondary));
}

.provider-secret__status--alert {
  border-color: color-mix(in srgb, var(--status-warning) 30%, var(--border-default));
  background: color-mix(in srgb, var(--status-warning) 12%, var(--surface-secondary));
}

@media (max-width: 1120px) {
  .provider-toolbar,
  .provider-workspace-grid {
    grid-template-columns: 1fr;
  }
}
</style>
